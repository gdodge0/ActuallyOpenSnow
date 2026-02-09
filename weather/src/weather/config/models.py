"""Forecast model registry and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from weather.domain.errors import ModelError


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Configuration for a forecast model.

    Attributes:
        model_id: The canonical model identifier (e.g., "gfs").
        api_model: The Open-Meteo API model parameter value.
        display_name: Human-readable model name.
        provider: The organization providing the model.
        max_forecast_days: Maximum forecast horizon in days.
        resolution_degrees: Horizontal resolution in degrees.
        description: Brief description of the model.
        herbie_model: The model name used by the Herbie library.
        herbie_product: The product string for Herbie.
        update_interval_hours: How often the model updates (in hours).
        is_ensemble: Whether this is an ensemble model.
        availability_buffer_hours: Hours to wait after run time for data availability.
        min_fxx: Minimum forecast hour to include (skips analysis time for models
            that don't publish useful data at fxx=0).
    """

    model_id: str
    api_model: str
    display_name: str
    provider: str
    max_forecast_days: int
    resolution_degrees: float
    description: str
    herbie_model: str | None = None
    herbie_product: str | None = None
    update_interval_hours: int = 6
    is_ensemble: bool = False
    availability_buffer_hours: int = 3
    forecast_steps: tuple[tuple[int, int], ...] | None = None
    min_fxx: int = 0


def get_fxx_range(config: ModelConfig) -> list[int]:
    """Generate the list of forecast hours for a model based on its forecast_steps.

    Args:
        config: ModelConfig instance.

    Returns:
        List of valid forecast hours for the model.
    """
    if config.forecast_steps is None:
        max_fxx = config.max_forecast_days * 24
        return list(range(config.min_fxx, max_fxx + 1))
    hours: list[int] = []
    prev_end = 0
    for i, (end_hour, step) in enumerate(config.forecast_steps):
        start = prev_end if i == 0 else prev_end + step
        hours.extend(range(start, end_hour + 1, step))
        prev_end = end_hour
    return [h for h in hours if h >= config.min_fxx]


# Registry of supported forecast models
MODELS: dict[str, ModelConfig] = {
    "gfs": ModelConfig(
        model_id="gfs",
        api_model="gfs_seamless",
        display_name="GFS",
        provider="NOAA",
        max_forecast_days=16,
        resolution_degrees=0.25,
        description="Global Forecast System - NOAA's primary global weather model",
        herbie_model="gfs",
        herbie_product="pgrb2.0p25",
        update_interval_hours=6,
        forecast_steps=((120, 1), (384, 3)),
    ),
    "ifs": ModelConfig(
        model_id="ifs",
        api_model="ecmwf_ifs025",
        display_name="IFS",
        provider="ECMWF",
        max_forecast_days=10,
        resolution_degrees=0.25,
        description="Integrated Forecasting System - ECMWF's operational model",
        herbie_model="ifs",
        herbie_product="oper",
        update_interval_hours=12,
        availability_buffer_hours=6,
        forecast_steps=((144, 3), (240, 6)),
        min_fxx=3,
    ),
    "aifs": ModelConfig(
        model_id="aifs",
        api_model="ecmwf_aifs025_single",
        display_name="AIFS",
        provider="ECMWF",
        max_forecast_days=15,
        resolution_degrees=0.25,
        description="Artificial Intelligence Forecast System - ECMWF's AI-based model",
        herbie_model="aifs",
        herbie_product="oper",
        update_interval_hours=12,
        availability_buffer_hours=6,
        forecast_steps=((360, 6),),
        min_fxx=6,
    ),
    # Additional models that could be added
    "icon": ModelConfig(
        model_id="icon",
        api_model="icon_seamless",
        display_name="ICON",
        provider="DWD",
        max_forecast_days=7,
        resolution_degrees=0.125,
        description="Icosahedral Nonhydrostatic Model - DWD's global model",
    ),
    "jma": ModelConfig(
        model_id="jma",
        api_model="jma_seamless",
        display_name="JMA",
        provider="JMA",
        max_forecast_days=11,
        resolution_degrees=0.25,
        description="Japan Meteorological Agency global model",
    ),
    "hrrr": ModelConfig(
        model_id="hrrr",
        api_model="",
        display_name="HRRR",
        provider="NOAA",
        max_forecast_days=2,
        resolution_degrees=0.03,
        description="High-Resolution Rapid Refresh - NOAA's 3km model",
        herbie_model="hrrr",
        herbie_product="sfc",
        update_interval_hours=1,
        forecast_steps=((48, 1),),
    ),
    "nbm": ModelConfig(
        model_id="nbm",
        api_model="",
        display_name="NBM",
        provider="NOAA",
        max_forecast_days=7,
        resolution_degrees=0.025,
        description="National Blend of Models - NOAA's statistically post-processed blend",
        herbie_model="nbm",
        herbie_product="co",
        update_interval_hours=3,
        forecast_steps=((36, 1), (168, 3)),
    ),
    "gefs": ModelConfig(
        model_id="gefs",
        api_model="",
        display_name="GEFS",
        provider="NOAA",
        max_forecast_days=16,
        resolution_degrees=0.25,
        description="Global Ensemble Forecast System - NOAA's 30-member ensemble",
        herbie_model="gefs",
        herbie_product="atmos.5",
        update_interval_hours=6,
        is_ensemble=True,
        forecast_steps=((240, 3), (384, 6)),
        min_fxx=3,
    ),
    "ecmwf_ens": ModelConfig(
        model_id="ecmwf_ens",
        api_model="",
        display_name="ECMWF ENS",
        provider="ECMWF",
        max_forecast_days=15,
        resolution_degrees=0.25,
        description="ECMWF Ensemble - 51-member ensemble prediction system",
        herbie_model="ifs",
        herbie_product="enfo",
        update_interval_hours=12,
        is_ensemble=True,
        availability_buffer_hours=6,
        forecast_steps=((144, 3), (360, 6)),
        min_fxx=3,
    ),
}

# Model aliases for convenience
MODEL_ALIASES: dict[str, str] = {
    "noaa": "gfs",
    "global": "gfs",
    "ecmwf": "ifs",
    "european": "ifs",
    "ai": "aifs",
    "german": "icon",
    "dwd": "icon",
    "japan": "jma",
    "hrrr3km": "hrrr",
    "ensemble": "gefs",
    "ens": "ecmwf_ens",
    "national_blend": "nbm",
    "blend_of_models": "nbm",
}


def validate_model_id(model_id: str) -> str:
    """Validate and normalize a model ID.

    Args:
        model_id: The model ID to validate (can be an alias).

    Returns:
        The canonical model ID.

    Raises:
        ModelError: If the model ID is not recognized.
    """
    normalized = model_id.lower().strip()

    # Check direct match
    if normalized in MODELS:
        return normalized

    # Check aliases
    if normalized in MODEL_ALIASES:
        return MODEL_ALIASES[normalized]

    available = ", ".join(sorted(MODELS.keys()))
    raise ModelError(
        f"Unknown model: '{model_id}'. Available models: {available}",
        model_id=model_id,
    )


def get_model_config(model_id: str) -> ModelConfig:
    """Get the configuration for a model.

    Args:
        model_id: The model ID (can be an alias).

    Returns:
        The ModelConfig for the specified model.

    Raises:
        ModelError: If the model ID is not recognized.
    """
    canonical_id = validate_model_id(model_id)
    return MODELS[canonical_id]


def list_available_models() -> list[ModelConfig]:
    """List all available forecast models.

    Returns:
        List of ModelConfig objects for all supported models.
    """
    return list(MODELS.values())

