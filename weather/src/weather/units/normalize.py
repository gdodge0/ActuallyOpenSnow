"""Unit normalization and canonical unit tokens."""

from __future__ import annotations

from weather.domain.errors import UnitError

# Canonical unit tokens used internally
CANONICAL_UNITS = {
    # Temperature
    "C",  # Celsius
    "F",  # Fahrenheit
    "K",  # Kelvin
    # Speed
    "kmh",  # kilometers per hour
    "ms",  # meters per second
    "mph",  # miles per hour
    "kn",  # knots
    # Length (precipitation, snowfall, elevation)
    "mm",  # millimeters
    "cm",  # centimeters
    "m",  # meters
    "in",  # inches
    "ft",  # feet
    # Percentage
    "%",
    # Pressure
    "hPa",
    "kPa",  # kilopascals
    # Time
    "s",  # seconds
    # Other
    "W/m²",  # solar radiation (instantaneous)
    "MJ/m²",  # solar radiation (daily totals)
    "°",  # degrees (wind direction)
    "J/kg",  # specific energy (CAPE)
    "μg/m³",  # air quality concentration
    "grains/m³",  # pollen concentration
    "m³/m³",  # volumetric (soil moisture)
    "kg/m²",  # mass per area
    "gpm",  # geopotential meters
    # Undefined/unknown
    "undefined",
}

# Alias mapping to canonical tokens
UNIT_ALIASES: dict[str, str] = {
    # Temperature aliases
    "celsius": "C",
    "°c": "C",
    "°C": "C",
    "c": "C",
    "fahrenheit": "F",
    "°f": "F",
    "°F": "F",
    "f": "F",
    "kelvin": "K",
    "k": "K",
    # Speed aliases
    "km/h": "kmh",
    "kmph": "kmh",
    "kph": "kmh",
    "m/s": "ms",
    "mps": "ms",
    "mi/h": "mph",
    "knots": "kn",
    "kt": "kn",
    # Length aliases
    "millimeter": "mm",
    "millimeters": "mm",
    "centimeter": "cm",
    "centimeters": "cm",
    "meter": "m",
    "meters": "m",
    "metre": "m",
    "metres": "m",
    "inch": "in",
    "inches": "in",
    "\"": "in",
    "foot": "ft",
    "feet": "ft",
    "'": "ft",
    # Pressure aliases
    "hpa": "hPa",
    "mbar": "hPa",
    "mb": "hPa",
    # Percentage
    "percent": "%",
    "pct": "%",
}


def normalize_unit(unit: str) -> str:
    """Normalize a unit string to its canonical token.

    Args:
        unit: The unit string to normalize (e.g., "km/h", "celsius", "°C").

    Returns:
        The canonical unit token (e.g., "kmh", "C").

    Raises:
        UnitError: If the unit is not recognized.
    """
    # Handle undefined/unknown units
    if unit in ("undefined", "unknown", ""):
        return "undefined"

    # Check if already canonical
    if unit in CANONICAL_UNITS:
        return unit

    # Check aliases
    normalized = UNIT_ALIASES.get(unit.lower())
    if normalized is not None:
        return normalized

    # Try case-sensitive alias lookup
    normalized = UNIT_ALIASES.get(unit)
    if normalized is not None:
        return normalized

    raise UnitError(f"Unknown unit: '{unit}'", unit=unit)


def get_unit_category(unit: str) -> str:
    """Get the category of a canonical unit.

    Args:
        unit: A canonical unit token.

    Returns:
        The category string: "temperature", "speed", "length", "percentage",
        "pressure", "other", or "undefined".

    Raises:
        UnitError: If the unit is not a canonical unit.
    """
    canonical = normalize_unit(unit)

    if canonical == "undefined":
        return "undefined"
    elif canonical in {"C", "F", "K"}:
        return "temperature"
    elif canonical in {"kmh", "ms", "mph", "kn"}:
        return "speed"
    elif canonical in {"mm", "cm", "m", "in", "ft"}:
        return "length"
    elif canonical == "%":
        return "percentage"
    elif canonical == "hPa":
        return "pressure"
    elif canonical in {"W/m²", "°"}:
        return "other"
    else:
        raise UnitError(f"Unknown unit category for: '{unit}'", unit=unit)

