"""Tests for range total calculations."""

import pytest
from datetime import datetime, timedelta, timezone

from weather.domain.forecast import Forecast
from weather.domain.errors import RangeError


def create_test_forecast(hours: int = 48) -> Forecast:
    """Create a test forecast with predictable data."""
    base_time = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    times_utc = [base_time + timedelta(hours=h) for h in range(hours)]

    # Create predictable snowfall: 1mm per hour
    snowfall = tuple(1.0 for _ in range(hours))

    # Create predictable precipitation: 2mm per hour
    precipitation = tuple(2.0 for _ in range(hours))

    return Forecast(
        lat=43.48,
        lon=-110.76,
        api_lat=43.5,
        api_lon=-110.75,
        elevation_m=3000.0,
        model_id="gfs",
        model_run_utc=base_time,
        times_utc=times_utc,
        hourly_data={
            "snowfall": snowfall,
            "precipitation": precipitation,
            "temperature_2m": tuple(float(-5 + i * 0.1) for i in range(hours)),
        },
        hourly_units={
            "snowfall": "cm",
            "precipitation": "mm",
            "temperature_2m": "C",
        },
    )


class TestRangeTotalsWithTimedelta:
    """Tests for range totals using timedelta offsets."""

    def test_full_range(self):
        """Test getting total for the full forecast range."""
        forecast = create_test_forecast(48)
        total = forecast.get_snowfall_total(unit="cm")

        assert total.value == 48.0  # 1cm per hour * 48 hours
        assert total.unit == "cm"

    def test_first_24_hours(self):
        """Test getting total for first 24 hours."""
        forecast = create_test_forecast(48)
        total = forecast.get_snowfall_total(
            unit="cm",
            start=timedelta(hours=0),
            end=timedelta(hours=24),
        )

        assert total.value == 24.0
        assert total.unit == "cm"

    def test_second_24_hours(self):
        """Test getting total for second 24 hours."""
        forecast = create_test_forecast(48)
        total = forecast.get_snowfall_total(
            unit="cm",
            start=timedelta(hours=24),
            end=timedelta(hours=48),
        )

        assert total.value == 24.0
        assert total.unit == "cm"

    def test_partial_range(self):
        """Test getting total for a partial range."""
        forecast = create_test_forecast(48)
        total = forecast.get_precipitation_total(
            unit="mm",
            start=timedelta(hours=10),
            end=timedelta(hours=20),
        )

        assert total.value == 20.0  # 2mm per hour * 10 hours
        assert total.unit == "mm"

    def test_unit_conversion_in_range(self):
        """Test unit conversion in range totals."""
        forecast = create_test_forecast(48)
        total = forecast.get_snowfall_total(
            unit="in",
            start=timedelta(hours=0),
            end=timedelta(hours=24),
        )

        # 24 cm = 9.45 inches (approximately)
        assert abs(total.value - 9.45) < 0.1
        assert total.unit == "in"


class TestRangeTotalsWithDatetime:
    """Tests for range totals using datetime objects."""

    def test_with_datetime_range(self):
        """Test getting total using datetime range."""
        forecast = create_test_forecast(48)

        start = datetime(2024, 1, 15, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 15, 12, tzinfo=timezone.utc)

        total = forecast.get_snowfall_total(unit="cm", start=start, end=end)

        assert total.value == 12.0
        assert total.unit == "cm"

    def test_mixed_timedelta_datetime(self):
        """Test mixing timedelta start with datetime end."""
        forecast = create_test_forecast(48)

        # This should work: timedelta for start, datetime for end
        start = timedelta(hours=0)
        end = datetime(2024, 1, 15, 12, tzinfo=timezone.utc)

        total = forecast.get_snowfall_total(unit="cm", start=start, end=end)
        assert total.value == 12.0


class TestRangeTotalsClamping:
    """Tests for range clamping behavior."""

    def test_start_before_forecast_clamps(self):
        """Test that start before forecast start is clamped."""
        forecast = create_test_forecast(24)
        total = forecast.get_snowfall_total(
            unit="cm",
            start=timedelta(hours=-10),  # Before forecast
            end=timedelta(hours=10),
        )

        # Should clamp to available data (hours 0-10)
        assert total.value == 10.0

    def test_end_after_forecast_clamps(self):
        """Test that end after forecast end is clamped."""
        forecast = create_test_forecast(24)
        total = forecast.get_snowfall_total(
            unit="cm",
            start=timedelta(hours=20),
            end=timedelta(hours=100),  # Way past forecast end
        )

        # Should clamp to available data (hours 20-24)
        assert total.value == 4.0


class TestRangeTotalsErrors:
    """Tests for error cases in range totals."""

    def test_end_before_start_raises(self):
        """Test that end before start raises RangeError."""
        forecast = create_test_forecast(48)

        with pytest.raises(RangeError):
            forecast.get_snowfall_total(
                unit="cm",
                start=timedelta(hours=24),
                end=timedelta(hours=12),
            )

    def test_missing_variable_raises(self):
        """Test that missing variable raises KeyError."""
        forecast = create_test_forecast(48)
        # Remove precipitation data
        forecast.hourly_data = {"snowfall": forecast.hourly_data["snowfall"]}

        with pytest.raises(KeyError):
            forecast.get_precipitation_total(unit="mm")


class TestPrecipitationTotals:
    """Tests specifically for precipitation totals."""

    def test_precipitation_total_basic(self):
        """Test basic precipitation total."""
        forecast = create_test_forecast(48)
        total = forecast.get_precipitation_total(unit="mm")

        assert total.value == 96.0  # 2mm * 48 hours
        assert total.unit == "mm"

    def test_precipitation_to_inches(self):
        """Test precipitation total in inches."""
        forecast = create_test_forecast(24)
        total = forecast.get_precipitation_total(unit="in")

        # 48mm (2mm * 24 hours) = 1.89 inches approximately
        assert abs(total.value - 1.89) < 0.02
        assert total.unit == "in"

