"""Tests for Forecast getter methods."""

import pytest
from datetime import datetime, timezone

from weather.domain.forecast import Forecast
from weather.domain.quantities import Series


def create_test_forecast() -> Forecast:
    """Create a test forecast with sample data."""
    base_time = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    hours = 24

    return Forecast(
        lat=43.48,
        lon=-110.76,
        api_lat=43.5,
        api_lon=-110.75,
        elevation_m=3000.0,
        model_id="gfs",
        model_run_utc=base_time,
        times_utc=[base_time.replace(hour=h) for h in range(hours)],
        hourly_data={
            "temperature_2m": tuple(float(-10 + i) for i in range(hours)),
            "wind_speed_10m": tuple(float(20 + i) for i in range(hours)),
            "wind_gusts_10m": tuple(float(30 + i) for i in range(hours)),
            "snowfall": tuple(0.5 for _ in range(hours)),
            "precipitation": tuple(1.0 for _ in range(hours)),
            "freezing_level_height": tuple(float(2000 + i * 10) for i in range(hours)),
        },
        hourly_units={
            "temperature_2m": "C",
            "wind_speed_10m": "kmh",
            "wind_gusts_10m": "kmh",
            "snowfall": "cm",
            "precipitation": "mm",
            "freezing_level_height": "m",
        },
    )


class TestTemperatureGetter:
    """Tests for get_temperature_2m."""

    def test_returns_series(self):
        """Test that getter returns a Series."""
        forecast = create_test_forecast()
        result = forecast.get_temperature_2m()

        assert isinstance(result, Series)
        assert len(result) == 24

    def test_default_unit_is_celsius(self):
        """Test that default unit is Celsius."""
        forecast = create_test_forecast()
        result = forecast.get_temperature_2m()

        assert result.unit == "C"
        assert result.values[0] == -10.0

    def test_converts_to_fahrenheit(self):
        """Test conversion to Fahrenheit."""
        forecast = create_test_forecast()
        result = forecast.get_temperature_2m(unit="F")

        assert result.unit == "F"
        # -10°C = 14°F
        assert result.values[0] == 14.0

    def test_converts_to_kelvin(self):
        """Test conversion to Kelvin."""
        forecast = create_test_forecast()
        result = forecast.get_temperature_2m(unit="K")

        assert result.unit == "K"
        # -10°C = 263.15K
        assert abs(result.values[0] - 263.15) < 0.01


class TestWindSpeedGetter:
    """Tests for get_wind_speed_10m."""

    def test_returns_series(self):
        """Test that getter returns a Series."""
        forecast = create_test_forecast()
        result = forecast.get_wind_speed_10m()

        assert isinstance(result, Series)
        assert len(result) == 24

    def test_default_unit_is_kmh(self):
        """Test that default unit is km/h."""
        forecast = create_test_forecast()
        result = forecast.get_wind_speed_10m()

        assert result.unit == "kmh"
        assert result.values[0] == 20.0

    def test_converts_to_mph(self):
        """Test conversion to mph."""
        forecast = create_test_forecast()
        result = forecast.get_wind_speed_10m(unit="mph")

        assert result.unit == "mph"
        # 20 km/h ≈ 12.43 mph
        assert abs(result.values[0] - 12.43) < 0.1

    def test_converts_to_ms(self):
        """Test conversion to m/s."""
        forecast = create_test_forecast()
        result = forecast.get_wind_speed_10m(unit="ms")

        assert result.unit == "ms"
        # 20 km/h ≈ 5.56 m/s
        assert abs(result.values[0] - 5.56) < 0.1


class TestWindGustsGetter:
    """Tests for get_wind_gusts_10m."""

    def test_returns_series(self):
        """Test that getter returns a Series."""
        forecast = create_test_forecast()
        result = forecast.get_wind_gusts_10m()

        assert isinstance(result, Series)
        assert result.values[0] == 30.0

    def test_converts_to_knots(self):
        """Test conversion to knots."""
        forecast = create_test_forecast()
        result = forecast.get_wind_gusts_10m(unit="kn")

        assert result.unit == "kn"
        # 30 km/h ≈ 16.2 knots
        assert abs(result.values[0] - 16.2) < 0.1


