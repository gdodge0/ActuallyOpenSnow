"""Configuration for weather API."""

from weather.config.defaults import (
    DEFAULT_MODEL,
    DEFAULT_CACHE_EXPIRE_AFTER,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_HOURLY_VARIABLES,
    DEFAULT_TEMPERATURE_UNIT,
    DEFAULT_WIND_SPEED_UNIT,
    DEFAULT_PRECIPITATION_UNIT,
    DEFAULT_LENGTH_UNIT,
)
from weather.config.models import (
    ModelConfig,
    MODELS,
    get_model_config,
    validate_model_id,
    list_available_models,
)

__all__ = [
    # Defaults
    "DEFAULT_MODEL",
    "DEFAULT_CACHE_EXPIRE_AFTER",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_HOURLY_VARIABLES",
    "DEFAULT_TEMPERATURE_UNIT",
    "DEFAULT_WIND_SPEED_UNIT",
    "DEFAULT_PRECIPITATION_UNIT",
    "DEFAULT_LENGTH_UNIT",
    # Models
    "ModelConfig",
    "MODELS",
    "get_model_config",
    "validate_model_id",
    "list_available_models",
]

