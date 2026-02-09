"""Parser for GRIB2 data extracted via Herbie."""

from __future__ import annotations

import math
from datetime import datetime, timezone


def de_accumulate(values: list[float | None]) -> list[float | None]:
    """De-accumulate a series of accumulated values (e.g., APCP, ASNOW).

    GRIB2 fields like APCP and ASNOW are accumulated from the start of the
    forecast run. This converts them to per-step (hourly) increments.

    Args:
        values: Accumulated values from consecutive forecast hours.

    Returns:
        Per-step incremental values.
    """
    if not values:
        return []

    result: list[float | None] = []
    prev = 0.0

    for i, val in enumerate(values):
        if val is None:
            result.append(None)
        elif i == 0:
            # First hour: the accumulated value IS the hourly value
            result.append(max(0.0, val))
            prev = val
        else:
            increment = val - prev
            # Clamp to 0 — small negative values can occur from floating-point
            result.append(max(0.0, increment))
            prev = val

    return result


def compute_wind_speed(u_values: list[float | None], v_values: list[float | None]) -> list[float | None]:
    """Compute wind speed from U and V components.

    Args:
        u_values: U-component (east-west) wind values in m/s.
        v_values: V-component (north-south) wind values in m/s.

    Returns:
        Wind speed values in km/h.
    """
    if len(u_values) != len(v_values):
        raise ValueError(
            f"U and V arrays must be same length: {len(u_values)} vs {len(v_values)}"
        )

    result: list[float | None] = []
    for u, v in zip(u_values, v_values):
        if u is None or v is None:
            result.append(None)
        else:
            speed_ms = math.sqrt(u * u + v * v)
            speed_kmh = speed_ms * 3.6  # m/s -> km/h
            result.append(speed_kmh)

    return result


def estimate_wind_gusts(
    wind_speed_kmh: list[float | None],
    gust_values: list[float | None] | None = None,
    gust_factor: float = 1.5,
) -> list[float | None]:
    """Get wind gusts, estimating from wind speed if not available.

    ECMWF models don't provide direct gust output. For those, we estimate
    gusts as gust_factor * wind speed.

    Args:
        wind_speed_kmh: Wind speed values in km/h.
        gust_values: Direct gust values in km/h if available.
        gust_factor: Multiplier for estimating gusts (default 1.5).

    Returns:
        Wind gust values in km/h.
    """
    if gust_values is not None and len(gust_values) == len(wind_speed_kmh):
        # Use direct gust values, but convert from m/s to km/h if needed
        return gust_values

    # Estimate gusts from wind speed
    result: list[float | None] = []
    for speed in wind_speed_kmh:
        if speed is None:
            result.append(None)
        else:
            result.append(speed * gust_factor)

    return result


def build_hourly_data(
    extracted_points: list[dict],
    model_id: str,
) -> tuple[dict[str, tuple[float | None, ...]], dict[str, str]]:
    """Build hourly_data and hourly_units dicts from extracted GRIB2 point data.

    Takes a list of dicts (one per forecast hour) with raw GRIB2 variable values,
    and produces the format expected by the Forecast dataclass.

    Args:
        extracted_points: List of dicts with keys like 'temperature', 'precipitation',
            'snowfall', 'wind_u', 'wind_v', 'wind_gusts', 'freezing_level'.
            One dict per forecast hour, ordered by time.
        model_id: The model ID (used to determine gust estimation).

    Returns:
        Tuple of (hourly_data, hourly_units) matching Forecast format.
    """
    if not extracted_points:
        return {}, {}

    # Extract per-variable arrays
    temps = [p.get("temperature") for p in extracted_points]
    precip_accum = [p.get("precipitation") for p in extracted_points]
    snow_accum = [p.get("snowfall") for p in extracted_points]
    wind_u = [p.get("wind_u") for p in extracted_points]
    wind_v = [p.get("wind_v") for p in extracted_points]
    raw_gusts = [p.get("wind_gusts") for p in extracted_points]
    freezing = [p.get("freezing_level") for p in extracted_points]

    # ECMWF tp/sf are in meters; convert to mm (×1000) to match NCEP convention
    is_ecmwf = model_id in ("ifs", "aifs", "ecmwf_ens")
    if is_ecmwf:
        precip_accum = [
            p * 1000.0 if p is not None else None for p in precip_accum
        ]
        # TODO: ECMWF sf is snowfall water equivalent (not snow depth like NCEP
        # ASNOW). After ×1000 + de-accumulation the m→cm conversion below won't
        # produce true snow depth. sf is excluded for AIFS/ECMWF ENS; for IFS
        # the enhanced_snowfall (from precip + temperature) is what the frontend
        # uses, so this is acceptable for now.
        snow_accum = [
            s * 1000.0 if s is not None else None for s in snow_accum
        ]

    # De-accumulate precipitation and snowfall
    precip_hourly = de_accumulate(precip_accum)
    snow_hourly = de_accumulate(snow_accum)

    # Compute wind speed from U/V components
    wind_speed = compute_wind_speed(wind_u, wind_v)

    # Get or estimate wind gusts
    is_ecmwf = model_id in ("ifs", "aifs", "ecmwf_ens")
    if is_ecmwf and all(g is None for g in raw_gusts):
        gusts = estimate_wind_gusts(wind_speed, gust_factor=1.5)
    else:
        # Convert raw gusts from m/s to km/h
        gusts_kmh: list[float | None] = []
        for g in raw_gusts:
            if g is None:
                gusts_kmh.append(None)
            else:
                gusts_kmh.append(g * 3.6)
        gusts = estimate_wind_gusts(wind_speed, gusts_kmh)

    # Convert snowfall from meters to centimeters (GRIB2 ASNOW is in meters)
    snow_cm: list[float | None] = []
    for s in snow_hourly:
        if s is None:
            snow_cm.append(None)
        else:
            snow_cm.append(s * 100.0)

    # Temperature: GRIB2 is in Kelvin, convert to Celsius
    temps_c: list[float | None] = []
    for t in temps:
        if t is None:
            temps_c.append(None)
        else:
            temps_c.append(t - 273.15)

    hourly_data: dict[str, tuple[float | None, ...]] = {
        "temperature_2m": tuple(temps_c),
        "wind_speed_10m": tuple(wind_speed),
        "wind_gusts_10m": tuple(gusts),
        "snowfall": tuple(snow_cm),
        "precipitation": tuple(precip_hourly),
        "freezing_level_height": tuple(freezing),
    }

    hourly_units: dict[str, str] = {
        "temperature_2m": "C",
        "wind_speed_10m": "kmh",
        "wind_gusts_10m": "kmh",
        "snowfall": "cm",
        "precipitation": "mm",
        "freezing_level_height": "m",
    }

    return hourly_data, hourly_units
