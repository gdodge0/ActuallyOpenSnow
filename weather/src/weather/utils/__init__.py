"""Utility functions for weather data processing."""

from weather.utils.geo import haversine_distance, coords_are_equivalent
from weather.utils.time import (
    infer_model_run_time,
    resolve_time_offset,
    get_time_index,
    slice_time_range,
    ensure_utc,
)
from weather.utils.snow import (
    get_snow_ratio,
    calculate_snowfall_from_precip,
    calculate_hourly_snowfall,
)

__all__ = [
    # Geo utilities
    "haversine_distance",
    "coords_are_equivalent",
    # Time utilities
    "infer_model_run_time",
    "resolve_time_offset",
    "get_time_index",
    "slice_time_range",
    "ensure_utc",
    # Snow utilities
    "get_snow_ratio",
    "calculate_snowfall_from_precip",
    "calculate_hourly_snowfall",
]

