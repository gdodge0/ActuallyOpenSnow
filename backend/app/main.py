"""FastAPI application for ActuallyOpenSnow."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

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


# Models to include in the blend with their weights
# Configurable via environment variables:
#   BLEND_WEIGHT_GFS=2.0
#   BLEND_WEIGHT_IFS=2.0
#   etc.
# Set weight to 0 to exclude a model from the blend
import os

# Default weights
DEFAULT_BLEND_WEIGHTS = {
    "gfs": 2.0,    # NOAA GFS - reliable global model
    "ifs": 2.0,    # ECMWF IFS - gold standard
    "aifs": 2.0,   # ECMWF AIFS - AI-enhanced
    "icon": 1.0,   # DWD ICON - European model
    "jma": 1.0,    # JMA - Japanese model
}

# All possible blend models
BLEND_MODELS = list(DEFAULT_BLEND_WEIGHTS.keys())


def get_blend_weights() -> dict[str, float]:
    """Get blend weights from environment variables with defaults.
    
    Called on each request to pick up any environment variable changes.
    """
    weights = {}
    for model_id, default_weight in DEFAULT_BLEND_WEIGHTS.items():
        env_var = f"BLEND_WEIGHT_{model_id.upper()}"
        env_value = os.environ.get(env_var)
        
        if env_value is not None:
            try:
                weight = float(env_value)
                if weight > 0:  # Only include models with positive weight
                    weights[model_id] = weight
                # If weight is 0 or negative, exclude model
            except ValueError:
                # Invalid value, use default
                weights[model_id] = default_weight
        else:
            weights[model_id] = default_weight
    
    return weights

# Global client instance
client: MeteoClient | None = None

# Thread pool for parallel API calls (Open-Meteo client is sync)
executor: ThreadPoolExecutor | None = None

# In-memory cache for blend forecasts (TTL managed manually)
# Key: cache_key, Value: (timestamp, ForecastResponse)
blend_cache: dict[str, tuple[float, ForecastResponse]] = {}
BLEND_CACHE_TTL = 1800  # 30 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the MeteoClient on startup."""
    global client, executor, blend_cache
    client = MeteoClient(cache_expire_after=1800)  # 30 min cache
    executor = ThreadPoolExecutor(max_workers=10)  # Parallel API calls
    # Clear blend cache on startup (ensures fresh data after weight changes)
    blend_cache.clear()
    weights = get_blend_weights()
    print(f"[Startup] Blend weights: {weights}")
    print(f"[Startup] Total weight: {sum(weights.values())}")
    yield
    # Cleanup
    if client:
        client.clear_cache()
    if executor:
        executor.shutdown(wait=False)


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


def get_blend_cache_key(lat: float, lon: float, elevation: float | None, weights: dict[str, float]) -> str:
    """Generate a cache key for blend forecasts."""
    # Include weights in cache key so weight changes invalidate cache
    weights_str = ",".join(f"{k}:{v}" for k, v in sorted(weights.items()))
    key_data = f"{lat:.4f}:{lon:.4f}:{elevation}:{weights_str}"
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cached_blend(cache_key: str) -> ForecastResponse | None:
    """Get a cached blend forecast if still valid."""
    if cache_key in blend_cache:
        timestamp, response = blend_cache[cache_key]
        if time.time() - timestamp < BLEND_CACHE_TTL:
            return response
        else:
            # Expired, remove from cache
            del blend_cache[cache_key]
    return None


def set_cached_blend(cache_key: str, response: ForecastResponse) -> None:
    """Cache a blend forecast."""
    blend_cache[cache_key] = (time.time(), response)
    
    # Simple cache eviction: remove oldest entries if cache too large
    if len(blend_cache) > 100:
        oldest_key = min(blend_cache.keys(), key=lambda k: blend_cache[k][0])
        del blend_cache[oldest_key]


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


