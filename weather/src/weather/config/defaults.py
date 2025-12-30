"""Default configuration values."""

from __future__ import annotations

# Default forecast model
DEFAULT_MODEL: str = "gfs"

# Cache settings
DEFAULT_CACHE_EXPIRE_AFTER: int = 3600  # 1 hour in seconds

# Retry settings
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_FACTOR: float = 0.5

# Default hourly variables to request
DEFAULT_HOURLY_VARIABLES: tuple[str, ...] = (
    "temperature_2m",
    "wind_speed_10m",
    "wind_gusts_10m",
    "snowfall",
    "precipitation",
    "freezing_level_height",
)

# Default unit preferences
DEFAULT_TEMPERATURE_UNIT: str = "C"
DEFAULT_WIND_SPEED_UNIT: str = "kmh"
DEFAULT_PRECIPITATION_UNIT: str = "mm"
DEFAULT_LENGTH_UNIT: str = "m"

# Maximum forecast horizons in days (requested, actual may be lower per model)
MAX_FORECAST_DAYS: int = 16

# Timezone for all forecast data
FORECAST_TIMEZONE: str = "UTC"

