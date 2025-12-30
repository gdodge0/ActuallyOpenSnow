"""Tests for time utility functions."""

import pytest
from datetime import datetime, timedelta, timezone

from weather.utils.time import (
    ensure_utc,
    infer_model_run_time,
    resolve_time_offset,
    get_time_index,
    slice_time_range,
    format_duration,
)
from weather.domain.errors import RangeError


class TestEnsureUtc:
    """Tests for ensure_utc function."""

    def test_utc_datetime_unchanged(self):
        """Test that UTC datetime is returned unchanged."""
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = ensure_utc(dt)
        assert result == dt
        assert result.tzinfo == timezone.utc

    def test_converts_other_timezone_to_utc(self):
        """Test conversion from other timezone to UTC."""
        # EST is UTC-5
        est = timezone(timedelta(hours=-5))
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=est)

        result = ensure_utc(dt)

        # 12:00 EST = 17:00 UTC
        assert result.hour == 17
        assert result.tzinfo == timezone.utc

    def test_converts_positive_offset_to_utc(self):
        """Test conversion from positive UTC offset."""
        # CET is UTC+1
        cet = timezone(timedelta(hours=1))
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=cet)

        result = ensure_utc(dt)

        # 12:00 CET = 11:00 UTC
        assert result.hour == 11
        assert result.tzinfo == timezone.utc

    def test_naive_datetime_raises_valueerror(self):
        """Test that naive datetime raises ValueError."""
        dt = datetime(2024, 1, 15, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValueError) as exc_info:
            ensure_utc(dt)

        assert "timezone" in str(exc_info.value).lower()


class TestInferModelRunTime:
    """Tests for infer_model_run_time function."""

    def test_infers_00z_run(self):
        """Test inference of 00Z model run."""
        times = [
            datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 15, 1, 0, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result == datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)

    def test_infers_06z_run(self):
        """Test inference of 06Z model run."""
        times = [
            datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 15, 7, 0, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result == datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc)

    def test_infers_12z_run(self):
        """Test inference of 12Z model run."""
        times = [
            datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 15, 13, 0, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result == datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)

    def test_infers_18z_run(self):
        """Test inference of 18Z model run."""
        times = [
            datetime(2024, 1, 15, 18, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 15, 19, 0, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result == datetime(2024, 1, 15, 18, 0, tzinfo=timezone.utc)

    def test_rounds_down_to_nearest_6_hours(self):
        """Test that non-standard hours round down to nearest 6-hour mark."""
        # Starting at 3:00 should round down to 0:00
        times = [
            datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result == datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)

    def test_rounds_down_hour_9_to_6(self):
        """Test that hour 9 rounds down to 6."""
        times = [
            datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result == datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc)

    def test_empty_list_returns_none(self):
        """Test that empty list returns None."""
        result = infer_model_run_time([])
        assert result is None

    def test_clears_minutes_and_seconds(self):
        """Test that minutes and seconds are cleared."""
        times = [
            datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc),
        ]

        result = infer_model_run_time(times)

        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 0


class TestResolveTimeOffset:
    """Tests for resolve_time_offset function."""

    def test_timedelta_added_to_reference(self):
        """Test that timedelta is added to reference."""
        reference = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        offset = timedelta(hours=24)

        result = resolve_time_offset(offset, reference)

        assert result == datetime(2024, 1, 16, 0, 0, tzinfo=timezone.utc)

    def test_negative_timedelta(self):
        """Test negative timedelta."""
        reference = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        offset = timedelta(hours=-6)

        result = resolve_time_offset(offset, reference)

        assert result == datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc)

    def test_datetime_converted_to_utc(self):
        """Test that datetime is converted to UTC."""
        reference = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        # EST is UTC-5
        est = timezone(timedelta(hours=-5))
        offset = datetime(2024, 1, 15, 12, 0, tzinfo=est)

        result = resolve_time_offset(offset, reference)

        # 12:00 EST = 17:00 UTC
        assert result.hour == 17
        assert result.tzinfo == timezone.utc

    def test_utc_datetime_unchanged(self):
        """Test that UTC datetime is returned as-is."""
        reference = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        offset = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)

        result = resolve_time_offset(offset, reference)

        assert result == offset