def create_blend_forecast(
    forecasts: dict[str, dict],  # model_id -> forecast dict
    lat: float,
    lon: float,
    elevation_m: float | None,
    model_run_times: list[datetime],
    weights: dict[str, float],
) -> ForecastResponse:
    """Create a blended forecast using weighted averaging of multiple models.
    
    Args:
        forecasts: Dict mapping model_id to forecast data dict
        lat: Requested latitude
        lon: Requested longitude
        elevation_m: Elevation in meters
        model_run_times: List of model run times
        weights: Weights for each model
    """
    if not forecasts:
        raise ValueError("No forecasts to blend")
    
    model_weights = weights
    
    # Use the first forecast as a template
    first_model_id = next(iter(forecasts.keys()))
    first_data = forecasts[first_model_id]
    
    # Find the minimum number of hours across all forecasts
    min_hours = min(len(f["times_utc"]) for f in forecasts.values())
    
    # Get all variable names from the first forecast
    variables = list(first_data["hourly_data"].keys())
    
    # Weighted average each variable across models
    blended_hourly_data: dict[str, list[float | None]] = {}
    
    for var in variables:
        blended_values: list[float | None] = []
        
        for hour_idx in range(min_hours):
            weighted_sum = 0.0
            total_weight = 0.0
            
            for model_id, forecast_data in forecasts.items():
                if var in forecast_data["hourly_data"]:
                    val = forecast_data["hourly_data"][var][hour_idx]
                    if val is not None:
                        # Get weight for this model (default to 1.0 if not specified)
                        weight = model_weights.get(model_id, 1.0)
                        weighted_sum += val * weight
                        total_weight += weight
            
            if total_weight > 0:
                # Weighted average
                blended_values.append(weighted_sum / total_weight)
            else:
                blended_values.append(None)
        
        blended_hourly_data[var] = blended_values
    
    # Use times from first forecast, truncated to min_hours
    blended_times = first_data["times_utc"][:min_hours]
    
    # Find the latest model run time
    latest_run = max(model_run_times) if model_run_times else None
    
    return ForecastResponse(
        lat=lat,
        lon=lon,
        api_lat=first_data["api_lat"],
        api_lon=first_data["api_lon"],
        elevation_m=elevation_m,
        model_id="blend",
        model_run_utc=latest_run.isoformat() if latest_run else None,
        times_utc=blended_times,
        hourly_data=blended_hourly_data,
        hourly_units=first_data["hourly_units"],
    )


def fetch_single_model(model_id: str, lat: float, lon: float, elevation: float | None) -> tuple[str, Forecast | None, str | None]:
    """Fetch a single model forecast (sync, for thread pool)."""
    if client is None:
        return model_id, None, "Client not initialized"
    
    try:
        forecast = client.get_forecast(
            lat=lat,
            lon=lon,
            model=model_id,
            elevation=elevation,
        )
        return model_id, forecast, None
    except (ModelError, ApiError) as e:
        return model_id, None, str(e)
    except Exception as e:
        return model_id, None, f"Unexpected error: {e}"


