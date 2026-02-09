"""Herbie-based GRIB2 weather data client."""

from __future__ import annotations

import logging
import math
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from weather.clients.base import BaseClient, ClientConfig
from weather.config.models import get_fxx_range, get_model_config, validate_model_id
from weather.domain.errors import ApiError, ModelError
from weather.domain.forecast import Forecast
from weather.parsing.grib2_parser import build_hourly_data

logger = logging.getLogger(__name__)

# GRIB2 search strings for each variable (NCEP wgrib2 format)
VARIABLE_SEARCH: dict[str, str] = {
    "temperature": ":TMP:2 m above ground:",
    "precipitation": ":APCP:surface:",
    "snowfall": ":ASNOW:surface:",
    "wind_u": ":UGRD:10 m above ground:",
    "wind_v": ":VGRD:10 m above ground:",
    "wind_gusts": ":GUST:surface:",
    "freezing_level": ":HGT:0C isotherm:",
}

# ECMWF eccodes-style search strings
ECMWF_VARIABLE_SEARCH: dict[str, str] = {
    "temperature": ":2t:",
    "precipitation": ":tp:",
    "snowfall": ":sf:",
    "wind_u": ":10u:",
    "wind_v": ":10v:",
    "wind_gusts": ":10fg:",
    "freezing_level": ":gh:",
}

ECMWF_MODELS = {"ifs", "aifs", "ecmwf_ens"}


def get_variable_search(model_id: str) -> dict[str, str]:
    """Return the correct GRIB2 search strings for a model."""
    if model_id in ECMWF_MODELS:
        return ECMWF_VARIABLE_SEARCH
    return VARIABLE_SEARCH


# Variables to exclude for specific models (not available in their GRIB2 products)
MODEL_VARIABLE_EXCLUSIONS: dict[str, set[str]] = {
    "nbm": {"snowfall", "wind_gusts", "freezing_level"},
    "aifs": {"snowfall", "wind_gusts", "freezing_level"},
    "ecmwf_ens": {"snowfall", "wind_gusts", "freezing_level"},
    "ifs": {"freezing_level"},
}

# Maximum hours to process in one FastHerbie batch (limits memory usage)
FASTHERBIE_CHUNK_SIZE = 48


