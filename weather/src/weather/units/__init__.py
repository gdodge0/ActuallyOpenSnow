"""Unit handling and conversion utilities."""

from weather.units.normalize import normalize_unit, UNIT_ALIASES, CANONICAL_UNITS
from weather.units.convert import (
    convert_temperature,
    convert_speed,
    convert_length,
    convert_value,
    convert_series,
)
from weather.units.openmeteo_units import decode_openmeteo_unit

__all__ = [
    # Normalization
    "normalize_unit",
    "UNIT_ALIASES",
    "CANONICAL_UNITS",
    # Conversion
    "convert_temperature",
    "convert_speed",
    "convert_length",
    "convert_value",
    "convert_series",
    # Open-Meteo specific
    "decode_openmeteo_unit",
]