async def fetch_blend_forecast(
    lat: float,
    lon: float,
    elevation: float | None,
) -> ForecastResponse:
    """Fetch and blend forecasts from multiple models (parallel)."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    if executor is None:
        raise HTTPException(status_code=503, detail="Thread pool not initialized")
    
    # Get current weights from environment variables
    weights = get_blend_weights()
    
    # Check cache first (cache key includes weights)
    cache_key = get_blend_cache_key(lat, lon, elevation, weights)
    cached = get_cached_blend(cache_key)
    if cached:
        return cached
    
    # Fetch all models in parallel using thread pool
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(executor, fetch_single_model, model_id, lat, lon, elevation)
        for model_id in BLEND_MODELS
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Collect successful forecasts
    forecasts: dict[str, dict] = {}
    model_run_times: list[datetime] = []
    errors: list[str] = []
    
    for model_id, forecast, error in results:
        if forecast is not None:
            # Convert to dict once, store for blending
            forecasts[model_id] = forecast.to_dict()
            if forecast.model_run_utc is not None:
                model_run_times.append(forecast.model_run_utc)
        else:
            errors.append(f"{model_id}: {error}")
    
    if not forecasts:
        raise HTTPException(
            status_code=502,
            detail=f"All models failed for blend: {'; '.join(errors)}",
        )
    
    # Create blend with current weights
    response = create_blend_forecast(forecasts, lat, lon, elevation, model_run_times, weights)
    
    # Cache the result
    set_cached_blend(cache_key, response)
    
    return response


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


def get_blend_description(weights: dict[str, float] | None = None) -> str:
    """Generate blend model description from weights."""
    if weights is None:
        weights = get_blend_weights()
    
    # Group models by weight
    weight_groups: dict[float, list[str]] = {}
    for model_id, weight in weights.items():
        if weight not in weight_groups:
            weight_groups[weight] = []
        weight_groups[weight].append(model_id.upper())
    
    # Sort by weight descending
    parts = []
    for weight in sorted(weight_groups.keys(), reverse=True):
        models = ", ".join(sorted(weight_groups[weight]))
        weight_str = f"{weight:g}x" if weight != int(weight) else f"{int(weight)}x"
        parts.append(f"{models} ({weight_str})")
    
    return f"Weighted multi-model blend: {'; '.join(parts)}"


@app.get("/api/models", response_model=list[ModelInfo])
async def get_models():
    """List all available forecast models."""
    models = list_available_models()
    
    # Start with the blend model
    result = [
        ModelInfo(
            model_id="blend",
            display_name="Blend",
            provider="ActuallyOpenSnow",
            max_forecast_days=7,
            resolution_degrees=0.25,
            description=get_blend_description(),
        )
    ]
    
    # Add individual models
    result.extend([
        ModelInfo(
            model_id=m.model_id,
            display_name=m.display_name,
            provider=m.provider,
            max_forecast_days=m.max_forecast_days,
            resolution_degrees=m.resolution_degrees,
            description=m.description,
        )
        for m in models
    ])
    
    return result


@app.get("/api/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Get details for a specific model."""
    if model_id == "blend":
        return ModelInfo(
            model_id="blend",
            display_name="Blend",
            provider="ActuallyOpenSnow",
            max_forecast_days=7,
            resolution_degrees=0.25,
            description=get_blend_description(),
        )
    
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


@app.get("/api/resorts/batch/forecast")
async def batch_resort_forecasts(
    slugs: str = Query(..., description="Comma-separated resort slugs"),
    model: str = Query("blend", description="Forecast model ID"),
    elevation: str = Query("summit", description="'base', 'summit', or meters"),
):
    """Fetch forecasts for multiple resorts in a single request."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    
    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        raise HTTPException(status_code=400, detail="At least one resort slug required")
    if len(slug_list) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 resorts per batch request")
    
    async def fetch_resort(slug: str) -> tuple[str, ForecastResponse | None, str | None]:
        resort = get_resort_by_slug(slug)
        if not resort:
            return slug, None, f"Resort '{slug}' not found"
        
        # Determine elevation
        elev_m: float | None = None
        if elevation == "summit":
            elev_m = resort.summit_elevation_m
        elif elevation == "base":
            elev_m = resort.base_elevation_m
        else:
            try:
                elev_m = float(elevation)
            except ValueError:
                elev_m = resort.summit_elevation_m
        
        try:
            if model == "blend":
                forecast = await fetch_blend_forecast(resort.lat, resort.lon, elev_m)
            else:
                raw_forecast = client.get_forecast(
                    lat=resort.lat,
                    lon=resort.lon,
                    model=model,
                    elevation=elev_m,
                )
                forecast = forecast_to_response(raw_forecast)
            return slug, forecast, None
        except Exception as e:
            return slug, None, str(e)
    
    # Fetch all resorts in parallel
    tasks = [fetch_resort(slug) for slug in slug_list]
    results = await asyncio.gather(*tasks)
    
    # Build response
    forecasts: dict[str, ForecastResponse] = {}
    errors: dict[str, str] = {}
    
    for slug, forecast, error in results:
        if forecast:
            forecasts[slug] = forecast
        elif error:
            errors[slug] = error
    
    return {
        "forecasts": forecasts,
        "errors": errors,
    }


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
    model: str = Query("blend", description="Forecast model ID (default: blend)"),
    elevation: Optional[float] = Query(None, description="Elevation override in meters"),
):
    """Get a weather forecast for coordinates."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    
    # Handle blend model
    if model == "blend":
        return await fetch_blend_forecast(lat, lon, elevation)
    
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
    model: str = Query("blend", description="Forecast model ID (default: blend)"),
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
    
    # Handle blend model
    if model == "blend":
        return await fetch_blend_forecast(resort.lat, resort.lon, elev_m)
    
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
    models: str = Query("blend,gfs,ifs,aifs", description="Comma-separated model IDs"),
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
            if model_id == "blend":
                forecasts["blend"] = await fetch_blend_forecast(lat, lon, elevation)
            else:
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
    models: str = Query("blend,gfs,ifs,aifs", description="Comma-separated model IDs"),
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


