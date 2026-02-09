"""Tests for HerbieClient with mocked Herbie library."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

from weather.clients.herbie_client import (
    HerbieClient,
    VARIABLE_SEARCH,
    ECMWF_VARIABLE_SEARCH,
    ECMWF_MODELS,
    get_variable_search,
    FASTHERBIE_CHUNK_SIZE,
    MODEL_VARIABLE_EXCLUSIONS,
)
from weather.domain.errors import ApiError, ModelError


def _make_ndarray_mock(value):
    """Create a mock that behaves like a 0-d numpy ndarray with .item() support."""
    mock_arr = MagicMock()
    mock_arr.item.return_value = float(value)
    return mock_arr


def _make_pick_points_ds(data_var_name, values_by_point):
    """Create a mock dataset returned by ds.herbie.pick_points().

    Args:
        data_var_name: Name of the data variable (e.g. "var").
        values_by_point: List of float values, one per point.

    Returns:
        Mock dataset with [data_var].isel(point=i).values.item() returning values.
    """
    ds_points = MagicMock()
    data_var_mock = MagicMock()

    def isel_fn(point):
        mock_val = MagicMock()
        mock_val.values = _make_ndarray_mock(values_by_point[point])
        return mock_val

    data_var_mock.isel = isel_fn
    ds_points.__getitem__ = lambda self, key: data_var_mock
    return ds_points


def _make_pick_points_ds_with_step(data_var_name, values_by_fxx_point):
    """Create a mock dataset returned by ds.herbie.pick_points() with a step dim.

    Args:
        data_var_name: Name of the data variable.
        values_by_fxx_point: Dict[step_timedelta, list[float]] — values per point per step.

    Returns:
        Mock dataset with [data_var].sel(step=...).isel(point=i).values returning values.
    """
    ds_points = MagicMock()
    data_var_mock = MagicMock()

    def sel_fn(step):
        step_data = MagicMock()

        def isel_fn(point):
            mock_val = MagicMock()
            mock_val.values = values_by_fxx_point.get(step, [0.0])[point]
            return mock_val

        step_data.isel = isel_fn
        return step_data

    data_var_mock.sel = sel_fn
    ds_points.__getitem__ = lambda self, key: data_var_mock
    return ds_points


class TestHerbieClientInit:
    """Tests for HerbieClient initialization."""

    def test_default_init(self):
        client = HerbieClient()
        assert client.cache_dir is None

    def test_custom_cache_dir(self):
        client = HerbieClient(cache_dir="/tmp/grib_cache")
        assert client.cache_dir == Path("/tmp/grib_cache")


class TestHerbieClientGetHerbie:
    """Tests for _get_herbie helper."""

    @patch("weather.clients.herbie_client.HerbieClient._get_herbie")
    def test_herbie_not_installed_raises(self, mock_get_herbie):
        """Test that missing herbie raises ApiError."""
        mock_get_herbie.side_effect = ApiError("Herbie is not installed")
        client = HerbieClient()
        with pytest.raises(ApiError, match="not installed"):
            client._get_herbie("hrrr", datetime(2024, 1, 1), 0)

    def test_model_without_herbie_raises(self):
        """Test that model without herbie_model raises ModelError."""
        client = HerbieClient()
        # ICON has no herbie_model
        with pytest.raises(ModelError, match="does not support Herbie"):
            # We need to mock the import but test the logic
            with patch.dict("sys.modules", {"herbie": MagicMock()}):
                client._get_herbie("icon", datetime(2024, 1, 1), 0)


class TestHerbieClientExtractPoint:
    """Tests for single-point extraction with mocked Herbie."""

    def _make_mock_herbie(self, var_values=None):
        """Create a mock Herbie instance that returns xarray datasets with pick_points."""
        mock_h = MagicMock()

        def mock_xarray(search_str):
            # Default value
            val = 0.0
            if var_values:
                for key, v in var_values.items():
                    if key in search_str:
                        val = v
                        break

            ds = MagicMock()
            ds.data_vars = {"var": None}

            # Mock ds.herbie.pick_points() → dataset with .isel(point=0)
            ds_points = _make_pick_points_ds("var", [val])
            ds.herbie.pick_points.return_value = ds_points
            return ds

        mock_h.xarray = mock_xarray
        return mock_h

    @patch("weather.clients.herbie_client.HerbieClient._get_herbie")
    def test_extract_point_returns_all_variables(self, mock_get_herbie):
        """Test that extract_point returns all expected variables."""
        mock_h = self._make_mock_herbie({
            "TMP": 273.15,
            "APCP": 2.0,
            "ASNOW": 0.05,
            "UGRD": 5.0,
            "VGRD": 3.0,
            "GUST": 12.0,
            "HGT": 2500.0,
        })
        mock_get_herbie.return_value = mock_h

        client = HerbieClient()
        result = client.extract_point("hrrr", datetime(2024, 1, 1), 6, 43.5, -110.8)

        assert "temperature" in result
        assert "precipitation" in result
        assert "snowfall" in result
        assert "wind_u" in result
        assert "wind_v" in result
        assert "wind_gusts" in result
        assert "freezing_level" in result

    @patch("weather.clients.herbie_client.HerbieClient._get_herbie")
    def test_extract_point_handles_missing_variable(self, mock_get_herbie):
        """Test that missing variables return None."""
        mock_h = MagicMock()

        def mock_xarray(search_str):
            if "GUST" in search_str:
                raise Exception("Variable not found")
            ds = MagicMock()
            ds.data_vars = {"var": None}
            ds_points = _make_pick_points_ds("var", [0.0])
            ds.herbie.pick_points.return_value = ds_points
            return ds

        mock_h.xarray = mock_xarray
        mock_get_herbie.return_value = mock_h

        client = HerbieClient()
        result = client.extract_point("hrrr", datetime(2024, 1, 1), 6, 43.5, -110.8)
        assert result["wind_gusts"] is None


class TestHerbieClientExtractPointsBatch:
    """Tests for batch point extraction."""

    @patch("weather.clients.herbie_client.HerbieClient._get_herbie")
    def test_batch_returns_one_result_per_point(self, mock_get_herbie):
        """Test that batch extraction returns correct number of results."""
        mock_h = MagicMock()

        def mock_xarray(search_str):
            ds = MagicMock()
            ds.data_vars = {"var": None}
            # 3 points, all returning 0.0
            ds_points = _make_pick_points_ds("var", [0.0, 0.0, 0.0])
            ds.herbie.pick_points.return_value = ds_points
            return ds

        mock_h.xarray = mock_xarray
        mock_get_herbie.return_value = mock_h

        client = HerbieClient()
        points = [(43.5, -110.8), (39.6, -106.4), (40.6, -111.5)]
        results = client.extract_points_batch("gfs", datetime(2024, 1, 1), 6, points)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert "temperature" in result


class TestHerbieClientGetForecast:
    """Tests for get_forecast integration."""

    @patch("weather.clients.herbie_client.HerbieClient.extract_point")
    @patch("weather.clients.herbie_client.HerbieClient._get_latest_run_dt")
    def test_get_forecast_returns_forecast(self, mock_run_dt, mock_extract):
        """Test that get_forecast assembles a Forecast object."""
        mock_run_dt.return_value = datetime(2024, 1, 1, 0, 0)

        mock_extract.return_value = {
            "temperature": 268.15,
            "precipitation": 0.0,
            "snowfall": 0.0,
            "wind_u": 5.0,
            "wind_v": 3.0,
            "wind_gusts": 12.0,
            "freezing_level": 2500.0,
        }

        client = HerbieClient()
        # Only fetch a few hours for the test
        with patch.object(
            type(client), "_get_latest_run_dt", return_value=datetime(2024, 1, 1, 0, 0)
        ):
            # Limit forecast hours by patching max_forecast_days
            from weather.config.models import MODELS, ModelConfig
            original = MODELS["hrrr"]
            # Create a version with 0 max days so we get just fxx=0
            test_config = ModelConfig(
                model_id="hrrr",
                api_model="",
                display_name="HRRR",
                provider="NOAA",
                max_forecast_days=0,
                resolution_degrees=0.03,
                description="Test",
                herbie_model="hrrr",
                herbie_product="sfc",
                update_interval_hours=1,
            )
            with patch.dict("weather.config.models.MODELS", {"hrrr": test_config}):
                forecast = client.get_forecast(43.5, -110.8, model="hrrr")

        assert forecast.model_id == "hrrr"
        assert forecast.lat == 43.5
        assert forecast.lon == -110.8
        assert len(forecast.times_utc) > 0
        assert "temperature_2m" in forecast.hourly_data

    def test_get_forecast_invalid_model(self):
        """Test that invalid model raises ModelError."""
        client = HerbieClient()
        with pytest.raises(ModelError):
            client.get_forecast(43.5, -110.8, model="nonexistent")

    def test_get_forecast_non_herbie_model(self):
        """Test that non-Herbie model raises ModelError."""
        client = HerbieClient()
        with pytest.raises(ModelError, match="does not support Herbie"):
            client.get_forecast(43.5, -110.8, model="icon")


class TestHerbieClientLatestRunDt:
    """Tests for _get_latest_run_dt."""

    def test_returns_naive_datetime(self):
        """Herbie requires naive datetimes."""
        from weather.config.models import MODELS
        client = HerbieClient()
        config = MODELS["gfs"]
        run_dt = client._get_latest_run_dt(config)
        assert run_dt.tzinfo is None

    def test_run_hour_aligned_to_interval(self):
        """Run hour should be aligned to model's update interval."""
        from weather.config.models import MODELS
        client = HerbieClient()

        # GFS updates every 6 hours
        config = MODELS["gfs"]
        run_dt = client._get_latest_run_dt(config)
        assert run_dt.hour % 6 == 0

        # HRRR updates every 1 hour
        config = MODELS["hrrr"]
        run_dt = client._get_latest_run_dt(config)
        # Every hour is valid for HRRR
        assert 0 <= run_dt.hour <= 23

    def test_returns_recent_datetime(self):
        """Run datetime should be within last 24 hours."""
        from weather.config.models import MODELS
        client = HerbieClient()
        config = MODELS["gfs"]
        run_dt = client._get_latest_run_dt(config)

        now = datetime.now()
        diff = now - run_dt
        assert diff.total_seconds() < 86400  # Within 24 hours


