"""On-demand point extraction API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ExtractionRequest(BaseModel):
    """Request for on-demand point extraction."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    elevation: float | None = Field(None, ge=0, le=9000)
    model: str = Field("blend", description="Model ID or 'blend'")


class ExtractionResponse(BaseModel):
    """Response from on-demand extraction."""
    lat: float
    lon: float
    elevation_m: float | None
    model_id: str
    times_utc: list[str]
    hourly_data: dict[str, list[float | None]]
    hourly_units: dict[str, str]
    enhanced_hourly_data: dict[str, list[float]] | None = None
    enhanced_hourly_units: dict[str, str] | None = None


@router.post("/extract", response_model=ExtractionResponse)
async def extract_point(request: ExtractionRequest):
    """On-demand point extraction from cached GRIB2 files.

    Extracts forecast data for custom coordinates from cached GRIB2 grids
    (no re-download needed). Falls back to a fresh Herbie download if
    cached data is unavailable.
    """
    from weather.clients.herbie_client import HerbieClient
    from weather.config.models import get_model_config, validate_model_id
    from engine.config import GRIB_CACHE_DIR

    model_id = request.model
    if model_id == "blend":
        model_id = "gfs"  # Default to GFS for custom extractions

    try:
        model_id = validate_model_id(model_id)
        config = get_model_config(model_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not config.herbie_model:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model_id}' does not support GRIB2 extraction",
        )

    client = HerbieClient(cache_dir=GRIB_CACHE_DIR)

    try:
        forecast = client.get_forecast(
            lat=request.lat,
            lon=request.lon,
            model=model_id,
            elevation=request.elevation,
        )
        data = forecast.to_dict(include_enhanced=True)

        return ExtractionResponse(
            lat=data["lat"],
            lon=data["lon"],
            elevation_m=data["elevation_m"],
            model_id=data["model_id"],
            times_utc=data["times_utc"],
            hourly_data=data["hourly_data"],
            hourly_units=data["hourly_units"],
            enhanced_hourly_data=data.get("enhanced_hourly_data"),
            enhanced_hourly_units=data.get("enhanced_hourly_units"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
