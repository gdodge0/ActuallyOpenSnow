"""Decode Open-Meteo unit strings and FlatBuffers unit enums."""

from __future__ import annotations

from weather.units.normalize import normalize_unit

# Open-Meteo hourly_units response strings -> canonical tokens
OPENMETEO_UNIT_MAP: dict[str, str] = {
    # Temperature
    "°C": "C",
    "°F": "F",
    # Speed
    "km/h": "kmh",
    "m/s": "ms",
    "mph": "mph",
    "kn": "kn",
    "knots": "kn",
    # Length/Precipitation
    "mm": "mm",
    "cm": "cm",
    "m": "m",
    "inch": "in",
    "in": "in",
    "ft": "ft",
    # Pressure
    "hPa": "hPa",
    # Percentage
    "%": "%",
    # Other
    "W/m²": "W/m²",
    "°": "°",
    # ISO8601 time format (just pass through)
    "iso8601": "iso8601",
    "unixtime": "unixtime",
}

# FlatBuffers Unit enum values (from Open-Meteo SDK)
# These are the integer values from the Unit enum in the FlatBuffers schema
# Updated to match current Open-Meteo API (as of late 2024)
FLATBUFFERS_UNIT_ENUM: dict[int, str] = {
    0: "undefined",
    1: "C",
    2: "F",
    3: "mm",
    4: "cm",
    5: "m",
    6: "in",
    7: "ft",
    8: "kmh",
    9: "ms",
    10: "mph",
    11: "kn",
    12: "%",
    13: "hPa",
    14: "W/m²",
    15: "°",
    16: "J/kg",
    17: "μg/m³",
    18: "grains/m³",
    19: "iso8601",
    20: "unixtime",
    # Additional units from newer Open-Meteo SDK versions
    21: "s",        # seconds
    22: "K",        # Kelvin
    23: "m³/m³",    # soil moisture (volumetric)
    24: "kmh",      # km/h (duplicate/alternative encoding)
    25: "ms",       # m/s (duplicate/alternative encoding)
    26: "mph",      # mph (duplicate/alternative encoding)
    27: "kn",       # knots (duplicate/alternative encoding)
    28: "cm",       # cm (duplicate/alternative encoding for snow)
    29: "m",        # meters (duplicate/alternative encoding for heights)
    30: "ft",       # feet (duplicate/alternative encoding)
    31: "in",       # inches (duplicate/alternative encoding)
    32: "mm",       # mm (duplicate/alternative encoding for precip)
    33: "kPa",      # kilopascals
    34: "MJ/m²",    # solar radiation (daily)
    35: "kg/m²",    # mass per area
    36: "gpm",      # geopotential meters
}


def decode_openmeteo_unit(unit: str | int) -> str:
    """Decode an Open-Meteo unit to a canonical token.

    Args:
        unit: Either a unit string from the JSON API's hourly_units,
              or an integer enum value from FlatBuffers Variables(i).Unit().

    Returns:
        The canonical unit token.

    Raises:
        ValueError: If the unit is not recognized.
    """
    if isinstance(unit, int):
        # FlatBuffers enum value
        if unit in FLATBUFFERS_UNIT_ENUM:
            result = FLATBUFFERS_UNIT_ENUM[unit]
            if result in ("undefined", "iso8601", "unixtime"):
                return result
            return normalize_unit(result)
        raise ValueError(f"Unknown FlatBuffers unit enum value: {unit}")

    # String from JSON API
    if unit in OPENMETEO_UNIT_MAP:
        result = OPENMETEO_UNIT_MAP[unit]
        if result in ("iso8601", "unixtime"):
            return result
        return normalize_unit(result)

    # Try normalizing directly
    try:
        return normalize_unit(unit)
    except Exception:
        raise ValueError(f"Unknown Open-Meteo unit string: '{unit}'")


def get_default_unit(variable_name: str) -> str:
    """Get the default unit for a variable name.

    Args:
        variable_name: The Open-Meteo variable name (e.g., "temperature_2m").

    Returns:
        The default canonical unit for that variable.
    """
    variable_defaults: dict[str, str] = {
        "temperature_2m": "C",
        "apparent_temperature": "C",
        "dew_point_2m": "C",
        "wind_speed_10m": "kmh",
        "wind_speed_80m": "kmh",
        "wind_speed_120m": "kmh",
        "wind_gusts_10m": "kmh",
        "wind_direction_10m": "°",
        "precipitation": "mm",
        "rain": "mm",
        "showers": "mm",
        "snowfall": "cm",  # Note: Open-Meteo returns snowfall in cm by default
        "snow_depth": "m",
        "freezing_level_height": "m",
        "relative_humidity_2m": "%",
        "surface_pressure": "hPa",
        "cloud_cover": "%",
        "visibility": "m",
        "shortwave_radiation": "W/m²",
    }

    return variable_defaults.get(variable_name, "undefined")