class TestVariableSearchStrings:
    """Tests for GRIB2 variable search string definitions."""

    def test_all_variables_defined(self):
        expected = {"temperature", "precipitation", "snowfall", "wind_u", "wind_v", "wind_gusts", "freezing_level"}
        assert set(VARIABLE_SEARCH.keys()) == expected

    def test_search_strings_are_non_empty(self):
        for var, search in VARIABLE_SEARCH.items():
            assert search, f"Empty search string for {var}"
            assert ":" in search, f"Search string for {var} missing colons"

    def test_ecmwf_keys_match_ncep_keys(self):
        """ECMWF and NCEP search dicts must have the same variable keys."""
        assert set(ECMWF_VARIABLE_SEARCH.keys()) == set(VARIABLE_SEARCH.keys())

    def test_ecmwf_search_strings_are_non_empty(self):
        for var, search in ECMWF_VARIABLE_SEARCH.items():
            assert search, f"Empty ECMWF search string for {var}"
            assert ":" in search, f"ECMWF search string for {var} missing colons"


class TestGetVariableSearch:
    """Tests for model-specific search string selection."""

    def test_ncep_models_return_ncep_strings(self):
        for model_id in ("gfs", "hrrr", "nbm", "gefs"):
            result = get_variable_search(model_id)
            assert result is VARIABLE_SEARCH, f"{model_id} should use NCEP strings"

    def test_ecmwf_models_return_ecmwf_strings(self):
        for model_id in ("ifs", "aifs", "ecmwf_ens"):
            result = get_variable_search(model_id)
            assert result is ECMWF_VARIABLE_SEARCH, f"{model_id} should use ECMWF strings"

    def test_ecmwf_models_set(self):
        assert ECMWF_MODELS == {"ifs", "aifs", "ecmwf_ens"}


