"""Mountain Weather - A typed Python API for mountain-relevant weather forecasts."""

from weather.clients.openmeteo import MeteoClient
from weather.domain.forecast import Forecast
from weather.domain.quantities import Quantity, Series
from weather.domain.errors import (
    WeatherError,
    ApiError,
    UnitError,
    ModelError,
    RangeError,
)
from weather.utils.snow import (
    get_snow_ratio,
    calculate_snowfall_from_precip,
    calculate_hourly_snowfall,
)

__version__ = "0.1.0"

__all__ = [
    # Main clients
    "MeteoClient",
    "HerbieClient",
    # Data models
    "Forecast",
    "Quantity",
    "Series",
    # Errors
    "WeatherError",
    "ApiError",
    "UnitError",
    "ModelError",
    "RangeError",
    # Snow utilities
    "get_snow_ratio",
    "calculate_snowfall_from_precip",
    "calculate_hourly_snowfall",
]


def __getattr__(name: str):
    """Lazy import for optional dependencies."""
    if name == "HerbieClient":
        from weather.clients.herbie_client import HerbieClient
        return HerbieClient
    raise AttributeError(f"module 'weather' has no attribute {name!r}")

