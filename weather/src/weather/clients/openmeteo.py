"""Open-Meteo API client implementation."""

from __future__ import annotations

import logging
import time
from typing import Any

import openmeteo_requests
import requests_cache
from requests.adapters import HTTPAdapter
from retry_requests import retry

from weather.clients.base import BaseClient, ClientConfig
from weather.config.defaults import (
    DEFAULT_MODEL,
    DEFAULT_CACHE_EXPIRE_AFTER,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_HOURLY_VARIABLES,
    MAX_FORECAST_DAYS,
)
from weather.config.models import get_model_config, validate_model_id
from weather.domain.forecast import Forecast
from weather.domain.errors import ApiError
from weather.parsing.openmeteo_parser import parse_openmeteo_response

logger = logging.getLogger(__name__)


class TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that enforces a default timeout on all requests."""

    def __init__(self, timeout: int = 30, *args: Any, **kwargs: Any) -> None:
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        kwargs.setdefault("timeout", self.timeout)
        return super().send(request, **kwargs)


class MeteoClient(BaseClient):
    """Client for the Open-Meteo weather API.

    Uses request caching and automatic retries for reliability.

    Example:
        >>> client = MeteoClient()
        >>> forecast = client.get_forecast(43.48, -110.76, model="gfs")
        >>> print(forecast.get_temperature_2m(unit="F"))
    """

    # Open-Meteo API endpoint
    API_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        cache_expire_after: int = DEFAULT_CACHE_EXPIRE_AFTER,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        timeout: int = 30,
        hourly_variables: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize the Open-Meteo client.

        Args:
            cache_expire_after: Cache TTL in seconds. Default 1 hour.
            max_retries: Maximum retry attempts. Default 3.
            backoff_factor: Backoff multiplier for retries. Default 0.5.
            timeout: Request timeout in seconds. Default 30.
            hourly_variables: Variables to request. Defaults to standard set.
        """
        config = ClientConfig(
            cache_expire_after=cache_expire_after,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            timeout=timeout,
        )
        super().__init__(config)

        self.hourly_variables = hourly_variables or DEFAULT_HOURLY_VARIABLES

        # Set up cached session with retries
        self._setup_session()

    def _setup_session(self) -> None:
        """Configure the requests session with caching, retries, and timeouts."""
        # Create a cached session
        cache_session = requests_cache.CachedSession(
            ".weather_cache",
            expire_after=self.config.cache_expire_after,
        )

        # Mount timeout-aware adapter so all requests enforce the timeout
        timeout_adapter = TimeoutHTTPAdapter(timeout=self.config.timeout)
        cache_session.mount("https://", timeout_adapter)
        cache_session.mount("http://", timeout_adapter)

        # Wrap with retry logic
        retry_session = retry(
            cache_session,
            retries=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
        )

        # Create Open-Meteo client
        self._client = openmeteo_requests.Client(session=retry_session)

    def get_forecast(
        self,
        lat: float,
        lon: float,
        *,
        model: str = DEFAULT_MODEL,
        elevation: float | None = None,
        temperature_unit: str = "celsius",
        wind_speed_unit: str = "kmh",
        precipitation_unit: str = "mm",
    ) -> Forecast:
        """Fetch a weather forecast for a location.

        Args:
            lat: Latitude in degrees (-90 to 90).
            lon: Longitude in degrees (-180 to 180).
            model: Forecast model ID. Default "gfs".
            elevation: Optional elevation override in meters.
            temperature_unit: Preferred temperature unit.
            wind_speed_unit: Preferred wind speed unit.
            precipitation_unit: Preferred precipitation unit.

        Returns:
            A Forecast object with weather data.

        Raises:
            ApiError: If the API request fails.
            ModelError: If the model ID is invalid.
        """
        # Validate and get model configuration
        model_id = validate_model_id(model)
        model_config = get_model_config(model_id)

        # Build request parameters
        params = self._build_params(
            lat=lat,
            lon=lon,
            model_config=model_config,
            elevation=elevation,
            temperature_unit=temperature_unit,
            wind_speed_unit=wind_speed_unit,
            precipitation_unit=precipitation_unit,
        )

        # Log request
        logger.info(
            "Fetching forecast",
            extra={
                "lat": lat,
                "lon": lon,
                "model": model_id,
                "elevation": elevation,
            },
        )

        # Make request
        start_time = time.monotonic()
        try:
            responses = self._client.weather_api(self.API_URL, params=params)
            elapsed = time.monotonic() - start_time

            # Check for cache hit
            cache_hit = False
            if hasattr(self._client, "_session"):
                session = self._client._session
                if hasattr(session, "cache"):
                    # Note: this is a simplification; actual cache hit detection
                    # depends on requests-cache internals
                    cache_hit = getattr(session, "_is_cache_hit", False)

            logger.info(
                "Forecast fetched",
                extra={
                    "lat": lat,
                    "lon": lon,
                    "model": model_id,
                    "elapsed_seconds": round(elapsed, 3),
                    "cache_hit": cache_hit,
                },
            )

        except Exception as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "Forecast request failed",
                extra={
                    "lat": lat,
                    "lon": lon,
                    "model": model_id,
                    "elapsed_seconds": round(elapsed, 3),
                    "error": str(e),
                },
            )
            raise ApiError(f"Failed to fetch forecast: {e}")

        if not responses:
            raise ApiError("Empty response from API")

        # Parse the first response (we only request one location)
        response = responses[0]

        return parse_openmeteo_response(
            response=response,
            requested_lat=lat,
            requested_lon=lon,
            model_id=model_id,
            elevation_override=elevation,
            hourly_variables=self.hourly_variables,
        )

    def _build_params(
        self,
        lat: float,
        lon: float,
        model_config: Any,
        elevation: float | None,
        temperature_unit: str,
        wind_speed_unit: str,
        precipitation_unit: str,
    ) -> dict[str, Any]:
        """Build API request parameters.

        Args:
            lat: Latitude.
            lon: Longitude.
            model_config: Model configuration.
            elevation: Optional elevation override.
            temperature_unit: Temperature unit preference.
            wind_speed_unit: Wind speed unit preference.
            precipitation_unit: Precipitation unit preference.

        Returns:
            Dictionary of API parameters.
        """
        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": list(self.hourly_variables),
            "models": model_config.api_model,
            "forecast_days": min(MAX_FORECAST_DAYS, model_config.max_forecast_days),
            "timezone": "UTC",
        }

        # Add elevation if specified
        if elevation is not None:
            params["elevation"] = elevation

        # Add unit preferences
        # Note: Open-Meteo uses different param names for units
        unit_mapping = {
            "temperature_unit": temperature_unit.lower(),
            "wind_speed_unit": wind_speed_unit.lower(),
            "precipitation_unit": precipitation_unit.lower(),
        }

        # Normalize unit values for API
        if unit_mapping["temperature_unit"] in ("c", "celsius"):
            unit_mapping["temperature_unit"] = "celsius"
        elif unit_mapping["temperature_unit"] in ("f", "fahrenheit"):
            unit_mapping["temperature_unit"] = "fahrenheit"

        if unit_mapping["wind_speed_unit"] == "kmh":
            unit_mapping["wind_speed_unit"] = "kmh"
        elif unit_mapping["wind_speed_unit"] == "ms":
            unit_mapping["wind_speed_unit"] = "ms"
        elif unit_mapping["wind_speed_unit"] == "mph":
            unit_mapping["wind_speed_unit"] = "mph"
        elif unit_mapping["wind_speed_unit"] == "kn":
            unit_mapping["wind_speed_unit"] = "kn"

        if unit_mapping["precipitation_unit"] in ("mm", "millimeter"):
            unit_mapping["precipitation_unit"] = "mm"
        elif unit_mapping["precipitation_unit"] in ("in", "inch"):
            unit_mapping["precipitation_unit"] = "inch"

        params.update(unit_mapping)

        return params

    def clear_cache(self) -> None:
        """Clear the request cache."""
        if hasattr(self._client, "_session"):
            session = self._client._session
            if hasattr(session, "cache"):
                session.cache.clear()
                logger.info("Cache cleared")