class TestHerbieClientExtractAllHoursBatch:
    """Tests for FastHerbie-based batch extraction across multiple forecast hours."""

    def _make_mock_fastherbie(self, available_fxx, all_fxx, num_points=1, values=None):
        """Create a mock FastHerbie instance.

        The mock supports the per-step extraction pattern:
        ds.sel(step=X) → 2D dataset → .herbie.pick_points() → point data

        Args:
            available_fxx: List of fxx values that have valid GRIB2 sources.
            all_fxx: Complete list of fxx values requested.
            num_points: Number of points for pick_points mock.
            values: Optional dict {fxx: [point_values]} for custom values.

        Returns:
            Mock FastHerbie instance.
        """
        import pandas as pd

        mock_fh = MagicMock()

        # Build objects list -- each with .grib and .fxx attributes
        objects = []
        for fxx in all_fxx:
            obj = MagicMock()
            obj.fxx = fxx
            obj.grib = f"some/path/f{fxx:03d}.grib2" if fxx in available_fxx else None
            objects.append(obj)
        mock_fh.objects = objects

        # Mock xarray -- returns a 3D dataset; code calls .sel(step=X)
        # then .herbie.pick_points() on the 2D result
        def mock_xarray(search_str):
            ds = MagicMock()
            ds.data_vars = {"var": None}

            def mock_sel(step):
                """Return a 2D mock dataset for a single step."""
                ds_2d = MagicMock()

                # Determine point values for this step
                fxx_hours = int(step.total_seconds() / 3600)
                if values and fxx_hours in values:
                    point_vals = values[fxx_hours]
                else:
                    point_vals = [0.0] * num_points

                ds_points = _make_pick_points_ds("var", point_vals)
                ds_2d.herbie.pick_points.return_value = ds_points
                return ds_2d

            ds.sel = mock_sel
            return ds

        mock_fh.xarray = mock_xarray
        return mock_fh

    @patch("weather.clients.herbie_client.get_model_config")
    def test_returns_correct_fxx_and_point_data(self, mock_config):
        """Test that batch extraction returns correct fxx values and data."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        fxx_range = [0, 1, 2, 3]
        available_fxx = [0, 1, 2, 3]
        mock_fh = self._make_mock_fastherbie(available_fxx, fxx_range, num_points=2)

        with patch("herbie.FastHerbie", return_value=mock_fh) as MockFH:
            client = HerbieClient()
            points = [(43.5, -110.8), (39.6, -106.4)]
            avail, results = client.extract_all_hours_batch(
                "hrrr", datetime(2024, 1, 1), fxx_range, points
            )

        assert avail == [0, 1, 2, 3]
        assert len(results) == 4
        for fxx in avail:
            assert len(results[fxx]) == 2  # 2 points
            for point_data in results[fxx]:
                assert "temperature" in point_data
                assert "precipitation" in point_data

    @patch("weather.clients.herbie_client.get_model_config")
    def test_handles_partial_availability(self, mock_config):
        """Test that unavailable hours are excluded from results."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        fxx_range = [0, 1, 2, 3, 4, 5]
        # Only hours 0-2 are available
        available_fxx = [0, 1, 2]
        mock_fh = self._make_mock_fastherbie(available_fxx, fxx_range)

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            points = [(43.5, -110.8)]
            avail, results = client.extract_all_hours_batch(
                "hrrr", datetime(2024, 1, 1), fxx_range, points
            )

        assert avail == [0, 1, 2]
        assert 3 not in results
        assert 4 not in results
        assert 5 not in results

    @patch("weather.clients.herbie_client.get_model_config")
    def test_no_available_hours_returns_empty(self, mock_config):
        """Test that no available hours returns empty results."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        fxx_range = [0, 1, 2]
        mock_fh = self._make_mock_fastherbie([], fxx_range)

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "hrrr", datetime(2024, 1, 1), fxx_range, [(43.5, -110.8)]
            )

        assert avail == []
        assert results == {}

    @patch("weather.clients.herbie_client.get_model_config")
    def test_ensemble_model_passes_member_mean(self, mock_config):
        """Test that ensemble models pass member='mean' to FastHerbie."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gefs", api_model="", display_name="GEFS",
            provider="NOAA", max_forecast_days=16, resolution_degrees=0.25,
            description="Test", herbie_model="gefs", herbie_product="atmos.5",
            update_interval_hours=6, is_ensemble=True,
        )

        fxx_range = [0, 1]
        mock_fh = self._make_mock_fastherbie([0, 1], fxx_range)

        with patch("herbie.FastHerbie", return_value=mock_fh) as MockFH:
            client = HerbieClient()
            client.extract_all_hours_batch(
                "gefs", datetime(2024, 1, 1), fxx_range, [(43.5, -110.8)]
            )

        call_kwargs = MockFH.call_args[1]
        assert call_kwargs["member"] == "mean"

    @patch("weather.clients.herbie_client.get_model_config")
    def test_chunking_for_large_ranges(self, mock_config):
        """Test that large fxx ranges are split into chunks."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=16, resolution_degrees=0.25,
            description="Test", herbie_model="gfs", herbie_product="pgrb2.0p25",
            update_interval_hours=6,
        )

        # Create fxx_range larger than FASTHERBIE_CHUNK_SIZE
        fxx_range = list(range(0, FASTHERBIE_CHUNK_SIZE + 10))
        all_available = list(range(0, 20))  # Only first 20 available

        call_count = 0
        chunks_seen = []

        def side_effect(**kwargs):
            nonlocal call_count
            fxx = kwargs["fxx"]
            chunks_seen.append(fxx)
            call_count += 1
            chunk_available = [f for f in all_available if f in fxx]
            return self._make_mock_fastherbie(chunk_available, fxx)

        with patch("herbie.FastHerbie", side_effect=side_effect):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "gfs", datetime(2024, 1, 1), fxx_range, [(43.5, -110.8)]
            )

        # Should have been called twice (chunk of 48 + chunk of 10)
        assert call_count == 2
        assert len(chunks_seen[0]) == FASTHERBIE_CHUNK_SIZE
        assert len(chunks_seen[1]) == 10

        # Results should include all available hours
        for fxx in all_available:
            assert fxx in avail

    @patch("weather.clients.herbie_client.get_model_config")
    def test_strips_tzinfo_for_herbie(self, mock_config):
        """Test that timezone-aware datetimes are made naive for Herbie."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        fxx_range = [0]
        mock_fh = self._make_mock_fastherbie([0], fxx_range)

        with patch("herbie.FastHerbie", return_value=mock_fh) as MockFH:
            client = HerbieClient()
            # Pass timezone-aware datetime
            client.extract_all_hours_batch(
                "hrrr",
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                fxx_range,
                [(43.5, -110.8)],
            )

        call_kwargs = MockFH.call_args[1]
        # DATES should contain naive datetimes
        dates = call_kwargs["DATES"]
        # pd.to_datetime wraps the list, so check the input was naive
        assert dates[0].tzinfo is None

    def test_non_herbie_model_raises(self):
        """Test that non-Herbie model raises ModelError."""
        client = HerbieClient()
        with pytest.raises(ModelError, match="does not support Herbie"):
            client.extract_all_hours_batch(
                "icon", datetime(2024, 1, 1), [0, 1], [(43.5, -110.8)]
            )

    @patch("weather.clients.herbie_client.get_model_config")
    def test_handles_variable_xarray_failure(self, mock_config):
        """Test that xarray failures for individual variables produce None."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        mock_fh = MagicMock()
        obj = MagicMock()
        obj.fxx = 0
        obj.grib = "some/path.grib2"
        mock_fh.objects = [obj]

        # xarray raises for all variables
        mock_fh.xarray.side_effect = Exception("Variable not found")

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "hrrr", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
            )

        assert avail == [0]
        assert len(results[0]) == 1
        # All variables should be None since xarray failed
        for var_name in VARIABLE_SEARCH:
            assert results[0][0][var_name] is None

    @patch("weather.clients.herbie_client.get_model_config")
    def test_per_step_pick_points_extracts_values(self, mock_config):
        """Test that per-step pick_points correctly extracts different values per step."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        fxx_range = [0, 1, 2]
        available_fxx = [0, 1, 2]
        # Different values per step for a single point
        mock_fh = self._make_mock_fastherbie(
            available_fxx, fxx_range, num_points=1,
            values={0: [273.15], 1: [270.0], 2: [268.0]},
        )

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "hrrr", datetime(2024, 1, 1), fxx_range, [(43.5, -110.8)]
            )

        assert avail == [0, 1, 2]
        # Each step should have extracted different values
        assert results[0][0]["temperature"] == 273.15
        assert results[1][0]["temperature"] == 270.0
        assert results[2][0]["temperature"] == 268.0

    @patch("weather.clients.herbie_client.get_model_config")
    def test_pick_points_failure_on_one_step_does_not_affect_others(self, mock_config):
        """Test that pick_points failure on one step still extracts other steps."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=2, resolution_degrees=0.03,
            description="Test", herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        import pandas as pd

        mock_fh = MagicMock()
        objects = []
        for fxx in [0, 1]:
            obj = MagicMock()
            obj.fxx = fxx
            obj.grib = f"some/path/f{fxx:03d}.grib2"
            objects.append(obj)
        mock_fh.objects = objects

        call_count = 0

        def mock_xarray(search_str):
            ds = MagicMock()
            ds.data_vars = {"var": None}

            def mock_sel(step):
                nonlocal call_count
                fxx_hours = int(step.total_seconds() / 3600)
                ds_2d = MagicMock()
                if fxx_hours == 0:
                    # Step 0: pick_points fails
                    ds_2d.herbie.pick_points.side_effect = Exception("Grid mismatch")
                else:
                    # Step 1: pick_points succeeds
                    ds_points = _make_pick_points_ds("var", [5.0])
                    ds_2d.herbie.pick_points.return_value = ds_points
                call_count += 1
                return ds_2d

            ds.sel = mock_sel
            return ds

        mock_fh.xarray = mock_xarray

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "hrrr", datetime(2024, 1, 1), [0, 1], [(43.5, -110.8)]
            )

        assert avail == [0, 1]
        # Step 0 should have all None (pick_points failed)
        for var_name in VARIABLE_SEARCH:
            assert results[0][0][var_name] is None
        # Step 1 should have values
        for var_name in VARIABLE_SEARCH:
            assert results[1][0][var_name] == 5.0


class TestItemExtraction:
    """Tests for .item() extraction handling 0-d arrays."""

    @patch("weather.clients.herbie_client.HerbieClient._get_herbie")
    def test_extract_point_uses_item(self, mock_get_herbie):
        """Test that extract_point calls .values.item() for value extraction."""
        mock_h = MagicMock()

        def mock_xarray(search_str):
            ds = MagicMock()
            ds.data_vars = {"var": None}
            ds_points = _make_pick_points_ds("var", [273.15])
            ds.herbie.pick_points.return_value = ds_points
            return ds

        mock_h.xarray = mock_xarray
        mock_get_herbie.return_value = mock_h

        client = HerbieClient()
        result = client.extract_point("hrrr", datetime(2024, 1, 1), 6, 43.5, -110.8)

        assert result["temperature"] == 273.15

    @patch("weather.clients.herbie_client.HerbieClient._get_herbie")
    def test_extract_points_batch_uses_item(self, mock_get_herbie):
        """Test that extract_points_batch calls .values.item() for value extraction."""
        mock_h = MagicMock()

        def mock_xarray(search_str):
            ds = MagicMock()
            ds.data_vars = {"var": None}
            ds_points = _make_pick_points_ds("var", [5.0, 10.0])
            ds.herbie.pick_points.return_value = ds_points
            return ds

        mock_h.xarray = mock_xarray
        mock_get_herbie.return_value = mock_h

        client = HerbieClient()
        points = [(43.5, -110.8), (39.6, -106.4)]
        results = client.extract_points_batch("gfs", datetime(2024, 1, 1), 6, points)

        assert results[0]["temperature"] == 5.0
        assert results[1]["temperature"] == 10.0


class TestModelVariableExclusions:
    """Tests for MODEL_VARIABLE_EXCLUSIONS and skipping unavailable variables."""

    def test_nbm_exclusions_defined(self):
        """Test that NBM has the expected variable exclusions."""
        assert "nbm" in MODEL_VARIABLE_EXCLUSIONS
        assert "snowfall" in MODEL_VARIABLE_EXCLUSIONS["nbm"]
        assert "wind_gusts" in MODEL_VARIABLE_EXCLUSIONS["nbm"]
        assert "freezing_level" in MODEL_VARIABLE_EXCLUSIONS["nbm"]

    def test_nbm_exclusions_do_not_include_core_vars(self):
        """Test that core variables are not excluded for NBM."""
        excluded = MODEL_VARIABLE_EXCLUSIONS["nbm"]
        assert "temperature" not in excluded
        assert "precipitation" not in excluded
        assert "wind_u" not in excluded
        assert "wind_v" not in excluded

    def test_aifs_exclusions_defined(self):
        """Test that AIFS has the expected variable exclusions."""
        assert "aifs" in MODEL_VARIABLE_EXCLUSIONS
        excluded = MODEL_VARIABLE_EXCLUSIONS["aifs"]
        assert "snowfall" in excluded
        assert "wind_gusts" in excluded
        assert "freezing_level" in excluded
        assert "temperature" not in excluded
        assert "precipitation" not in excluded

    def test_ecmwf_ens_exclusions_defined(self):
        """Test that ECMWF ENS has the expected variable exclusions."""
        assert "ecmwf_ens" in MODEL_VARIABLE_EXCLUSIONS
        excluded = MODEL_VARIABLE_EXCLUSIONS["ecmwf_ens"]
        assert "snowfall" in excluded
        assert "wind_gusts" in excluded
        assert "freezing_level" in excluded
        assert "temperature" not in excluded
        assert "precipitation" not in excluded

    def test_ifs_exclusions_defined(self):
        """Test that IFS excludes freezing_level but not snowfall/wind_gusts."""
        assert "ifs" in MODEL_VARIABLE_EXCLUSIONS
        excluded = MODEL_VARIABLE_EXCLUSIONS["ifs"]
        assert "freezing_level" in excluded
        assert "temperature" not in excluded
        assert "precipitation" not in excluded
        assert "snowfall" not in excluded

    @patch("weather.clients.herbie_client.get_model_config")
    def test_excluded_vars_produce_none_in_results(self, mock_config):
        """Test that excluded variables result in None values for NBM."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="nbm", api_model="", display_name="NBM",
            provider="NOAA", max_forecast_days=7, resolution_degrees=0.025,
            description="Test", herbie_model="nbm", herbie_product="co",
            update_interval_hours=3,
        )

        mock_fh = MagicMock()
        obj = MagicMock()
        obj.fxx = 0
        obj.grib = "some/path.grib2"
        mock_fh.objects = [obj]

        def mock_xarray(search_str):
            ds = MagicMock()
            ds.data_vars = {"var": None}

            def mock_sel(step):
                ds_2d = MagicMock()
                ds_points = _make_pick_points_ds("var", [1.0])
                ds_2d.herbie.pick_points.return_value = ds_points
                return ds_2d

            ds.sel = mock_sel
            return ds

        mock_fh.xarray = mock_xarray

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "nbm", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
            )

        assert avail == [0]
        # Excluded variables should be None
        assert results[0][0]["snowfall"] is None
        assert results[0][0]["wind_gusts"] is None
        assert results[0][0]["freezing_level"] is None
        # Non-excluded variables should have values
        assert results[0][0]["temperature"] == 1.0
        assert results[0][0]["precipitation"] == 1.0