class HerbieClient(BaseClient):
    """Client that fetches weather data from GRIB2 files via the Herbie library.

    Uses Herbie to download GRIB2 model data and extracts point forecasts
    for specified coordinates.

    Example:
        >>> client = HerbieClient()
        >>> forecast = client.get_forecast(43.48, -110.76, model="hrrr")
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        config: ClientConfig | None = None,
    ) -> None:
        """Initialize the Herbie client.

        Args:
            cache_dir: Directory for GRIB2 file caching. Defaults to Herbie's default.
            config: Optional client configuration.
        """
        super().__init__(config)
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def _get_herbie(self, model_id: str, run_dt: datetime, fxx: int) -> Any:
        """Create a Herbie instance for a specific model run and forecast hour.

        Args:
            model_id: Canonical model ID.
            run_dt: Model run datetime (will be made naive for Herbie).
            fxx: Forecast hour.

        Returns:
            A Herbie instance.

        Raises:
            ApiError: If Herbie is not installed or model not supported.
        """
        try:
            from herbie import Herbie
        except ImportError:
            raise ApiError(
                "Herbie is not installed. Install with: pip install mountain-weather[herbie]"
            )

        config = get_model_config(model_id)
        if not config.herbie_model:
            raise ModelError(
                f"Model '{model_id}' does not support Herbie/GRIB2 access",
                model_id=model_id,
            )

        # Herbie expects naive datetimes
        naive_dt = run_dt.replace(tzinfo=None) if run_dt.tzinfo else run_dt

        kwargs: dict[str, Any] = {
            "date": naive_dt,
            "model": config.herbie_model,
            "product": config.herbie_product,
            "fxx": fxx,
            "priority": ["google", "aws", "nomads", "ecmwf"],
        }

        # Ensemble models need member="mean"
        if config.is_ensemble:
            kwargs["member"] = "mean"

        if self.cache_dir:
            kwargs["save_dir"] = str(self.cache_dir)

        return Herbie(**kwargs)

    def fetch_grib2(self, model_id: str, run_dt: datetime, fxx: int) -> Path:
        """Download a single GRIB2 file for a forecast hour.

        Args:
            model_id: Canonical model ID.
            run_dt: Model run datetime.
            fxx: Forecast hour.

        Returns:
            Path to the downloaded GRIB2 file.

        Raises:
            ApiError: If download fails.
        """
        model_id = validate_model_id(model_id)

        try:
            h = self._get_herbie(model_id, run_dt, fxx)
            # Download all variables we need
            search_patterns = "|".join(get_variable_search(model_id).values())
            path = h.download(search_patterns)
            return Path(path)
        except (ApiError, ModelError):
            raise
        except Exception as e:
            raise ApiError(f"Failed to download GRIB2 for {model_id} fxx={fxx}: {e}")

    def extract_point(
        self,
        model_id: str,
        run_dt: datetime,
        fxx: int,
        lat: float,
        lon: float,
    ) -> dict[str, float | None]:
        """Extract weather variables at a single point from a GRIB2 file.

        Args:
            model_id: Canonical model ID.
            run_dt: Model run datetime.
            fxx: Forecast hour.
            lat: Latitude.
            lon: Longitude.

        Returns:
            Dict with variable values at the point.
        """
        model_id = validate_model_id(model_id)

        try:
            h = self._get_herbie(model_id, run_dt, fxx)
        except (ApiError, ModelError):
            raise
        except Exception as e:
            raise ApiError(f"Failed to create Herbie instance: {e}")

        result: dict[str, float | None] = {}
        points_df = pd.DataFrame({"latitude": [lat], "longitude": [lon]})

        for var_name, search_str in get_variable_search(model_id).items():
            try:
                ds = h.xarray(search_str)
                data_var = list(ds.data_vars)[0]
                # pick_points handles both projected (HRRR, NBM) and regular grids
                ds_points = ds.herbie.pick_points(points_df, method="nearest")
                fval = ds_points[data_var].isel(point=0).values.item()
                if math.isnan(fval):
                    result[var_name] = None
                else:
                    result[var_name] = fval
            except Exception as e:
                logger.debug(f"Variable {var_name} not available for {model_id} fxx={fxx}: {e}")
                result[var_name] = None

        return result

    def extract_points_batch(
        self,
        model_id: str,
        run_dt: datetime,
        fxx: int,
        points: list[tuple[float, float]],
    ) -> list[dict[str, float | None]]:
        """Extract weather variables at multiple points from a single GRIB2 file.

        More efficient than calling extract_point() repeatedly since the GRIB2
        data is loaded once.

        Args:
            model_id: Canonical model ID.
            run_dt: Model run datetime.
            fxx: Forecast hour.
            points: List of (lat, lon) tuples.

        Returns:
            List of dicts, one per point, with variable values.
        """
        model_id = validate_model_id(model_id)

        try:
            h = self._get_herbie(model_id, run_dt, fxx)
        except (ApiError, ModelError):
            raise
        except Exception as e:
            raise ApiError(f"Failed to create Herbie instance: {e}")

        # Load each variable's dataset once
        datasets: dict[str, Any] = {}
        data_var_names: dict[str, str] = {}

        var_search = get_variable_search(model_id)
        for var_name, search_str in var_search.items():
            try:
                ds = h.xarray(search_str)
                data_var = list(ds.data_vars)[0]
                datasets[var_name] = ds
                data_var_names[var_name] = data_var
            except Exception as e:
                logger.debug(f"Variable {var_name} not available: {e}")

        # Build points dataframe and extract all points at once per variable
        points_df = pd.DataFrame({
            "latitude": [lat for lat, lon in points],
            "longitude": [lon for lat, lon in points],
        })
        results: list[dict[str, float | None]] = [
            {var: None for var in var_search} for _ in points
        ]

        for var_name in var_search:
            if var_name not in datasets:
                continue

            try:
                ds = datasets[var_name]
                data_var = data_var_names[var_name]
                # pick_points handles both projected (HRRR, NBM) and regular grids
                ds_points = ds.herbie.pick_points(points_df, method="nearest")
                for i in range(len(points)):
                    fval = ds_points[data_var].isel(point=i).values.item()
                    if math.isnan(fval):
                        results[i][var_name] = None
                    else:
                        results[i][var_name] = fval
            except Exception:
                pass  # Already initialized to None

        return results

    def extract_all_hours_batch(
        self,
        model_id: str,
        run_dt: datetime,
        fxx_range: list[int],
        points: list[tuple[float, float]],
        max_concurrent: int = 4,
    ) -> tuple[list[int], dict[int, list[dict[str, float | None]]]]:
        """Extract all forecast hours in parallel using FastHerbie.

        Uses FastHerbie to create Herbie objects and download GRIB2 data
        concurrently, then extracts point data for all resorts. For large
        forecast ranges (>FASTHERBIE_CHUNK_SIZE hours), processes in chunks.

        Args:
            model_id: Canonical model ID.
            run_dt: Model run datetime.
            fxx_range: List of forecast hours to process.
            points: List of (lat, lon) tuples.
            max_concurrent: Maximum concurrent downloads.

        Returns:
            Tuple of (available_fxx_list, {fxx: [point_data_dicts]}).
        """
        model_id = validate_model_id(model_id)

        if len(fxx_range) > FASTHERBIE_CHUNK_SIZE:
            return self._extract_all_hours_chunked(
                model_id, run_dt, fxx_range, points, max_concurrent
            )

        return self._extract_all_hours_single(
            model_id, run_dt, fxx_range, points, max_concurrent
        )

    def _extract_all_hours_chunked(
        self,
        model_id: str,
        run_dt: datetime,
        fxx_range: list[int],
        points: list[tuple[float, float]],
        max_concurrent: int,
    ) -> tuple[list[int], dict[int, list[dict[str, float | None]]]]:
        """Process large fxx ranges in chunks to limit memory usage."""
        all_available: list[int] = []
        all_results: dict[int, list[dict[str, float | None]]] = {}

        for chunk_start in range(0, len(fxx_range), FASTHERBIE_CHUNK_SIZE):
            chunk = fxx_range[chunk_start : chunk_start + FASTHERBIE_CHUNK_SIZE]
            logger.info(
                f"Processing chunk fxx={chunk[0]}-{chunk[-1]} "
                f"({len(chunk)} hours) for {model_id}"
            )
            avail, results = self._extract_all_hours_single(
                model_id, run_dt, chunk, points, max_concurrent
            )
            all_available.extend(avail)
            all_results.update(results)

        return all_available, all_results

    def _extract_all_hours_single(
        self,
        model_id: str,
        run_dt: datetime,
        fxx_range: list[int],
        points: list[tuple[float, float]],
        max_concurrent: int,
    ) -> tuple[list[int], dict[int, list[dict[str, float | None]]]]:
        """Extract a single chunk of forecast hours using FastHerbie."""
        try:
            from herbie import FastHerbie
        except ImportError:
            raise ApiError(
                "Herbie is not installed. Install with: pip install mountain-weather[herbie]"
            )

        config = get_model_config(model_id)
        if not config.herbie_model:
            raise ModelError(
                f"Model '{model_id}' does not support Herbie/GRIB2 access",
                model_id=model_id,
            )

        # Herbie expects naive datetimes
        naive_dt = run_dt.replace(tzinfo=None) if run_dt.tzinfo else run_dt

        kwargs: dict[str, Any] = {
            "DATES": pd.to_datetime([naive_dt]),
            "fxx": fxx_range,
            "model": config.herbie_model,
            "product": config.herbie_product,
            "max_threads": max_concurrent,
            "priority": ["google", "aws", "nomads", "ecmwf"],
        }

        if config.is_ensemble:
            kwargs["member"] = "mean"

        if self.cache_dir:
            kwargs["save_dir"] = str(self.cache_dir)

        logger.info(
            f"Creating FastHerbie for {model_id}: {len(fxx_range)} hours, "
            f"max_threads={max_concurrent}"
        )
        # Suppress herbie.fast logger during construction — FastHerbie logs
        # ERROR-level tracebacks for missing hours internally, but we handle
        # missing hours ourselves via the .grib attribute check below.
        herbie_fast_logger = logging.getLogger("herbie.fast")
        original_level = herbie_fast_logger.level
        herbie_fast_logger.setLevel(logging.CRITICAL)
        try:
            fh = FastHerbie(**kwargs)
        finally:
            herbie_fast_logger.setLevel(original_level)

        # Determine which fxx values have valid Herbie objects
        available_fxx: list[int] = []
        for h_obj in fh.objects:
            if h_obj.grib is not None:
                available_fxx.append(h_obj.fxx)

        if not available_fxx:
            logger.warning(f"No available forecast hours for {model_id}")
            return [], {}

        logger.info(
            f"FastHerbie found {len(available_fxx)}/{len(fxx_range)} "
            f"available hours for {model_id}"
        )

        # Load each variable dataset (concatenated across all available hours).
        # Suppress FutureWarning from xarray's combine_nested (herbie doesn't
        # pass coords= explicitly; fixed upstream eventually).
        #
        # Two storage paths:
        #   datasets[var]           — batch-loaded 3D dataset (step, y, x)
        #   per_hour_datasets[var]  — dict {fxx: 2D dataset} (fallback when
        #                             batch loading fails, e.g. accumulation
        #                             variables missing at fxx=0)
        datasets: dict[str, Any] = {}
        per_hour_datasets: dict[str, dict[int, Any]] = {}
        data_var_names: dict[str, str] = {}
        excluded_vars = MODEL_VARIABLE_EXCLUSIONS.get(model_id, set())

        var_search = get_variable_search(model_id)
        for var_name, search_str in var_search.items():
            if var_name in excluded_vars:
                logger.info(f"Skipping {var_name} for {model_id} (not available in product)")
                continue
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore", category=FutureWarning, module="herbie"
                    )
                    ds = fh.xarray(search_str)
                data_var = list(ds.data_vars)[0]
                datasets[var_name] = ds
                data_var_names[var_name] = data_var
            except KeyError as e:
                logger.warning(
                    f"Variable {var_name} missing source link for {model_id}: {e}. "
                    f"Data may not be published yet."
                )
            except Exception as e:
                # Batch xarray failed (e.g. accumulation variable missing at
                # fxx=0).  Fall back to per-hour loading so we don't lose
                # data for all the hours that DO have this variable.
                logger.debug(
                    f"Batch xarray failed for {var_name} ({model_id}): {e}. "
                    f"Falling back to per-hour loading."
                )
                hourly: dict[int, Any] = {}
                dvar_name: str | None = None
                for h_obj in fh.objects:
                    if h_obj.grib is None:
                        continue
                    try:
                        with warnings.catch_warnings():
                            warnings.filterwarnings(
                                "ignore", category=FutureWarning, module="herbie"
                            )
                            ds_h = h_obj.xarray(search_str)
                        if dvar_name is None:
                            dvar_name = list(ds_h.data_vars)[0]
                        hourly[h_obj.fxx] = ds_h
                    except Exception as per_hour_err:
                        logger.debug(
                            f"Per-hour fallback failed for {var_name} "
                            f"({model_id}) fxx={h_obj.fxx}: {per_hour_err}"
                        )
                if hourly and dvar_name is not None:
                    per_hour_datasets[var_name] = hourly
                    data_var_names[var_name] = dvar_name
                    logger.info(
                        f"Per-hour fallback loaded {var_name} for "
                        f"{len(hourly)}/{len(available_fxx)} hours ({model_id})"
                    )
                else:
                    logger.warning(
                        f"Variable {var_name} not available for {model_id} "
                        f"(batch failed: {e}; per-hour fallback: "
                        f"0/{len(available_fxx)} hours loaded)"
                    )

        # Build points dataframe and use pick_points for spatial extraction.
        # pick_points handles both projected (HRRR, NBM) and regular grids.
        points_df = pd.DataFrame({
            "latitude": [lat for lat, lon in points],
            "longitude": [lon for lat, lon in points],
        })

        # Extract point data for each available fxx by selecting each step
        # first (producing a 2D spatial dataset), then calling pick_points().
        # FastHerbie's fh.xarray() returns a 3D dataset (step, y, x) where
        # pick_points() fails because lat/lon gain an extra step dimension.
        all_loaded_vars = set(datasets) | set(per_hour_datasets)
        all_results: dict[int, list[dict[str, float | None]]] = {}

        for fxx in available_fxx:
            step = pd.Timedelta(hours=fxx)
            point_results: list[dict[str, float | None]] = []

            # pick_points per variable on 2D slice for this step
            picked_step: dict[str, Any] = {}
            for var_name in all_loaded_vars:
                try:
                    if var_name in datasets:
                        ds_2d = datasets[var_name].sel(step=step)
                    elif fxx in per_hour_datasets.get(var_name, {}):
                        # Per-hour dataset is already 2D (no step dim)
                        ds_2d = per_hour_datasets[var_name][fxx]
                    else:
                        continue
                    picked_step[var_name] = ds_2d.herbie.pick_points(
                        points_df, method="nearest"
                    )
                except Exception as e:
                    logger.warning(
                        f"pick_points failed for {var_name} ({model_id}) "
                        f"fxx={fxx}: {e}"
                    )

            for i in range(len(points)):
                point_data: dict[str, float | None] = {}

                for var_name in var_search:
                    if var_name not in picked_step:
                        point_data[var_name] = None
                        continue

                    try:
                        data_var = data_var_names[var_name]
                        fval = (
                            picked_step[var_name][data_var]
                            .isel(point=i)
                            .values.item()
                        )
                        if math.isnan(fval):
                            point_data[var_name] = None
                        else:
                            point_data[var_name] = fval
                    except Exception as e:
                        if i == 0:
                            logger.warning(
                                f"Value extraction failed for {var_name} "
                                f"({model_id}) fxx={fxx}: {e}"
                            )
                        point_data[var_name] = None

                point_results.append(point_data)

            all_results[fxx] = point_results

        return sorted(available_fxx), all_results

    def get_forecast(
        self,
        lat: float,
        lon: float,
        *,
        model: str = "gfs",
        elevation: float | None = None,
        temperature_unit: str = "C",
        wind_speed_unit: str = "kmh",
        precipitation_unit: str = "mm",
    ) -> Forecast:
        """Fetch a full forecast for a location via GRIB2 data.

        Downloads all forecast hours for the latest model run and assembles
        them into a Forecast dataclass.

        Args:
            lat: Latitude.
            lon: Longitude.
            model: Model ID.
            elevation: Optional elevation override in meters.
            temperature_unit: Not used (GRIB2 data is always metric internally).
            wind_speed_unit: Not used.
            precipitation_unit: Not used.

        Returns:
            A Forecast object with weather data.
        """
        model_id = validate_model_id(model)
        config = get_model_config(model_id)

        if not config.herbie_model:
            raise ModelError(
                f"Model '{model_id}' does not support Herbie/GRIB2 access",
                model_id=model_id,
            )

        # Determine latest model run time
        run_dt = self._get_latest_run_dt(config)
        fxx_range = get_fxx_range(config)

        logger.info(
            f"Fetching {model_id} forecast for ({lat}, {lon}), "
            f"run={run_dt.isoformat()}, fxx_count={len(fxx_range)}"
        )

        # Extract data for each forecast hour
        extracted_points: list[dict] = []
        times_utc: list[datetime] = []

        for fxx in fxx_range:
            try:
                point_data = self.extract_point(model_id, run_dt, fxx, lat, lon)
                extracted_points.append(point_data)

                valid_time = run_dt + timedelta(hours=fxx)
                if valid_time.tzinfo is None:
                    valid_time = valid_time.replace(tzinfo=timezone.utc)
                times_utc.append(valid_time)
            except Exception as e:
                logger.warning(f"Failed to extract fxx={fxx}: {e}")
                # Stop at first failure — don't leave gaps
                break

        if not extracted_points:
            raise ApiError(f"No data extracted for {model_id}")

        # Build hourly data from extracted points
        hourly_data, hourly_units = build_hourly_data(extracted_points, model_id)

        return Forecast(
            lat=lat,
            lon=lon,
            api_lat=lat,
            api_lon=lon,
            elevation_m=elevation,
            model_id=model_id,
            model_run_utc=run_dt.replace(tzinfo=timezone.utc) if run_dt.tzinfo is None else run_dt,
            times_utc=times_utc,
            hourly_data=hourly_data,
            hourly_units=hourly_units,
        )

    def _get_latest_run_dt(self, config: Any) -> datetime:
        """Determine the latest available model run datetime.

        Uses the model's update interval to find the most recent run that
        should be available (with a configurable buffer for data availability).

        Args:
            config: ModelConfig instance.

        Returns:
            Naive datetime of the latest model run.
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        buffer_hours = getattr(config, "availability_buffer_hours", 3)
        available_time = now - timedelta(hours=buffer_hours)

        interval = config.update_interval_hours
        # Round down to the nearest run hour
        run_hour = (available_time.hour // interval) * interval

        run_dt = available_time.replace(
            hour=run_hour, minute=0, second=0, microsecond=0
        )

        # Return naive datetime (Herbie expects this)
        return run_dt.replace(tzinfo=None)

    def get_candidate_run_dts(self, config: Any) -> list[datetime]:
        """Get a list of candidate model run datetimes to try, newest first.

        Returns the latest run plus the previous run as a fallback, so callers
        can retry with an older run if data hasn't been published yet.

        Args:
            config: ModelConfig instance.

        Returns:
            List of naive datetimes (newest first).
        """
        latest = self._get_latest_run_dt(config)
        previous = latest - timedelta(hours=config.update_interval_hours)
        return [latest, previous]
