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

__version__ = "0.1.0"

__all__ = [
    # Main client
    "MeteoClient",
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
]

