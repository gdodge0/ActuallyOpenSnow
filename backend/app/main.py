"""FastAPI application for ActuallyOpenSnow."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Add weather package to path
weather_path = Path(__file__).parent.parent.parent / "weather" / "src"
sys.path.insert(0, str(weather_path))

from weather import MeteoClient, Forecast, ApiError, ModelError
from weather.config.models import list_available_models, MODELS

from app.models import (
    ForecastResponse,
    ComparisonResponse,
    ModelInfo,
    ErrorResponse,
)
from app.resorts import RESORTS, get_resort_by_slug, Resort


# Global client instance
client: MeteoClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the MeteoClient on startup."""
    global client
    client = MeteoClient(cache_expire_after=1800)  # 30 min cache
    yield
    # Cleanup
    if client:
        client.clear_cache()


app = FastAPI(
    title="ActuallyOpenSnow API",
    description="Mountain weather forecasts for skiers and snowboarders",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins in production (nginx handles security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def forecast_to_response(forecast: Forecast) -> ForecastResponse:
    """Convert a Forecast to a ForecastResponse."""
    data = forecast.to_dict()
    return ForecastResponse(
        lat=data["lat"],
        lon=data["lon"],
        api_lat=data["api_lat"],
        api_lon=data["api_lon"],
        elevation_m=data["elevation_m"],
        model_id=data["model_id"],
        model_run_utc=data["model_run_utc"],
        times_utc=data["times_utc"],
        hourly_data=data["hourly_data"],
        hourly_units=data["hourly_units"],
    )


# ============================================================================
# Health Check
# ============================================================================


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "actuallyopensnow-api"}


# ============================================================================
# Models
# ============================================================================


@app.get("/api/models", response_model=list[ModelInfo])
async def get_models():
    """List all available forecast models."""
    models = list_available_models()
    return [
        ModelInfo(
            model_id=m.model_id,
            display_name=m.display_name,
            provider=m.provider,
            max_forecast_days=m.max_forecast_days,
            resolution_degrees=m.resolution_degrees,
            description=m.description,
        )
        for m in models
    ]


@app.get("/api/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Get details for a specific model."""
    if model_id not in MODELS:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    
    m = MODELS[model_id]
    return ModelInfo(
        model_id=m.model_id,
        display_name=m.display_name,
        provider=m.provider,
        max_forecast_days=m.max_forecast_days,
        resolution_degrees=m.resolution_degrees,
        description=m.description,
    )


# ============================================================================
# Resorts
# ============================================================================


@app.get("/api/resorts", response_model=list[Resort])
async def get_resorts(
    state: Optional[str] = Query(None, description="Filter by state/province code"),
):
    """List all ski resorts."""
    if state:
        return [r for r in RESORTS if r.state.upper() == state.upper()]
    return RESORTS


@app.get("/api/resorts/{slug}", response_model=Resort)
async def get_resort(slug: str):
    """Get a resort by slug."""
    resort = get_resort_by_slug(slug)
    if not resort:
        raise HTTPException(status_code=404, detail=f"Resort '{slug}' not found")
    return resort


# ============================================================================
# Forecasts
# ============================================================================


@app.get("/api/forecast", response_model=ForecastResponse)
async def get_forecast(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    model: str = Query("gfs", description="Forecast model ID"),
    elevation: Optional[float] = Query(None, description="Elevation override in meters"),
):
    """Get a weather forecast for coordinates."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    
    try:
        forecast = client.get_forecast(
            lat=lat,
            lon=lon,
            model=model,
            elevation=elevation,
        )
        return forecast_to_response(forecast)
    except ModelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/api/resorts/{slug}/forecast", response_model=ForecastResponse)
async def get_resort_forecast(
    slug: str,
    model: str = Query("gfs", description="Forecast model ID"),
    elevation: Optional[str] = Query("summit", description="'base', 'summit', or meters"),
):
    """Get forecast for a resort."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    
    resort = get_resort_by_slug(slug)
    if not resort:
        raise HTTPException(status_code=404, detail=f"Resort '{slug}' not found")
    
    # Determine elevation
    elev_m: float | None = None
    if elevation == "summit":
        elev_m = resort.summit_elevation_m
    elif elevation == "base":
        elev_m = resort.base_elevation_m
    elif elevation:
        try:
            elev_m = float(elevation)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Elevation must be 'base', 'summit', or a number in meters",
            )
    
    try:
        forecast = client.get_forecast(
            lat=resort.lat,
            lon=resort.lon,
            model=model,
            elevation=elev_m,
        )
        return forecast_to_response(forecast)
    except ModelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/api/compare", response_model=ComparisonResponse)
async def compare_models(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    models: str = Query("gfs,ifs,aifs", description="Comma-separated model IDs"),
    elevation: Optional[float] = Query(None, description="Elevation override in meters"),
):
    """Compare forecasts from multiple models."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    
    model_ids = [m.strip() for m in models.split(",") if m.strip()]
    if not model_ids:
        raise HTTPException(status_code=400, detail="At least one model required")
    
    forecasts: dict[str, ForecastResponse] = {}
    errors: list[str] = []
    
    for model_id in model_ids:
        try:
            forecast = client.get_forecast(
                lat=lat,
                lon=lon,
                model=model_id,
                elevation=elevation,
            )
            forecasts[model_id] = forecast_to_response(forecast)
        except (ModelError, ApiError) as e:
            errors.append(f"{model_id}: {e}")
    
    if not forecasts:
        raise HTTPException(
            status_code=502,
            detail=f"All models failed: {'; '.join(errors)}",
        )
    
    return ComparisonResponse(
        lat=lat,
        lon=lon,
        elevation_m=elevation,
        forecasts=forecasts,
    )


@app.get("/api/resorts/{slug}/compare", response_model=ComparisonResponse)
async def compare_resort_models(
    slug: str,
    models: str = Query("gfs,ifs,aifs", description="Comma-separated model IDs"),
    elevation: Optional[str] = Query("summit", description="'base', 'summit', or meters"),
):
    """Compare forecasts from multiple models for a resort."""
    resort = get_resort_by_slug(slug)
    if not resort:
        raise HTTPException(status_code=404, detail=f"Resort '{slug}' not found")
    
    # Determine elevation
    elev_m: float | None = None
    if elevation == "summit":
        elev_m = resort.summit_elevation_m
    elif elevation == "base":
        elev_m = resort.base_elevation_m
    elif elevation:
        try:
            elev_m = float(elevation)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Elevation must be 'base', 'summit', or a number in meters",
            )
    
    return await compare_models(
        lat=resort.lat,
        lon=resort.lon,
        models=models,
        elevation=elev_m,
    )