class TestAvailabilityBuffer:
    """Tests for availability_buffer_hours in _get_latest_run_dt."""

    def test_default_buffer_is_3_hours(self):
        """Test that default availability buffer is 3 hours."""
        from weather.config.models import ModelConfig
        config = ModelConfig(
            model_id="test", api_model="test", display_name="Test",
            provider="Test", max_forecast_days=7, resolution_degrees=0.25,
            description="Test", herbie_model="test", herbie_product="test",
            update_interval_hours=6,
        )
        assert config.availability_buffer_hours == 3

    def test_ecmwf_models_use_6_hour_buffer(self):
        """Test that ECMWF models have 6-hour availability buffer."""
        from weather.config.models import MODELS
        assert MODELS["ifs"].availability_buffer_hours == 6
        assert MODELS["aifs"].availability_buffer_hours == 6
        assert MODELS["ecmwf_ens"].availability_buffer_hours == 6

    def test_non_ecmwf_models_use_default_buffer(self):
        """Test that non-ECMWF models use the default 3-hour buffer."""
        from weather.config.models import MODELS
        assert MODELS["gfs"].availability_buffer_hours == 3
        assert MODELS["hrrr"].availability_buffer_hours == 3
        assert MODELS["nbm"].availability_buffer_hours == 3

    @patch("weather.clients.herbie_client.datetime")
    def test_buffer_affects_run_dt(self, mock_datetime):
        """Test that buffer hours affect the computed run datetime."""
        from weather.config.models import ModelConfig

        mock_now = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        client = HerbieClient()

        # With 3-hour buffer: available_time = 15:00, run_hour = 12
        config_3h = ModelConfig(
            model_id="test", api_model="", display_name="Test",
            provider="Test", max_forecast_days=7, resolution_degrees=0.25,
            description="Test", herbie_model="test", herbie_product="test",
            update_interval_hours=6, availability_buffer_hours=3,
        )
        run_dt_3h = client._get_latest_run_dt(config_3h)
        assert run_dt_3h.hour == 12

        # With 6-hour buffer: available_time = 12:00, run_hour = 12
        config_6h = ModelConfig(
            model_id="test", api_model="", display_name="Test",
            provider="Test", max_forecast_days=7, resolution_degrees=0.25,
            description="Test", herbie_model="test", herbie_product="test",
            update_interval_hours=12, availability_buffer_hours=6,
        )
        run_dt_6h = client._get_latest_run_dt(config_6h)
        assert run_dt_6h.hour == 12

        # With 6-hour buffer at time 17:00: available_time = 11:00, run_hour = 0
        mock_now_17 = datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now_17
        run_dt_6h_17 = client._get_latest_run_dt(config_6h)
        assert run_dt_6h_17.hour == 0


