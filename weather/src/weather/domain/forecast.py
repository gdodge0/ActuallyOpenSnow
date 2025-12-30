"""Forecast dataclass with getters and range logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Union

from weather.domain.quantities import Quantity, Series
from weather.domain.errors import RangeError
from weather.units.convert import convert_value, convert_series
from weather.units.normalize import normalize_unit
from weather.utils.geo import coords_are_equivalent
from weather.utils.time import slice_time_range, resolve_time_offset

TimeOffset = Union[datetime, timedelta]


@dataclass
class Forecast:
    """Weather forecast data for a location.

    Contains hourly forecast data, metadata, and methods for accessing
    weather variables with optional unit conversion.

    Attributes:
        lat: Requested latitude.
        lon: Requested longitude.
        api_lat: API-returned latitude (grid point).
        api_lon: API-returned longitude (grid point).
        elevation_m: Elevation in meters (from API or overridden).
        model_id: Forecast model identifier.
        model_run_utc: Model run timestamp in UTC.
        times_utc: List of hourly forecast timestamps.
        hourly_data: Dictionary of variable name -> raw values.
        hourly_units: Dictionary of variable name -> unit string.
    """

    lat: float
    lon: float
    api_lat: float
    api_lon: float
    elevation_m: float | None
    model_id: str
    model_run_utc: datetime | None
    times_utc: list[datetime]
    hourly_data: dict[str, tuple[float | None, ...]]
    hourly_units: dict[str, str]

    # Accumulated series (computed lazily)
    _snowfall_accumulated: tuple[float, ...] | None = field(default=None, repr=False)
    _precip_accumulated: tuple[float, ...] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate and normalize forecast data."""
        # Ensure times are in UTC
        if self.times_utc and self.times_utc[0].tzinfo is None:
            self.times_utc = [
                t.replace(tzinfo=timezone.utc) for t in self.times_utc
            ]

        # Ensure model_run_utc is in UTC
        if self.model_run_utc and self.model_run_utc.tzinfo is None:
            self.model_run_utc = self.model_run_utc.replace(tzinfo=timezone.utc)

    @property
    def hours_available(self) -> int:
        """Number of hourly timesteps in the forecast."""
        return len(self.times_utc)

    @property
    def forecast_start(self) -> datetime | None:
        """First timestamp in the forecast."""
        return self.times_utc[0] if self.times_utc else None

    @property
    def forecast_end(self) -> datetime | None:
        """Last timestamp in the forecast."""
        return self.times_utc[-1] if self.times_utc else None

    # -------------------------------------------------------------------------
    # Hourly series getters
    # -------------------------------------------------------------------------

    def _get_series(
        self,
        variable: str,
        unit: str | None = None,
    ) -> Series:
        """Get a variable's data as a Series with optional unit conversion.

        Args:
            variable: The variable name (e.g., "temperature_2m").
            unit: Optional target unit for conversion.

        Returns:
            A Series with the variable data.

        Raises:
            KeyError: If the variable is not in the forecast.
        """
        if variable not in self.hourly_data:
            available = ", ".join(sorted(self.hourly_data.keys()))
            raise KeyError(
                f"Variable '{variable}' not in forecast. Available: {available}"
            )

        raw_values = self.hourly_data[variable]
        raw_unit = self.hourly_units.get(variable, "undefined")

        series = Series(values=raw_values, unit=raw_unit)

        if unit is not None:
            target_unit = normalize_unit(unit)
            series = convert_series(series, target_unit)

        return series

    def get_temperature_2m(self, unit: str = "C") -> Series:
        """Get 2-meter temperature.

        Args:
            unit: Target unit (C, F, or K). Default is Celsius.

        Returns:
            Temperature series with specified unit.
        """
        return self._get_series("temperature_2m", unit)

    def get_wind_speed_10m(self, unit: str = "kmh") -> Series:
        """Get 10-meter wind speed.

        Args:
            unit: Target unit (kmh, ms, mph, or kn). Default is km/h.

        Returns:
            Wind speed series with specified unit.
        """
        return self._get_series("wind_speed_10m", unit)

    def get_wind_gusts_10m(self, unit: str = "kmh") -> Series:
        """Get 10-meter wind gusts.

        Args:
            unit: Target unit (kmh, ms, mph, or kn). Default is km/h.

        Returns:
            Wind gust series with specified unit.
        """
        return self._get_series("wind_gusts_10m", unit)

    def get_snowfall(self, unit: str = "cm") -> Series:
        """Get hourly snowfall.

        Args:
            unit: Target unit (mm, cm, in, or ft). Default is cm.

        Returns:
            Snowfall series with specified unit.
        """
        return self._get_series("snowfall", unit)

    def get_precipitation(self, unit: str = "mm") -> Series:
        """Get hourly precipitation.

        Args:
            unit: Target unit (mm, cm, in, or ft). Default is mm.

        Returns:
            Precipitation series with specified unit.
        """
        return self._get_series("precipitation", unit)

    def get_freezing_level_height(self, unit: str = "m") -> Series:
        """Get freezing level height (snow level proxy).

        Args:
            unit: Target unit (m or ft). Default is meters.

        Returns:
            Freezing level height series with specified unit.
        """
        return self._get_series("freezing_level_height", unit)

    # -------------------------------------------------------------------------
    # Accumulated series
    # -------------------------------------------------------------------------

    def _compute_accumulated(self, variable: str) -> tuple[float, ...]:
        """Compute cumulative sum for a variable."""
        if variable not in self.hourly_data:
            raise KeyError(f"Variable '{variable}' not in forecast")

        values = self.hourly_data[variable]
        accumulated = []
        total = 0.0

        for v in values:
            if v is not None:
                total += v
            accumulated.append(total)

        return tuple(accumulated)

    def get_snowfall_accumulated(self, unit: str = "cm") -> Series:
        """Get cumulative snowfall.

        Args:
            unit: Target unit (mm, cm, in, or ft). Default is cm.

        Returns:
            Accumulated snowfall series with specified unit.
        """
        if self._snowfall_accumulated is None:
            self._snowfall_accumulated = self._compute_accumulated("snowfall")

        raw_unit = self.hourly_units.get("snowfall", "cm")
        series = Series(values=self._snowfall_accumulated, unit=raw_unit)

        if unit is not None:
            target_unit = normalize_unit(unit)
            series = convert_series(series, target_unit)

        return series

    def get_precipitation_accumulated(self, unit: str = "mm") -> Series:
        """Get cumulative precipitation.

        Args:
            unit: Target unit (mm, cm, in, or ft). Default is mm.

        Returns:
            Accumulated precipitation series with specified unit.
        """
        if self._precip_accumulated is None:
            self._precip_accumulated = self._compute_accumulated("precipitation")

        raw_unit = self.hourly_units.get("precipitation", "mm")
        series = Series(values=self._precip_accumulated, unit=raw_unit)

        if unit is not None:
            target_unit = normalize_unit(unit)
            series = convert_series(series, target_unit)

        return series

    # -------------------------------------------------------------------------
    # Range totals
    # -------------------------------------------------------------------------

    def _get_range_total(
        self,
        variable: str,
        unit: str,
        start: TimeOffset | None,
        end: TimeOffset | None,
    ) -> Quantity:
        """Get the total of a variable over a time range.

        Args:
            variable: The variable name.
            unit: Target unit for the result.
            start: Start of range (datetime or timedelta). Default is forecast start.
            end: End of range (datetime or timedelta). Default is forecast end.

        Returns:
            A Quantity with the total value in the specified unit.
        """
        if not self.times_utc:
            raise RangeError("No forecast data available")

        # Default to full range
        if start is None:
            start = timedelta(0)
        if end is None:
            end = timedelta(hours=len(self.times_utc))

        # Get indices for the range
        start_idx, end_idx = slice_time_range(start, end, self.times_utc)

        # Get the variable data
        if variable not in self.hourly_data:
            raise KeyError(f"Variable '{variable}' not in forecast")

        values = self.hourly_data[variable]
        raw_unit = self.hourly_units.get(variable, "undefined")

        # Sum values in range
        range_values = values[start_idx:end_idx]
        total = sum(v for v in range_values if v is not None)

        # Convert unit if needed
        target_unit = normalize_unit(unit)
        from_unit = normalize_unit(raw_unit)

        if from_unit != target_unit:
            total = convert_value(total, from_unit, target_unit)

        return Quantity(value=total, unit=target_unit)

    def get_snowfall_total(
        self,
        unit: str = "cm",
        start: TimeOffset | None = None,
        end: TimeOffset | None = None,
    ) -> Quantity:
        """Get total snowfall over a time range.

        Args:
            unit: Target unit (mm, cm, in, or ft). Default is cm.
            start: Start of range (datetime or timedelta). Default is forecast start.
            end: End of range (datetime or timedelta). Default is forecast end.

        Returns:
            A Quantity with the total snowfall.
        """
        return self._get_range_total("snowfall", unit, start, end)

    def get_precipitation_total(
        self,
        unit: str = "mm",
        start: TimeOffset | None = None,
        end: TimeOffset | None = None,
    ) -> Quantity:
        """Get total precipitation over a time range.

        Args:
            unit: Target unit (mm, cm, in, or ft). Default is mm.
            start: Start of range (datetime or timedelta). Default is forecast start.
            end: End of range (datetime or timedelta). Default is forecast end.

        Returns:
            A Quantity with the total precipitation.
        """
        return self._get_range_total("precipitation", unit, start, end)

    # -------------------------------------------------------------------------
    # Equivalence
    # -------------------------------------------------------------------------

    def is_equivalent(self, other: Forecast, threshold_meters: float = 100.0) -> bool:
        """Check if this forecast is equivalent to another.

        Two forecasts are equivalent if they:
        - Are within threshold distance (default 100m)
        - Use the same model
        - Have the same model run time

        Args:
            other: Another Forecast to compare.
            threshold_meters: Maximum distance in meters for equivalence.

        Returns:
            True if forecasts are equivalent.
        """
        # Check model
        if self.model_id != other.model_id:
            return False

        # Check model run time
        if self.model_run_utc != other.model_run_utc:
            return False

        # Check location using API-returned coordinates
        return coords_are_equivalent(
            self.api_lat,
            self.api_lon,
            other.api_lat,
            other.api_lon,
            threshold_meters=threshold_meters,
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on full data match."""
        if not isinstance(other, Forecast):
            return NotImplemented

        return (
            self.lat == other.lat
            and self.lon == other.lon
            and self.api_lat == other.api_lat
            and self.api_lon == other.api_lon
            and self.model_id == other.model_id
            and self.model_run_utc == other.model_run_utc
            and self.times_utc == other.times_utc
            and self.hourly_data == other.hourly_data
        )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert forecast to a dictionary for JSON serialization.

        Returns:
            Dictionary representation of the forecast.
        """
        return {
            "lat": self.lat,
            "lon": self.lon,
            "api_lat": self.api_lat,
            "api_lon": self.api_lon,
            "elevation_m": self.elevation_m,
            "model_id": self.model_id,
            "model_run_utc": (
                self.model_run_utc.isoformat() if self.model_run_utc else None
            ),
            "times_utc": [t.isoformat() for t in self.times_utc],
            "hourly_data": {k: list(v) for k, v in self.hourly_data.items()},
            "hourly_units": self.hourly_units,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Forecast:
        """Create a Forecast from a dictionary.

        Args:
            data: Dictionary representation (from to_dict).

        Returns:
            A Forecast instance.
        """
        model_run = data.get("model_run_utc")
        if model_run and isinstance(model_run, str):
            model_run = datetime.fromisoformat(model_run)

        times = data.get("times_utc", [])
        if times and isinstance(times[0], str):
            times = [datetime.fromisoformat(t) for t in times]

        hourly_data = {
            k: tuple(v) for k, v in data.get("hourly_data", {}).items()
        }

        return cls(
            lat=data["lat"],
            lon=data["lon"],
            api_lat=data["api_lat"],
            api_lon=data["api_lon"],
            elevation_m=data.get("elevation_m"),
            model_id=data["model_id"],
            model_run_utc=model_run,
            times_utc=times,
            hourly_data=hourly_data,
            hourly_units=data.get("hourly_units", {}),
        )

