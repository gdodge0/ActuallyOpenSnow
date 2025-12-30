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
    """

    model_id: str
    api_model: str
    display_name: str
    provider: str
    max_forecast_days: int
    resolution_degrees: float
    description: str


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
    ),
    "ifs": ModelConfig(
        model_id="ifs",
        api_model="ecmwf_ifs025",
        display_name="IFS",
        provider="ECMWF",
        max_forecast_days=10,
        resolution_degrees=0.25,
        description="Integrated Forecasting System - ECMWF's operational model",
    ),
    "aifs": ModelConfig(
        model_id="aifs",
        api_model="ecmwf_aifs025_single",
        display_name="AIFS",
        provider="ECMWF",
        max_forecast_days=15,
        resolution_degrees=0.25,
        description="Artificial Intelligence Forecast System - ECMWF's AI-based model",
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