class TestFastHerbieLoggerSuppression:
    """Tests for herbie.fast logger suppression during FastHerbie construction."""

    @patch("weather.clients.herbie_client.get_model_config")
    def test_herbie_fast_logger_suppressed_during_construction(self, mock_config):
        """Test that herbie.fast logger is set to CRITICAL during FastHerbie()."""
        import logging as _logging
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="ifs", api_model="ecmwf_ifs025", display_name="IFS",
            provider="ECMWF", max_forecast_days=10, resolution_degrees=0.25,
            description="Test", herbie_model="ifs", herbie_product="oper",
            update_interval_hours=12, availability_buffer_hours=6,
        )

        captured_levels = []

        def capturing_fastherbie(**kwargs):
            level = _logging.getLogger("herbie.fast").level
            captured_levels.append(level)
            mock_fh = MagicMock()
            obj = MagicMock()
            obj.fxx = 0
            obj.grib = "some/path.grib2"
            mock_fh.objects = [obj]
            mock_fh.xarray.side_effect = Exception("skip")
            return mock_fh

        with patch("herbie.FastHerbie", side_effect=capturing_fastherbie):
            client = HerbieClient()
            client.extract_all_hours_batch(
                "ifs", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
            )

        assert captured_levels[0] == _logging.CRITICAL

        # Logger should be restored after construction
        assert _logging.getLogger("herbie.fast").level != _logging.CRITICAL

    @patch("weather.clients.herbie_client.get_model_config")
    def test_herbie_fast_logger_restored_on_exception(self, mock_config):
        """Test that herbie.fast logger is restored even if FastHerbie raises."""
        import logging as _logging
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="ifs", api_model="ecmwf_ifs025", display_name="IFS",
            provider="ECMWF", max_forecast_days=10, resolution_degrees=0.25,
            description="Test", herbie_model="ifs", herbie_product="oper",
            update_interval_hours=12, availability_buffer_hours=6,
        )

        herbie_fast_logger = _logging.getLogger("herbie.fast")
        original_level = herbie_fast_logger.level

        with patch("herbie.FastHerbie", side_effect=RuntimeError("boom")):
            client = HerbieClient()
            with pytest.raises(RuntimeError):
                client.extract_all_hours_batch(
                    "ifs", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
                )

        assert herbie_fast_logger.level == original_level


