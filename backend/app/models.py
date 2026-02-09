"""Pydantic models for API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class Resort(BaseModel):
    """Ski resort with coordinates."""

    slug: str = Field(..., description="URL-friendly identifier")
    name: str = Field(..., description="Display name")
    state: str = Field(..., description="State/province code")
    country: str = Field(..., description="Country code")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    base_elevation_m: float = Field(..., description="Base elevation in meters")
    summit_elevation_m: float = Field(..., description="Summit elevation in meters")


class ModelInfo(BaseModel):
    """Forecast model information."""

    model_id: str
    display_name: str
    provider: str
    max_forecast_days: int
    resolution_degrees: float
    description: str


class ForecastResponse(BaseModel):
    """Weather forecast response matching the Python Forecast.to_dict()."""

    lat: float
    lon: float
    api_lat: float
    api_lon: float
    elevation_m: Optional[float]
    model_id: str
    model_run_utc: Optional[str]
    times_utc: list[str]
    hourly_data: dict[str, list[Optional[float]]]
    hourly_units: dict[str, str]
    # Enhanced snowfall data (calculated from precipitation + temperature)
    enhanced_hourly_data: Optional[dict[str, list[float]]] = None
    enhanced_hourly_units: Optional[dict[str, str]] = None
    # Ensemble prediction ranges (10th/90th percentile)
    ensemble_ranges: Optional[dict[str, dict[str, list[float]]]] = None


class ComparisonResponse(BaseModel):
    """Multi-model comparison response."""

    lat: float
    lon: float
    elevation_m: Optional[float]
    forecasts: dict[str, ForecastResponse]


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    error_type: str

