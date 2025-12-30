"""Base client interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from weather.domain.forecast import Forecast


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """Configuration for a weather client.

    Attributes:
        cache_expire_after: Cache TTL in seconds (default 3600).
        max_retries: Maximum retry attempts (default 3).
        backoff_factor: Exponential backoff multiplier (default 0.5).
        timeout: Request timeout in seconds (default 30).
    """

    cache_expire_after: int = 3600
    max_retries: int = 3
    backoff_factor: float = 0.5
    timeout: int = 30


@runtime_checkable
class WeatherClient(Protocol):
    """Protocol for weather API clients."""

    def get_forecast(
        self,
        lat: float,
        lon: float,
        *,
        model: str = "gfs",
        elevation: float | None = None,
        temperature_unit: str = "C",
        wind_speed_unit: str = "kmh",
        precipitation_unit: str = "mm",
    ) -> Forecast:
        """Fetch a weather forecast for a location.

        Args:
            lat: Latitude in degrees (-90 to 90).
            lon: Longitude in degrees (-180 to 180).
            model: Forecast model ID (default "gfs").
            elevation: Optional elevation override in meters.
            temperature_unit: Preferred temperature unit.
            wind_speed_unit: Preferred wind speed unit.
            precipitation_unit: Preferred precipitation unit.

        Returns:
            A Forecast object with weather data.
        """
        ...


class BaseClient(ABC):
    """Abstract base class for weather clients.

    Provides common functionality for caching, retries, and logging.
    """

    def __init__(self, config: ClientConfig | None = None) -> None:
        """Initialize the client.

        Args:
            config: Optional client configuration.
        """
        self.config = config or ClientConfig()

    @abstractmethod
    def get_forecast(
        self,
        lat: float,
        lon: float,
        *,
        model: str = "gfs",
        elevation: float | None = None,
        temperature_unit: str = "C",
        wind_speed_unit: str = "kmh",
        precipitation_unit: str = "mm",
    ) -> Forecast:
        """Fetch a weather forecast for a location."""
        ...