class TestSnowfallGetter:
    """Tests for get_snowfall."""

    def test_returns_series(self):
        """Test that getter returns a Series."""
        forecast = create_test_forecast()
        result = forecast.get_snowfall()

        assert isinstance(result, Series)
        assert len(result) == 24

    def test_default_unit_is_cm(self):
        """Test that default unit is cm."""
        forecast = create_test_forecast()
        result = forecast.get_snowfall()

        assert result.unit == "cm"
        assert result.values[0] == 0.5

    def test_converts_to_inches(self):
        """Test conversion to inches."""
        forecast = create_test_forecast()
        result = forecast.get_snowfall(unit="in")

        assert result.unit == "in"
        # 0.5 cm ≈ 0.197 in
        assert abs(result.values[0] - 0.197) < 0.01


class TestPrecipitationGetter:
    """Tests for get_precipitation."""

    def test_returns_series(self):
        """Test that getter returns a Series."""
        forecast = create_test_forecast()
        result = forecast.get_precipitation()

        assert isinstance(result, Series)

    def test_default_unit_is_mm(self):
        """Test that default unit is mm."""
        forecast = create_test_forecast()
        result = forecast.get_precipitation()

        assert result.unit == "mm"

    def test_converts_to_inches(self):
        """Test conversion to inches."""
        forecast = create_test_forecast()
        result = forecast.get_precipitation(unit="in")

        assert result.unit == "in"
        # 1mm ≈ 0.0394 in
        assert abs(result.values[0] - 0.0394) < 0.001


class TestFreezingLevelGetter:
    """Tests for get_freezing_level_height."""

    def test_returns_series(self):
        """Test that getter returns a Series."""
        forecast = create_test_forecast()
        result = forecast.get_freezing_level_height()

        assert isinstance(result, Series)

    def test_default_unit_is_meters(self):
        """Test that default unit is meters."""
        forecast = create_test_forecast()
        result = forecast.get_freezing_level_height()

        assert result.unit == "m"
        assert result.values[0] == 2000.0

    def test_converts_to_feet(self):
        """Test conversion to feet."""
        forecast = create_test_forecast()
        result = forecast.get_freezing_level_height(unit="ft")

        assert result.unit == "ft"
        # 2000m ≈ 6562 ft
        assert abs(result.values[0] - 6562) < 1


class TestAccumulatedSeries:
    """Tests for accumulated series getters."""

    def test_snowfall_accumulated(self):
        """Test accumulated snowfall calculation."""
        forecast = create_test_forecast()
        result = forecast.get_snowfall_accumulated()

        assert isinstance(result, Series)
        # Each hour adds 0.5 cm
        assert result.values[0] == 0.5
        assert result.values[1] == 1.0
        assert result.values[23] == 12.0  # 24 * 0.5

    def test_precipitation_accumulated(self):
        """Test accumulated precipitation calculation."""
        forecast = create_test_forecast()
        result = forecast.get_precipitation_accumulated()

        assert isinstance(result, Series)
        # Each hour adds 1 mm
        assert result.values[0] == 1.0
        assert result.values[23] == 24.0

    def test_accumulated_with_unit_conversion(self):
        """Test accumulated series with unit conversion."""
        forecast = create_test_forecast()
        result = forecast.get_snowfall_accumulated(unit="in")

        assert result.unit == "in"
        # 12 cm total ≈ 4.72 in
        assert abs(result.values[23] - 4.72) < 0.1


class TestMissingVariable:
    """Tests for missing variable handling."""

    def test_missing_variable_raises_keyerror(self):
        """Test that accessing missing variable raises KeyError."""
        forecast = create_test_forecast()
        # Remove a variable
        del forecast.hourly_data["wind_gusts_10m"]

        with pytest.raises(KeyError) as exc_info:
            forecast.get_wind_gusts_10m()

        assert "wind_gusts_10m" in str(exc_info.value)