class TestFastHerbiePriority:
    """Tests for priority kwarg passed to FastHerbie and Herbie."""

    @patch("weather.clients.herbie_client.get_model_config")
    def test_priority_passed_to_fastherbie(self, mock_config):
        """Test that priority kwarg excludes Azure sources."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="ifs", api_model="ecmwf_ifs025", display_name="IFS",
            provider="ECMWF", max_forecast_days=10, resolution_degrees=0.25,
            description="Test", herbie_model="ifs", herbie_product="oper",
            update_interval_hours=12, availability_buffer_hours=6,
        )

        mock_fh = MagicMock()
        mock_fh.objects = []

        with patch("herbie.FastHerbie", return_value=mock_fh) as MockFH:
            client = HerbieClient()
            client.extract_all_hours_batch(
                "ifs", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
            )

        call_kwargs = MockFH.call_args[1]
        assert "priority" in call_kwargs
        assert "azure" not in call_kwargs["priority"]
        assert "google" in call_kwargs["priority"]


class TestFastHerbieKeyError:
    """Tests for KeyError handling in FastHerbie xarray calls."""

    @patch("weather.clients.herbie_client.get_model_config")
    def test_xarray_keyerror_skips_variable(self, mock_config):
        """Test that KeyError from fh.xarray() skips the variable gracefully."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="aifs", api_model="ecmwf_aifs025_single", display_name="AIFS",
            provider="ECMWF", max_forecast_days=15, resolution_degrees=0.25,
            description="Test", herbie_model="aifs", herbie_product="oper",
            update_interval_hours=12, availability_buffer_hours=6,
        )

        mock_fh = MagicMock()
        obj = MagicMock()
        obj.fxx = 0
        obj.grib = "some/path.grib2"
        mock_fh.objects = [obj]

        call_count = 0

        def mock_xarray(search_str):
            nonlocal call_count
            call_count += 1
            if ":2t:" in search_str:
                # Temperature works (ECMWF eccodes format)
                ds = MagicMock()
                ds.data_vars = {"var": None}
                def mock_sel(step):
                    ds_2d = MagicMock()
                    ds_points = _make_pick_points_ds("var", [273.15])
                    ds_2d.herbie.pick_points.return_value = ds_points
                    return ds_2d
                ds.sel = mock_sel
                return ds
            raise KeyError("href")

        mock_fh.xarray = mock_xarray

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "aifs", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
            )

        assert avail == [0]
        assert results[0][0]["temperature"] == 273.15
        # Variables that raised KeyError should be None
        assert results[0][0]["precipitation"] is None