class TestGetTimeIndex:
    """Tests for get_time_index function."""

    @pytest.fixture
    def sample_times(self):
        """Sample hourly times for testing."""
        base = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        return [base + timedelta(hours=h) for h in range(24)]

    def test_exact_match(self, sample_times):
        """Test finding exact time match."""
        target = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        result = get_time_index(target, sample_times)
        assert result == 12

    def test_between_times_returns_earlier(self, sample_times):
        """Test that time between hours returns earlier index."""
        target = datetime(2024, 1, 15, 12, 30, tzinfo=timezone.utc)
        result = get_time_index(target, sample_times)
        assert result == 12

    def test_before_start_clamped(self, sample_times):
        """Test that time before start is clamped to 0."""
        target = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
        result = get_time_index(target, sample_times, clamp=True)
        assert result == 0

    def test_before_start_raises_when_not_clamped(self, sample_times):
        """Test that time before start raises when clamp=False."""
        target = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)

        with pytest.raises(RangeError):
            get_time_index(target, sample_times, clamp=False)

    def test_after_end_clamped(self, sample_times):
        """Test that time after end is clamped to last index."""
        target = datetime(2024, 1, 16, 0, 0, tzinfo=timezone.utc)
        result = get_time_index(target, sample_times, clamp=True)
        assert result == 23

    def test_after_end_raises_when_not_clamped(self, sample_times):
        """Test that time after end raises when clamp=False."""
        target = datetime(2024, 1, 16, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(RangeError):
            get_time_index(target, sample_times, clamp=False)

    def test_empty_times_raises(self):
        """Test that empty times list raises RangeError."""
        target = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)

        with pytest.raises(RangeError):
            get_time_index(target, [])

    def test_first_time(self, sample_times):
        """Test finding first time."""
        target = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        result = get_time_index(target, sample_times)
        assert result == 0

    def test_last_time(self, sample_times):
        """Test finding last time."""
        target = datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc)
        result = get_time_index(target, sample_times)
        assert result == 23


class TestSliceTimeRange:
    """Tests for slice_time_range function."""

    @pytest.fixture
    def sample_times(self):
        """Sample hourly times for testing."""
        base = datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        return [base + timedelta(hours=h) for h in range(48)]

    def test_timedelta_range(self, sample_times):
        """Test slicing with timedelta offsets."""
        start = timedelta(hours=0)
        end = timedelta(hours=24)

        start_idx, end_idx = slice_time_range(start, end, sample_times)

        assert start_idx == 0
        assert end_idx == 24

    def test_datetime_range(self, sample_times):
        """Test slicing with datetime objects."""
        start = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 16, 0, 0, tzinfo=timezone.utc)

        start_idx, end_idx = slice_time_range(start, end, sample_times)

        assert start_idx == 12
        assert end_idx == 24

    def test_mixed_timedelta_datetime(self, sample_times):
        """Test mixing timedelta start with datetime end."""
        start = timedelta(hours=0)
        end = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)

        start_idx, end_idx = slice_time_range(start, end, sample_times)

        assert start_idx == 0
        assert end_idx == 12

    def test_end_before_start_raises(self, sample_times):
        """Test that end before start raises RangeError."""
        start = timedelta(hours=24)
        end = timedelta(hours=12)

        with pytest.raises(RangeError):
            slice_time_range(start, end, sample_times)

    def test_empty_times_raises(self):
        """Test that empty times list raises RangeError."""
        with pytest.raises(RangeError):
            slice_time_range(timedelta(0), timedelta(hours=24), [])

    def test_clamping_start_before_forecast(self, sample_times):
        """Test that start before forecast is clamped."""
        start = timedelta(hours=-10)
        end = timedelta(hours=10)

        start_idx, end_idx = slice_time_range(start, end, sample_times)

        assert start_idx == 0
        assert end_idx == 10

    def test_clamping_end_after_forecast(self, sample_times):
        """Test that end after forecast is clamped."""
        start = timedelta(hours=40)
        end = timedelta(hours=100)

        start_idx, end_idx = slice_time_range(start, end, sample_times)

        assert start_idx == 40
        assert end_idx == 48  # Clamped to length


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_hours_only(self):
        """Test formatting hours less than 24."""
        assert format_duration(1) == "1h"
        assert format_duration(12) == "12h"
        assert format_duration(23) == "23h"

    def test_zero_hours(self):
        """Test formatting zero hours."""
        assert format_duration(0) == "0h"

    def test_exact_days(self):
        """Test formatting exact days."""
        assert format_duration(24) == "1d"
        assert format_duration(48) == "2d"
        assert format_duration(168) == "7d"

    def test_days_and_hours(self):
        """Test formatting days with remaining hours."""
        assert format_duration(25) == "1d 1h"
        assert format_duration(36) == "1d 12h"
        assert format_duration(50) == "2d 2h"

    def test_large_values(self):
        """Test formatting large hour values."""
        # 14 days
        assert format_duration(336) == "14d"
        # 14 days 12 hours
        assert format_duration(348) == "14d 12h"

