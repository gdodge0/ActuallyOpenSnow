"""Unit conversion functions."""

from __future__ import annotations

from weather.domain.errors import UnitError
from weather.domain.quantities import Series
from weather.units.normalize import normalize_unit, get_unit_category


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature value between units.

    Args:
        value: The temperature value to convert.
        from_unit: Source unit (C, F, or K).
        to_unit: Target unit (C, F, or K).

    Returns:
        The converted temperature value.

    Raises:
        UnitError: If either unit is not a valid temperature unit.
    """
    from_canonical = normalize_unit(from_unit)
    to_canonical = normalize_unit(to_unit)

    if from_canonical == to_canonical:
        return value

    # Validate units are temperature
    for unit in (from_canonical, to_canonical):
        if unit not in {"C", "F", "K"}:
            raise UnitError(f"Not a temperature unit: '{unit}'", unit=unit)

    # Convert to Celsius first
    if from_canonical == "C":
        celsius = value
    elif from_canonical == "F":
        celsius = (value - 32) * 5 / 9
    else:  # K
        celsius = value - 273.15

    # Convert from Celsius to target
    if to_canonical == "C":
        return celsius
    elif to_canonical == "F":
        return celsius * 9 / 5 + 32
    else:  # K
        return celsius + 273.15


def convert_speed(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a speed value between units.

    Args:
        value: The speed value to convert.
        from_unit: Source unit (kmh, ms, mph, or kn).
        to_unit: Target unit (kmh, ms, mph, or kn).

    Returns:
        The converted speed value.

    Raises:
        UnitError: If either unit is not a valid speed unit.
    """
    from_canonical = normalize_unit(from_unit)
    to_canonical = normalize_unit(to_unit)

    if from_canonical == to_canonical:
        return value

    # Validate units are speed
    for unit in (from_canonical, to_canonical):
        if unit not in {"kmh", "ms", "mph", "kn"}:
            raise UnitError(f"Not a speed unit: '{unit}'", unit=unit)

    # Conversion factors to m/s
    to_ms = {
        "ms": 1.0,
        "kmh": 1 / 3.6,
        "mph": 0.44704,
        "kn": 0.514444,
    }

    # Convert to m/s, then to target
    ms_value = value * to_ms[from_canonical]
    return ms_value / to_ms[to_canonical]


def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a length value between units.

    Args:
        value: The length value to convert.
        from_unit: Source unit (mm, cm, m, in, or ft).
        to_unit: Target unit (mm, cm, m, in, or ft).

    Returns:
        The converted length value.

    Raises:
        UnitError: If either unit is not a valid length unit.
    """
    from_canonical = normalize_unit(from_unit)
    to_canonical = normalize_unit(to_unit)

    if from_canonical == to_canonical:
        return value

    # Validate units are length
    for unit in (from_canonical, to_canonical):
        if unit not in {"mm", "cm", "m", "in", "ft"}:
            raise UnitError(f"Not a length unit: '{unit}'", unit=unit)

    # Conversion factors to meters
    to_m = {
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "in": 0.0254,
        "ft": 0.3048,
    }

    # Convert to meters, then to target
    m_value = value * to_m[from_canonical]
    return m_value / to_m[to_canonical]


def convert_value(
    value: float,
    from_unit: str,
    to_unit: str,
) -> float:
    """Convert a value between units, auto-detecting the category.

    Args:
        value: The value to convert.
        from_unit: Source unit.
        to_unit: Target unit.

    Returns:
        The converted value.

    Raises:
        UnitError: If units are incompatible or unknown.
    """
    from_canonical = normalize_unit(from_unit)
    to_canonical = normalize_unit(to_unit)

    if from_canonical == to_canonical:
        return value

    # Handle undefined units - cannot convert
    if from_canonical == "undefined":
        raise UnitError(
            f"Cannot convert from undefined unit to '{to_unit}'",
            unit=from_unit,
        )
    if to_canonical == "undefined":
        raise UnitError(
            f"Cannot convert from '{from_unit}' to undefined unit",
            unit=to_unit,
        )

    from_category = get_unit_category(from_canonical)
    to_category = get_unit_category(to_canonical)

    if from_category != to_category:
        raise UnitError(
            f"Cannot convert between incompatible units: "
            f"'{from_unit}' ({from_category}) and '{to_unit}' ({to_category})"
        )

    if from_category == "temperature":
        return convert_temperature(value, from_canonical, to_canonical)
    elif from_category == "speed":
        return convert_speed(value, from_canonical, to_canonical)
    elif from_category == "length":
        return convert_length(value, from_canonical, to_canonical)
    else:
        raise UnitError(
            f"No conversion available for category: '{from_category}'",
            unit=from_unit,
        )


def convert_series(
    series: Series,
    to_unit: str,
) -> Series:
    """Convert all values in a series to a new unit.

    Args:
        series: The series to convert.
        to_unit: Target unit.

    Returns:
        A new Series with converted values and the new unit.

    Raises:
        UnitError: If units are incompatible or unknown.
    """
    to_canonical = normalize_unit(to_unit)
    from_canonical = normalize_unit(series.unit)

    if from_canonical == to_canonical:
        return series

    converted_values = tuple(
        convert_value(v, from_canonical, to_canonical) if v is not None else None
        for v in series.values
    )

    return Series(values=converted_values, unit=to_canonical)