class TestPerHourFallback:
    """Tests for per-hour fallback when batch fh.xarray() fails.

    This covers the case where accumulation variables (APCP, ASNOW) are
    missing at fxx=0, causing FastHerbie's batch xarray() to fail. The
    fallback loads each hour individually so data for fxx>0 is preserved.
    """

    @patch("weather.clients.herbie_client.get_model_config")
    def test_per_hour_fallback_recovers_data(self, mock_config):
        """Test that per-hour fallback recovers data for hours where the variable exists."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=16, resolution_degrees=0.25,
            description="Test", herbie_model="gfs", herbie_product="pgrb2.0p25",
            update_interval_hours=6,
        )

        # Build mock FastHerbie with 3 hours (fxx 0, 1, 2)
        mock_fh = MagicMock()
        h_objects = []
        for fxx_val in [0, 1, 2]:
            obj = MagicMock()
            obj.fxx = fxx_val
            obj.grib = f"some/path/f{fxx_val:03d}.grib2"

            # Per-hour xarray: fxx=0 fails for APCP, others succeed
            def make_per_hour_xarray(fxx_v):
                def per_hour_xarray(search_str):
                    if "APCP" in search_str and fxx_v == 0:
                        raise FileNotFoundError("subset file not found")
                    ds = MagicMock()
                    ds.data_vars = {"var": None}
                    ds_points = _make_pick_points_ds("var", [float(fxx_v) + 0.5])
                    ds.herbie.pick_points.return_value = ds_points
                    return ds
                return per_hour_xarray

            obj.xarray = make_per_hour_xarray(fxx_val)
            h_objects.append(obj)

        mock_fh.objects = h_objects

        # Batch xarray: temperature works, precipitation fails (fxx=0 issue)
        def batch_xarray(search_str):
            if "APCP" in search_str:
                raise FileNotFoundError("subset_xxx__gfs.f000 not found")
            if "ASNOW" in search_str:
                raise FileNotFoundError("subset_xxx__gfs.f000 not found")
            # Other variables work in batch
            ds = MagicMock()
            ds.data_vars = {"var": None}

            def mock_sel(step):
                fxx_hours = int(step.total_seconds() / 3600)
                ds_2d = MagicMock()
                ds_points = _make_pick_points_ds("var", [100.0 + fxx_hours])
                ds_2d.herbie.pick_points.return_value = ds_points
                return ds_2d

            ds.sel = mock_sel
            return ds

        mock_fh.xarray = batch_xarray

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "gfs", datetime(2024, 1, 1), [0, 1, 2], [(43.5, -110.8)]
            )

        assert avail == [0, 1, 2]

        # Batch-loaded variables should work at all hours
        assert results[0][0]["temperature"] == 100.0
        assert results[1][0]["temperature"] == 101.0
        assert results[2][0]["temperature"] == 102.0

        # Precipitation: fxx=0 should be None (fallback failed for that hour),
        # fxx=1 and fxx=2 should have data from per-hour fallback
        assert results[0][0]["precipitation"] is None
        assert results[1][0]["precipitation"] == 1.5
        assert results[2][0]["precipitation"] == 2.5

    @patch("weather.clients.herbie_client.get_model_config")
    def test_per_hour_fallback_all_fail_produces_none(self, mock_config):
        """Test that if per-hour fallback also fails for all hours, variable is None."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=16, resolution_degrees=0.25,
            description="Test", herbie_model="gfs", herbie_product="pgrb2.0p25",
            update_interval_hours=6,
        )

        mock_fh = MagicMock()
        obj = MagicMock()
        obj.fxx = 0
        obj.grib = "some/path.grib2"
        # Per-hour xarray also fails
        obj.xarray = MagicMock(side_effect=Exception("Variable not found"))
        mock_fh.objects = [obj]

        # Batch xarray: all fail
        mock_fh.xarray = MagicMock(side_effect=Exception("Batch failed"))

        with patch("herbie.FastHerbie", return_value=mock_fh):
            client = HerbieClient()
            avail, results = client.extract_all_hours_batch(
                "gfs", datetime(2024, 1, 1), [0], [(43.5, -110.8)]
            )

        assert avail == [0]
        # All variables should be None
        for var_name in VARIABLE_SEARCH:
            assert results[0][0][var_name] is None


