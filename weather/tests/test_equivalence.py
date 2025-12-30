"""Tests for forecast equivalence."""

import pytest
from datetime import datetime, timezone

from weather.domain.forecast import Forecast


def create_forecast(
    lat: float = 43.48,
    lon: float = -110.76,
    api_lat: float = 43.5,
    api_lon: float = -110.75,
    model_id: str = "gfs",
    model_run_utc: datetime | None = None,
) -> Forecast:
    """Create a minimal forecast for equivalence testing."""
    if model_run_utc is None:
        model_run_utc = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

    return Forecast(
        lat=lat,
        lon=lon,
        api_lat=api_lat,
        api_lon=api_lon,
        elevation_m=3000.0,
        model_id=model_id,
        model_run_utc=model_run_utc,
        times_utc=[model_run_utc],
        hourly_data={"temperature_2m": (0.0,)},
        hourly_units={"temperature_2m": "C"},
    )


class TestIsEquivalent:
    """Tests for Forecast.is_equivalent method."""

    def test_same_forecast_is_equivalent(self):
        """Test that a forecast is equivalent to itself."""
        forecast = create_forecast()
        assert forecast.is_equivalent(forecast)

    def test_identical_forecasts_are_equivalent(self):
        """Test that two identical forecasts are equivalent."""
        forecast1 = create_forecast()
        forecast2 = create_forecast()
        assert forecast1.is_equivalent(forecast2)

    def test_different_model_not_equivalent(self):
        """Test that different models are not equivalent."""
        forecast1 = create_forecast(model_id="gfs")
        forecast2 = create_forecast(model_id="ifs")
        assert not forecast1.is_equivalent(forecast2)

    def test_different_model_run_not_equivalent(self):
        """Test that different model runs are not equivalent."""
        run1 = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        run2 = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)

        forecast1 = create_forecast(model_run_utc=run1)
        forecast2 = create_forecast(model_run_utc=run2)
        assert not forecast1.is_equivalent(forecast2)

    def test_close_locations_are_equivalent(self):
        """Test that locations within 100m are equivalent."""
        # Two points about 50 meters apart (same grid point)
        forecast1 = create_forecast(api_lat=43.5000, api_lon=-110.75)
        forecast2 = create_forecast(api_lat=43.5003, api_lon=-110.75)
        assert forecast1.is_equivalent(forecast2)

    def test_distant_locations_not_equivalent(self):
        """Test that locations more than 100m apart are not equivalent."""
        # Two points about 1km apart
        forecast1 = create_forecast(api_lat=43.5, api_lon=-110.75)
        forecast2 = create_forecast(api_lat=43.51, api_lon=-110.75)
        assert not forecast1.is_equivalent(forecast2)

    def test_custom_threshold(self):
        """Test equivalence with custom distance threshold."""
        # Two points about 1km apart
        forecast1 = create_forecast(api_lat=43.5, api_lon=-110.75)
        forecast2 = create_forecast(api_lat=43.51, api_lon=-110.75)

        # Should not be equivalent at default 100m
        assert not forecast1.is_equivalent(forecast2)

        # Should be equivalent at 2000m threshold
        assert forecast1.is_equivalent(forecast2, threshold_meters=2000)


class TestForecastEquality:
    """Tests for Forecast.__eq__ method."""

    def test_equal_forecasts(self):
        """Test that equal forecasts compare as equal."""
        forecast1 = create_forecast()
        forecast2 = create_forecast()
        assert forecast1 == forecast2

    def test_different_data_not_equal(self):
        """Test that forecasts with different data are not equal."""
        forecast1 = create_forecast()
        forecast2 = create_forecast()
        forecast2.hourly_data = {"temperature_2m": (10.0,)}  # Different value

        assert forecast1 != forecast2

    def test_different_lat_not_equal(self):
        """Test that forecasts with different requested lat are not equal."""
        forecast1 = create_forecast(lat=43.48)
        forecast2 = create_forecast(lat=43.49)
        assert forecast1 != forecast2

    def test_comparison_with_non_forecast(self):
        """Test comparison with non-Forecast returns NotImplemented."""
        forecast = create_forecast()
        assert forecast.__eq__("not a forecast") == NotImplemented
        assert (forecast == "not a forecast") is False


class TestEquivalenceVsEquality:
    """Tests demonstrating difference between equivalence and equality."""

    def test_equivalent_but_not_equal(self):
        """Test forecasts can be equivalent but not strictly equal."""
        # Same location (within 100m), same model, same run
        # But different requested coordinates
        forecast1 = create_forecast(lat=43.48, lon=-110.76)
        forecast2 = create_forecast(lat=43.49, lon=-110.77)

        # Equivalent (same grid point, model, run)
        assert forecast1.is_equivalent(forecast2)

        # But not equal (different requested coordinates)
        assert forecast1 != forecast2

    def test_equal_implies_equivalent(self):
        """Test that equal forecasts are always equivalent."""
        forecast1 = create_forecast()
        forecast2 = create_forecast()

        assert forecast1 == forecast2
        assert forecast1.is_equivalent(forecast2)

