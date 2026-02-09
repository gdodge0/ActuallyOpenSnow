"""Blend computation logic."""

from __future__ import annotations

from typing import Any

from engine.config import BLEND_WEIGHTS


def compute_blend(
    forecasts: dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute a weighted-average blend from multiple model forecasts.

    Args:
        forecasts: Dict mapping model_id to forecast data dict.
            Each dict must have: times_utc, hourly_data, hourly_units.
        weights: Optional weight overrides. Defaults to BLEND_WEIGHTS.

    Returns:
        Blended forecast data dict with times_utc, hourly_data, hourly_units,
        enhanced_hourly_data, enhanced_hourly_units.
    """
    if not forecasts:
        raise ValueError("No forecasts to blend")

    model_weights = weights or BLEND_WEIGHTS

    # Use first forecast as template
    first_data = next(iter(forecasts.values()))
    variables = list(first_data["hourly_data"].keys())
    min_hours = min(len(f["times_utc"]) for f in forecasts.values())

    # Blend hourly_data
    blended_hourly: dict[str, list[float | None]] = {}
    for var in variables:
        blended_values: list[float | None] = []
        for hour_idx in range(min_hours):
            weighted_sum = 0.0
            total_weight = 0.0

            for model_id, fdata in forecasts.items():
                if var not in fdata["hourly_data"]:
                    continue
                values = fdata["hourly_data"][var]
                if hour_idx >= len(values):
                    continue
                val = values[hour_idx]
                if val is not None:
                    w = model_weights.get(model_id, 1.0)
                    weighted_sum += val * w
                    total_weight += w

            if total_weight > 0:
                blended_values.append(weighted_sum / total_weight)
            else:
                blended_values.append(None)

        blended_hourly[var] = blended_values

    # Blend enhanced data
    enhanced_vars = ["enhanced_snowfall", "rain"]
    blended_enhanced: dict[str, list[float]] = {}

    for var in enhanced_vars:
        blended_values_e: list[float] = []
        for hour_idx in range(min_hours):
            weighted_sum = 0.0
            total_weight = 0.0

            for model_id, fdata in forecasts.items():
                edata = fdata.get("enhanced_hourly_data") or {}
                if var not in edata:
                    continue
                values = edata[var]
                if hour_idx >= len(values):
                    continue
                val = values[hour_idx]
                if val is not None:
                    w = model_weights.get(model_id, 1.0)
                    weighted_sum += val * w
                    total_weight += w

            if total_weight > 0:
                blended_values_e.append(weighted_sum / total_weight)
            else:
                blended_values_e.append(0.0)

        blended_enhanced[var] = blended_values_e

    return {
        "times_utc": first_data["times_utc"][:min_hours],
        "hourly_data": blended_hourly,
        "hourly_units": first_data["hourly_units"],
        "enhanced_hourly_data": blended_enhanced,
        "enhanced_hourly_units": {"enhanced_snowfall": "cm", "rain": "mm"},
    }


def compute_ensemble_ranges(
    ensemble_forecasts: dict[str, dict[str, Any]],
    variables: list[str] | None = None,
) -> dict[str, dict[str, list[float]]]:
    """Compute ensemble prediction ranges (10th/90th percentile).

    Args:
        ensemble_forecasts: Dict mapping model_id to forecast data.
            Only ensemble models (GEFS, ECMWF ENS) should be included.
        variables: Variables to compute ranges for. Defaults to
            enhanced_snowfall, temperature_2m, precipitation.

    Returns:
        Dict of {variable: {p10: [...], p90: [...]}}.
    """
    if not ensemble_forecasts:
        return {}

    if variables is None:
        variables = ["enhanced_snowfall", "temperature_2m", "precipitation"]

    min_hours = min(len(f["times_utc"]) for f in ensemble_forecasts.values())
    ranges: dict[str, dict[str, list[float]]] = {}

    for var in variables:
        p10_values: list[float] = []
        p90_values: list[float] = []

        for hour_idx in range(min_hours):
            hour_values: list[float] = []

            for fdata in ensemble_forecasts.values():
                # Check enhanced data first, then hourly_data
                edata = fdata.get("enhanced_hourly_data") or {}
                if var in edata and hour_idx < len(edata[var]):
                    val = edata[var][hour_idx]
                    if val is not None:
                        hour_values.append(val)
                elif var in fdata.get("hourly_data", {}) and hour_idx < len(fdata["hourly_data"][var]):
                    val = fdata["hourly_data"][var][hour_idx]
                    if val is not None:
                        hour_values.append(val)

            if hour_values:
                sorted_vals = sorted(hour_values)
                n = len(sorted_vals)
                p10_idx = max(0, int(n * 0.1))
                p90_idx = min(n - 1, int(n * 0.9))
                p10_values.append(sorted_vals[p10_idx])
                p90_values.append(sorted_vals[p90_idx])
            else:
                p10_values.append(0.0)
                p90_values.append(0.0)

        ranges[var] = {"p10": p10_values, "p90": p90_values}

    return ranges