# ============================================================================
# Blend Configuration (read-only, configured via environment variables)
# ============================================================================


@app.get("/api/blend/config")
async def get_blend_config():
    """Get current blend model configuration.
    
    Weights are configured via environment variables:
      - BLEND_WEIGHT_GFS (default: 2.0)
      - BLEND_WEIGHT_IFS (default: 2.0)
      - BLEND_WEIGHT_AIFS (default: 2.0)
      - BLEND_WEIGHT_ICON (default: 1.0)
      - BLEND_WEIGHT_JMA (default: 1.0)
    
    Set a weight to 0 to exclude that model from the blend.
    """
    weights = get_blend_weights()
    return {
        "models": BLEND_MODELS,
        "weights": weights,
        "description": get_blend_description(weights),
        "total_weight": sum(weights.values()),
        "config_method": "environment_variables",
        "env_vars_checked": {
            f"BLEND_WEIGHT_{m.upper()}": os.environ.get(f"BLEND_WEIGHT_{m.upper()}", "not set")
            for m in BLEND_MODELS
        },
    }


@app.get("/api/blend/debug")
async def debug_blend(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    elevation: Optional[float] = Query(None, description="Elevation in meters"),
):
    """Debug endpoint to see individual model totals and blend calculation."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    if executor is None:
        raise HTTPException(status_code=503, detail="Thread pool not initialized")
    
    # Get current weights from environment
    weights = get_blend_weights()
    
    # Fetch all models in parallel
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(executor, fetch_single_model, model_id, lat, lon, elevation)
        for model_id in BLEND_MODELS
    ]
    results = await asyncio.gather(*tasks)
    
    # Calculate totals for each model
    model_totals = {}
    model_errors = {}
    
    for model_id, forecast, error in results:
        if forecast is not None:
            data = forecast.to_dict()
            snowfall = data["hourly_data"].get("snowfall", [])
            total_cm = sum(v for v in snowfall if v is not None)
            total_inches = total_cm / 2.54
            model_totals[model_id] = {
                "total_cm": round(total_cm, 2),
                "total_inches": round(total_inches, 2),
                "hours": len(snowfall),
                "weight": weights.get(model_id, 1.0),
            }
        else:
            model_errors[model_id] = error
    
    # Calculate expected blend total
    weighted_sum_cm = sum(
        info["total_cm"] * info["weight"] 
        for info in model_totals.values()
    )
    total_weight = sum(info["weight"] for info in model_totals.values())
    
    blend_total_cm = weighted_sum_cm / total_weight if total_weight > 0 else 0
    blend_total_inches = blend_total_cm / 2.54
    
    return {
        "location": {"lat": lat, "lon": lon, "elevation": elevation},
        "weights_config": weights,
        "env_vars": {
            f"BLEND_WEIGHT_{m.upper()}": os.environ.get(f"BLEND_WEIGHT_{m.upper()}", "not set")
            for m in BLEND_MODELS
        },
        "models": model_totals,
        "errors": model_errors,
        "blend_calculation": {
            "weighted_sum_cm": round(weighted_sum_cm, 2),
            "total_weight": total_weight,
            "blend_total_cm": round(blend_total_cm, 2),
            "blend_total_inches": round(blend_total_inches, 2),
        },
    }


# ============================================================================
# Cache Management
# ============================================================================


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all caches (admin endpoint)."""
    global blend_cache
    
    if client:
        client.clear_cache()
    
    blend_cache.clear()
    
    return {"status": "ok", "message": "All caches cleared"}


@app.get("/api/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    now = time.time()
    valid_entries = sum(1 for ts, _ in blend_cache.values() if now - ts < BLEND_CACHE_TTL)
    
    return {
        "blend_cache": {
            "total_entries": len(blend_cache),
            "valid_entries": valid_entries,
            "ttl_seconds": BLEND_CACHE_TTL,
        }
    }
