"""Time and date utility functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Union

from weather.domain.errors import RangeError


TimeOffset = Union[datetime, timedelta]


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is in UTC timezone.

    Args:
        dt: A datetime object.

    Returns:
        The datetime converted to UTC.

    Raises:
        ValueError: If the datetime is naive (no timezone info).
    """
    if dt.tzinfo is None:
        raise ValueError("Datetime must have timezone info. Use timezone-aware datetimes.")

    return dt.astimezone(timezone.utc)


def infer_model_run_time(times_utc: list[datetime]) -> datetime | None:
    """Infer the model run time from forecast timestamps.

    Open-Meteo forecasts typically start at the most recent model run.
    The first timestamp usually indicates the model run time (at 00, 06, 12, or 18 UTC).

    Args:
        times_utc: List of forecast timestamps in UTC.

    Returns:
        The inferred model run time, or None if unable to infer.
    """
    if not times_utc:
        return None

    first_time = times_utc[0]

    # Model runs are typically at 00, 06, 12, or 18 UTC
    # Round down to the nearest 6-hour interval
    run_hour = (first_time.hour // 6) * 6

    return first_time.replace(hour=run_hour, minute=0, second=0, microsecond=0)


def resolve_time_offset(
    offset: TimeOffset,
    reference: datetime,
) -> datetime:
    """Resolve a time offset to an absolute datetime.

    Args:
        offset: Either a datetime (returned as-is after UTC conversion)
                or a timedelta (added to reference).
        reference: The reference datetime for timedelta offsets.

    Returns:
        The resolved datetime in UTC.
    """
    if isinstance(offset, timedelta):
        return reference + offset
    else:
        return ensure_utc(offset)


def get_time_index(
    target: datetime,
    times_utc: list[datetime],
    clamp: bool = True,
) -> int:
    """Find the index of a target time in the forecast times.

    Args:
        target: The target datetime to find.
        times_utc: List of forecast timestamps.
        clamp: If True, clamp to valid range. If False, raise on out of bounds.

    Returns:
        The index of the closest time at or before target.

    Raises:
        RangeError: If target is out of range and clamp is False.
    """
    if not times_utc:
        raise RangeError("No forecast times available")

    target_utc = ensure_utc(target) if target.tzinfo else target.replace(tzinfo=timezone.utc)

    if target_utc < times_utc[0]:
        if clamp:
            return 0
        raise RangeError(
            f"Target time {target_utc} is before forecast start {times_utc[0]}"
        )

    if target_utc >= times_utc[-1]:
        if clamp:
            return len(times_utc) - 1
        raise RangeError(
            f"Target time {target_utc} is after forecast end {times_utc[-1]}"
        )

    # Binary search for the correct index
    for i, t in enumerate(times_utc):
        if t > target_utc:
            return max(0, i - 1)

    return len(times_utc) - 1


def slice_time_range(
    start: TimeOffset,
    end: TimeOffset,
    times_utc: list[datetime],
) -> tuple[int, int]:
    """Get the index range for a time window.

    Args:
        start: Start of range (datetime or timedelta from first time).
        end: End of range (datetime or timedelta from first time).
        times_utc: List of forecast timestamps.

    Returns:
        Tuple of (start_index, end_index) for range [start, end).
        The range is clamped to available data.

    Raises:
        RangeError: If the time range is invalid or empty.
    """
    if not times_utc:
        raise RangeError("No forecast times available")

    reference = times_utc[0]

    start_dt = resolve_time_offset(start, reference)
    end_dt = resolve_time_offset(end, reference)

    if end_dt <= start_dt:
        raise RangeError(f"End time must be after start time: {start_dt} >= {end_dt}")

    start_idx = get_time_index(start_dt, times_utc, clamp=True)
    end_idx = get_time_index(end_dt, times_utc, clamp=True)

    # Adjust end_idx for exclusive end semantics [start, end)
    # If end_dt is after the timestamp at end_idx, include that timestamp
    if times_utc[end_idx] < end_dt:
        end_idx += 1

    # Ensure we have at least one element
    if end_idx <= start_idx:
        end_idx = start_idx + 1

    return start_idx, min(end_idx, len(times_utc))


def format_duration(hours: int) -> str:
    """Format a duration in hours as a human-readable string.

    Args:
        hours: Number of hours.

    Returns:
        Formatted string like "24h", "3d", "7d 12h".
    """
    if hours < 24:
        return f"{hours}h"

    days = hours // 24
    remaining_hours = hours % 24

    if remaining_hours == 0:
        return f"{days}d"

    return f"{days}d {remaining_hours}h"

