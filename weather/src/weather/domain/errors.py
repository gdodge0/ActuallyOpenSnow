"""Custom exceptions for the weather package."""

from __future__ import annotations


class WeatherError(Exception):
    """Base exception for all weather-related errors."""

    pass


class ApiError(WeatherError):
    """Raised when an API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.status_code is not None:
            parts.append(f"(status={self.status_code})")
        return " ".join(parts)


class UnitError(WeatherError):
    """Raised when a unit conversion fails or an invalid unit is specified."""

    def __init__(self, message: str, unit: str | None = None) -> None:
        super().__init__(message)
        self.unit = unit


class ModelError(WeatherError):
    """Raised when an invalid or unsupported model is specified."""

    def __init__(self, message: str, model_id: str | None = None) -> None:
        super().__init__(message)
        self.model_id = model_id


class RangeError(WeatherError):
    """Raised when a time range is invalid or out of bounds."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

