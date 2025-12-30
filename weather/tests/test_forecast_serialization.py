"""Tests for Forecast serialization and properties."""

import pytest
from datetime import datetime, timezone, timedelta

from weather.domain.forecast import Forecast


def create_test_forecast(
    hours: int = 24,
    naive_times: bool = False,
    naive_model_run: bool = False,
) -> Forecast:
    """Create a test forecast with configurable options."""
    if naive_times:
        base_time = datetime(2024, 1, 15, 0, 0, 0)
    else:
        base_time = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

    if naive_model_run:
        model_run = datetime(2024, 1, 15, 0, 0, 0)
    else:
        model_run = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

    return Forecast(
        lat=43.48,
        lon=-110.76,
        api_lat=43.5,
        api_lon=-110.75,
        elevation_m=3000.0,
        model_id="gfs",
        model_run_utc=model_run,
        times_utc=[base_time + timedelta(hours=h) for h in range(hours)],
        hourly_data={
            "temperature_2m": tuple(float(-10 + i) for i in range(hours)),
            "snowfall": tuple(0.5 for _ in range(hours)),
        },
        hourly_units={
            "temperature_2m": "C",
            "snowfall": "cm",
        },
    )


class TestForecastProperties:
    """Tests for Forecast property methods."""

    def test_hours_available(self):
        """Test hours_available property."""
        forecast = create_test_forecast(hours=48)
        assert forecast.hours_available == 48

    def test_hours_available_empty(self):
        """Test hours_available with no data."""
        forecast = create_test_forecast(hours=0)
        assert forecast.hours_available == 0

    def test_forecast_start(self):
        """Test forecast_start property."""
        forecast = create_test_forecast(hours=24)
        expected = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert forecast.forecast_start == expected

    def test_forecast_start_empty(self):
        """Test forecast_start with no data returns None."""
        forecast = create_test_forecast(hours=0)
        assert forecast.forecast_start is None

    def test_forecast_end(self):
        """Test forecast_end property."""
        forecast = create_test_forecast(hours=24)
        expected = datetime(2024, 1, 15, 23, 0, 0, tzinfo=timezone.utc)
        assert forecast.forecast_end == expected

    def test_forecast_end_empty(self):
        """Test forecast_end with no data returns None."""
        forecast = create_test_forecast(hours=0)
        assert forecast.forecast_end is None


class TestForecastPostInit:
    """Tests for Forecast __post_init__ processing."""

    def test_naive_times_converted_to_utc(self):
        """Test that naive times are converted to UTC."""
        forecast = create_test_forecast(naive_times=True)

        # All times should now have UTC timezone
        for t in forecast.times_utc:
            assert t.tzinfo == timezone.utc

    def test_naive_model_run_converted_to_utc(self):
        """Test that naive model_run_utc is converted to UTC."""
        forecast = create_test_forecast(naive_model_run=True)
        assert forecast.model_run_utc.tzinfo == timezone.utc

    def test_utc_times_unchanged(self):
        """Test that UTC times remain unchanged."""
        forecast = create_test_forecast(naive_times=False)
        expected_first = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert forecast.times_utc[0] == expected_first


class TestForecastToDict:
    """Tests for Forecast.to_dict method."""

    def test_basic_to_dict(self):
        """Test basic conversion to dictionary."""
        forecast = create_test_forecast(hours=3)
        d = forecast.to_dict()

        assert d["lat"] == 43.48
        assert d["lon"] == -110.76
        assert d["api_lat"] == 43.5
        assert d["api_lon"] == -110.75
        assert d["elevation_m"] == 3000.0
        assert d["model_id"] == "gfs"

    def test_to_dict_model_run_isoformat(self):
        """Test that model_run_utc is converted to ISO format."""
        forecast = create_test_forecast()
        d = forecast.to_dict()

        assert isinstance(d["model_run_utc"], str)
        assert "2024-01-15" in d["model_run_utc"]

    def test_to_dict_none_model_run(self):
        """Test to_dict with None model_run_utc."""
        forecast = create_test_forecast()
        forecast.model_run_utc = None

        d = forecast.to_dict()
        assert d["model_run_utc"] is None

    def test_to_dict_times_isoformat(self):
        """Test that times_utc are converted to ISO format."""
        forecast = create_test_forecast(hours=3)
        d = forecast.to_dict()

        assert isinstance(d["times_utc"], list)
        assert len(d["times_utc"]) == 3
        for t in d["times_utc"]:
            assert isinstance(t, str)
            assert "2024-01-15" in t

    def test_to_dict_hourly_data_as_lists(self):
        """Test that hourly_data tuples are converted to lists."""
        forecast = create_test_forecast(hours=3)
        d = forecast.to_dict()

        assert isinstance(d["hourly_data"], dict)
        assert isinstance(d["hourly_data"]["temperature_2m"], list)
        assert isinstance(d["hourly_data"]["snowfall"], list)

    def test_to_dict_hourly_units_preserved(self):
        """Test that hourly_units are preserved."""
        forecast = create_test_forecast()
        d = forecast.to_dict()

        assert d["hourly_units"]["temperature_2m"] == "C"
        assert d["hourly_units"]["snowfall"] == "cm"