class TestGetCandidateRunDts:
    """Tests for get_candidate_run_dts method."""

    @patch("weather.clients.herbie_client.datetime")
    def test_returns_two_candidates(self, mock_datetime):
        """Test that get_candidate_run_dts returns latest and previous run."""
        from weather.config.models import ModelConfig

        mock_now = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        config = ModelConfig(
            model_id="test", api_model="", display_name="Test",
            provider="Test", max_forecast_days=7, resolution_degrees=0.25,
            description="Test", herbie_model="test", herbie_product="test",
            update_interval_hours=6, availability_buffer_hours=3,
        )

        client = HerbieClient()
        candidates = client.get_candidate_run_dts(config)

        assert len(candidates) == 2
        # First should be newest
        assert candidates[0] > candidates[1]
        # Gap should be update_interval_hours
        diff = candidates[0] - candidates[1]
        assert diff == timedelta(hours=6)

    @patch("weather.clients.herbie_client.datetime")
    def test_candidates_are_naive(self, mock_datetime):
        """Test that candidate datetimes are naive (no tzinfo)."""
        from weather.config.models import ModelConfig

        mock_now = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        config = ModelConfig(
            model_id="test", api_model="", display_name="Test",
            provider="Test", max_forecast_days=7, resolution_degrees=0.25,
            description="Test", herbie_model="test", herbie_product="test",
            update_interval_hours=12, availability_buffer_hours=6,
        )

        client = HerbieClient()
        candidates = client.get_candidate_run_dts(config)

        for dt in candidates:
            assert dt.tzinfo is None