class TestForecastFromDict:
    """Tests for Forecast.from_dict method."""

    def test_basic_from_dict(self):
        """Test basic creation from dictionary."""
        data = {
            "lat": 43.48,
            "lon": -110.76,
            "api_lat": 43.5,
            "api_lon": -110.75,
            "elevation_m": 3000.0,
            "model_id": "gfs",
            "model_run_utc": "2024-01-15T00:00:00+00:00",
            "times_utc": [
                "2024-01-15T00:00:00+00:00",
                "2024-01-15T01:00:00+00:00",
            ],
            "hourly_data": {
                "temperature_2m": [-10.0, -9.0],
            },
            "hourly_units": {
                "temperature_2m": "C",
            },
        }

        forecast = Forecast.from_dict(data)

        assert forecast.lat == 43.48
        assert forecast.lon == -110.76
        assert forecast.model_id == "gfs"
        assert len(forecast.times_utc) == 2

    def test_from_dict_parses_model_run(self):
        """Test that model_run_utc string is parsed to datetime."""
        data = {
            "lat": 43.48,
            "lon": -110.76,
            "api_lat": 43.5,
            "api_lon": -110.75,
            "model_id": "gfs",
            "model_run_utc": "2024-01-15T06:00:00+00:00",
            "times_utc": [],
            "hourly_data": {},
            "hourly_units": {},
        }

        forecast = Forecast.from_dict(data)

        assert isinstance(forecast.model_run_utc, datetime)
        assert forecast.model_run_utc.hour == 6

    def test_from_dict_none_model_run(self):
        """Test from_dict with None model_run_utc."""
        data = {
            "lat": 43.48,
            "lon": -110.76,
            "api_lat": 43.5,
            "api_lon": -110.75,
            "model_id": "gfs",
            "model_run_utc": None,
            "times_utc": [],
            "hourly_data": {},
            "hourly_units": {},
        }

        forecast = Forecast.from_dict(data)
        assert forecast.model_run_utc is None

    def test_from_dict_parses_times(self):
        """Test that times_utc strings are parsed to datetimes."""
        data = {
            "lat": 43.48,
            "lon": -110.76,
            "api_lat": 43.5,
            "api_lon": -110.75,
            "model_id": "gfs",
            "times_utc": [
                "2024-01-15T00:00:00+00:00",
                "2024-01-15T01:00:00+00:00",
            ],
            "hourly_data": {},
            "hourly_units": {},
        }

        forecast = Forecast.from_dict(data)

        assert all(isinstance(t, datetime) for t in forecast.times_utc)
        assert forecast.times_utc[0].hour == 0
        assert forecast.times_utc[1].hour == 1

    def test_from_dict_converts_lists_to_tuples(self):
        """Test that hourly_data lists are converted to tuples."""
        data = {
            "lat": 43.48,
            "lon": -110.76,
            "api_lat": 43.5,
            "api_lon": -110.75,
            "model_id": "gfs",
            "times_utc": [],
            "hourly_data": {
                "temperature_2m": [-10.0, -9.0, -8.0],
            },
            "hourly_units": {},
        }

        forecast = Forecast.from_dict(data)

        assert isinstance(forecast.hourly_data["temperature_2m"], tuple)

    def test_from_dict_missing_optional_fields(self):
        """Test from_dict with missing optional fields."""
        data = {
            "lat": 43.48,
            "lon": -110.76,
            "api_lat": 43.5,
            "api_lon": -110.75,
            "model_id": "gfs",
        }

        forecast = Forecast.from_dict(data)

        assert forecast.elevation_m is None
        assert forecast.model_run_utc is None
        assert forecast.times_utc == []
        assert forecast.hourly_data == {}
        assert forecast.hourly_units == {}


class TestForecastRoundTrip:
    """Tests for to_dict -> from_dict round trip."""

    def test_round_trip_preserves_data(self):
        """Test that round trip preserves all data."""
        original = create_test_forecast(hours=24)

        d = original.to_dict()
        restored = Forecast.from_dict(d)

        assert restored.lat == original.lat
        assert restored.lon == original.lon
        assert restored.api_lat == original.api_lat
        assert restored.api_lon == original.api_lon
        assert restored.elevation_m == original.elevation_m
        assert restored.model_id == original.model_id
        assert len(restored.times_utc) == len(original.times_utc)
        assert restored.hourly_units == original.hourly_units

    def test_round_trip_preserves_hourly_data(self):
        """Test that round trip preserves hourly data values."""
        original = create_test_forecast(hours=5)

        d = original.to_dict()
        restored = Forecast.from_dict(d)

        for var in original.hourly_data:
            assert var in restored.hourly_data
            assert restored.hourly_data[var] == original.hourly_data[var]

    def test_round_trip_preserves_times(self):
        """Test that round trip preserves times correctly."""
        original = create_test_forecast(hours=5)

        d = original.to_dict()
        restored = Forecast.from_dict(d)

        # Compare times (may differ by microseconds due to ISO format)
        for orig_t, rest_t in zip(original.times_utc, restored.times_utc):
            assert orig_t.year == rest_t.year
            assert orig_t.month == rest_t.month
            assert orig_t.day == rest_t.day
            assert orig_t.hour == rest_t.hour

    def test_round_trip_with_none_values(self):
        """Test round trip with None values in data."""
        base_time = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

        original = Forecast(
            lat=43.48,
            lon=-110.76,
            api_lat=43.5,
            api_lon=-110.75,
            elevation_m=None,  # None elevation
            model_id="gfs",
            model_run_utc=None,  # None model run
            times_utc=[base_time],
            hourly_data={
                "temperature_2m": (10.0, None, 12.0),  # None value
            },
            hourly_units={"temperature_2m": "C"},
        )

        d = original.to_dict()
        restored = Forecast.from_dict(d)

        assert restored.elevation_m is None
        assert restored.model_run_utc is None
        assert restored.hourly_data["temperature_2m"][1] is None

