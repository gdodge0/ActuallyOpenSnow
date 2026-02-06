"""FastAPI application for ActuallyOpenSnow."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# ============================================================================
# Production Mode & Rate Limiting Configuration
# ============================================================================

# Production mode - set ENVIRONMENT=production to disable debug endpoints
PRODUCTION_MODE = os.environ.get("ENVIRONMENT", "development").lower() == "production"

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Unique coordinates rate limiting (per IP)
# Tracks unique coordinate pairs requested per IP in a time window
UNIQUE_COORDS_WINDOW = 3600  # 1 hour window
UNIQUE_COORDS_LIMIT = 100    # Max 100 unique coordinate pairs per hour per IP
unique_coords_tracker: dict[str, dict[str, float]] = defaultdict(dict)  # IP -> {coord_key: timestamp}

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
ASYNC_GATHER_TIMEOUT = 120  # seconds — max wait for parallel model fetches


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the MeteoClient on startup."""
    global client, executor, blend_cache
    client = MeteoClient(cache_expire_after=1800)  # 30 min cache
    executor = ThreadPoolExecutor(max_workers=20)  # Parallel API calls (5 per blend × 4 concurrent)
    # Clear blend cache on startup (ensures fresh data after weight changes)
    blend_cache.clear()
    weights = get_blend_weights()
    print(f"[Startup] Production mode: {PRODUCTION_MODE}")
    print(f"[Startup] Debug endpoints: {'DISABLED' if PRODUCTION_MODE else 'ENABLED'}")
    print(f"[Startup] Blend weights: {weights}")
    print(f"[Startup] Total weight: {sum(weights.values())}")
    yield
    # Cleanup
    if client:
        client.clear_cache()
    if executor:
        executor.shutdown(wait=True, cancel_futures=True)


app = FastAPI(
    title="ActuallyOpenSnow API",
    description="Mountain weather forecasts for skiers and snowboarders",
    version="1.0.0",
    lifespan=lifespan,
)

# Register rate limiter
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "error_type": "rate_limit_exceeded",
            "message": "You've made too many requests. Please wait a moment before trying again.",
            "limit": str(exc.detail),
        },
    )


# CORS - allow all origins in production (nginx handles security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Unique Coordinates Rate Limiting
# ============================================================================


def check_unique_coords_limit(request: Request, lat: float, lon: float) -> None:
    """Check if IP has exceeded unique coordinates limit.
    
    Raises HTTPException 429 if limit exceeded.
    """
    ip = get_remote_address(request)
    coord_key = f"{lat:.4f}:{lon:.4f}"
    now = time.time()
    
    # Clean up old entries for this IP
    if ip in unique_coords_tracker:
        unique_coords_tracker[ip] = {
            k: v for k, v in unique_coords_tracker[ip].items()
            if now - v < UNIQUE_COORDS_WINDOW
        }
    
    # Check if this coordinate was already requested (doesn't count against limit)
    if coord_key in unique_coords_tracker[ip]:
        unique_coords_tracker[ip][coord_key] = now  # Update timestamp
        return
    
    # Check if limit exceeded
    if len(unique_coords_tracker[ip]) >= UNIQUE_COORDS_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Unique coordinates limit exceeded: max {UNIQUE_COORDS_LIMIT} unique locations per hour",
        )
    
    # Record this new coordinate
    unique_coords_tracker[ip][coord_key] = now


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
    data = forecast.to_dict(include_enhanced=True)
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
        enhanced_hourly_data=data.get("enhanced_hourly_data"),
        enhanced_hourly_units=data.get("enhanced_hourly_units"),
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
    
    # Also blend enhanced hourly data if available
    blended_enhanced_data: dict[str, list[float]] = {}
    enhanced_vars = ["enhanced_snowfall", "rain"]
    
    for var in enhanced_vars:
        blended_values_enhanced: list[float] = []
        
        for hour_idx in range(min_hours):
            weighted_sum = 0.0
            total_weight = 0.0
            
            for model_id, forecast_data in forecasts.items():
                enhanced_data = forecast_data.get("enhanced_hourly_data", {})
                if var in enhanced_data and hour_idx < len(enhanced_data[var]):
                    val = enhanced_data[var][hour_idx]
                    if val is not None:
                        weight = model_weights.get(model_id, 1.0)
                        weighted_sum += val * weight
                        total_weight += weight
            
            if total_weight > 0:
                blended_values_enhanced.append(weighted_sum / total_weight)
            else:
                blended_values_enhanced.append(0.0)
        
        blended_enhanced_data[var] = blended_values_enhanced
    
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
        enhanced_hourly_data=blended_enhanced_data,
        enhanced_hourly_units=first_data.get("enhanced_hourly_units", {"enhanced_snowfall": "cm", "rain": "mm"}),
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
    
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=ASYNC_GATHER_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Blend forecast timed out — upstream models took too long")

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
@limiter.limit("120/minute")
async def get_models(request: Request):
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
@limiter.limit("120/minute")
async def get_model(request: Request, model_id: str):
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
@limiter.limit("120/minute")
async def get_resorts(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by state/province code"),
):
    """List all ski resorts."""
    if state:
        return [r for r in RESORTS if r.state.upper() == state.upper()]
    return RESORTS


@app.get("/api/resorts/batch/forecast")
@limiter.limit("30/minute")
async def batch_resort_forecasts(
    request: Request,
    slugs: str = Query(..., description="Comma-separated resort slugs"),
    model: str = Query("blend", description="Forecast model ID"),
    elevation: str = Query("summit", description="'base', 'summit', or meters (0-9000)"),
):
    """Fetch forecasts for multiple resorts in a single request."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    if executor is None:
        raise HTTPException(status_code=503, detail="Thread pool not initialized")

    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        raise HTTPException(status_code=400, detail="At least one resort slug required")
    if len(slug_list) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 resorts per batch request")

    loop = asyncio.get_event_loop()

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
                # Validate elevation range
                if elev_m < 0 or elev_m > 9000:
                    return slug, None, "Elevation must be between 0 and 9000 meters"
            except ValueError:
                elev_m = resort.summit_elevation_m

        try:
            if model == "blend":
                forecast = await fetch_blend_forecast(resort.lat, resort.lon, elev_m)
            else:
                _, raw_forecast, error = await loop.run_in_executor(
                    executor, fetch_single_model, model, resort.lat, resort.lon, elev_m,
                )
                if raw_forecast is None:
                    return slug, None, error or "Unknown error"
                forecast = forecast_to_response(raw_forecast)
            return slug, forecast, None
        except Exception as e:
            return slug, None, str(e)
    
    # Fetch all resorts in parallel
    tasks = [fetch_resort(slug) for slug in slug_list]
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=ASYNC_GATHER_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Batch forecast timed out — upstream models took too long")

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
@limiter.limit("120/minute")
async def get_resort(request: Request, slug: str):
    """Get a resort by slug."""
    resort = get_resort_by_slug(slug)
    if not resort:
        raise HTTPException(status_code=404, detail=f"Resort '{slug}' not found")
    return resort


# ============================================================================
# Forecasts
# ============================================================================


@app.get("/api/forecast", response_model=ForecastResponse)
@limiter.limit("10/minute")
async def get_forecast(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    model: str = Query("blend", description="Forecast model ID (default: blend)"),
    elevation: Optional[float] = Query(None, ge=0, le=9000, description="Elevation override in meters (0-9000)"),
):
    """Get a weather forecast for coordinates."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    
    # Check unique coordinates rate limit
    check_unique_coords_limit(request, lat, lon)
    
    # Handle blend model
    if model == "blend":
        return await fetch_blend_forecast(lat, lon, elevation)
    
    if executor is None:
        raise HTTPException(status_code=503, detail="Thread pool not initialized")

    try:
        loop = asyncio.get_event_loop()
        model_id, forecast, error = await loop.run_in_executor(
            executor, fetch_single_model, model, lat, lon, elevation,
        )
        if forecast is None:
            raise ApiError(error or "Unknown error")
        return forecast_to_response(forecast)
    except ModelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/api/resorts/{slug}/forecast", response_model=ForecastResponse)
@limiter.limit("120/minute")
async def get_resort_forecast(
    request: Request,
    slug: str,
    model: str = Query("blend", description="Forecast model ID (default: blend)"),
    elevation: Optional[str] = Query("summit", description="'base', 'summit', or meters (0-9000)"),
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
            # Validate elevation range
            if elev_m < 0 or elev_m > 9000:
                raise HTTPException(
                    status_code=400,
                    detail="Elevation must be between 0 and 9000 meters",
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Elevation must be 'base', 'summit', or a number in meters (0-9000)",
            )
    
    # Handle blend model
    if model == "blend":
        return await fetch_blend_forecast(resort.lat, resort.lon, elev_m)

    if executor is None:
        raise HTTPException(status_code=503, detail="Thread pool not initialized")

    try:
        loop = asyncio.get_event_loop()
        model_id, forecast, error = await loop.run_in_executor(
            executor, fetch_single_model, model, resort.lat, resort.lon, elev_m,
        )
        if forecast is None:
            raise ApiError(error or "Unknown error")
        return forecast_to_response(forecast)
    except ModelError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/api/compare", response_model=ComparisonResponse)
@limiter.limit("10/minute")
async def compare_models(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    models: str = Query("blend,gfs,ifs,aifs", description="Comma-separated model IDs"),
    elevation: Optional[float] = Query(None, ge=0, le=9000, description="Elevation override in meters (0-9000)"),
):
    """Compare forecasts from multiple models."""
    if client is None:
        raise HTTPException(status_code=503, detail="Weather client not initialized")
    if executor is None:
        raise HTTPException(status_code=503, detail="Thread pool not initialized")

    # Check unique coordinates rate limit
    check_unique_coords_limit(request, lat, lon)

    model_ids = [m.strip() for m in models.split(",") if m.strip()]
    if not model_ids:
        raise HTTPException(status_code=400, detail="At least one model required")

    # Fetch all models in parallel
    loop = asyncio.get_event_loop()

    async def fetch_compare_model(mid: str) -> tuple[str, ForecastResponse | None, str | None]:
        try:
            if mid == "blend":
                resp = await fetch_blend_forecast(lat, lon, elevation)
                return mid, resp, None
            else:
                _, forecast, error = await loop.run_in_executor(
                    executor, fetch_single_model, mid, lat, lon, elevation,
                )
                if forecast is None:
                    return mid, None, error
                return mid, forecast_to_response(forecast), None
        except (ModelError, ApiError) as e:
            return mid, None, str(e)

    compare_tasks = [fetch_compare_model(mid) for mid in model_ids]
    try:
        compare_results = await asyncio.wait_for(asyncio.gather(*compare_tasks), timeout=ASYNC_GATHER_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Model comparison timed out — upstream models took too long")

    forecasts: dict[str, ForecastResponse] = {}
    errors: list[str] = []

    for mid, resp, error in compare_results:
        if resp is not None:
            forecasts[mid] = resp
        elif error:
            errors.append(f"{mid}: {error}")

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
@limiter.limit("60/minute")
async def compare_resort_models(
    request: Request,
    slug: str,
    models: str = Query("blend,gfs,ifs,aifs", description="Comma-separated model IDs"),
    elevation: Optional[str] = Query("summit", description="'base', 'summit', or meters (0-9000)"),
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
            # Validate elevation range
            if elev_m < 0 or elev_m > 9000:
                raise HTTPException(
                    status_code=400,
                    detail="Elevation must be between 0 and 9000 meters",
                )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Elevation must be 'base', 'summit', or a number in meters (0-9000)",
            )
    
    return await compare_models(
        request=request,
        lat=resort.lat,
        lon=resort.lon,
        models=models,
        elevation=elev_m,
    )


# ============================================================================
# Blend Configuration (read-only, configured via environment variables)
# ============================================================================


@app.get("/api/blend/config")
@limiter.limit("60/minute")
async def get_blend_config(request: Request):
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
    elevation: Optional[float] = Query(None, ge=0, le=9000, description="Elevation in meters (0-9000)"),
):
    """Debug endpoint to see individual model totals and blend calculation. Disabled in production."""
    # Disabled in production for security
    if PRODUCTION_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    
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
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=ASYNC_GATHER_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Debug blend timed out — upstream models took too long")

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
    """Clear all caches (admin endpoint). Disabled in production."""
    # Disabled in production for security
    if PRODUCTION_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    
    global blend_cache
    
    if client:
        client.clear_cache()
    
    blend_cache.clear()
    
    return {"status": "ok", "message": "All caches cleared"}


@app.get("/api/cache/stats")
@limiter.limit("60/minute")
async def cache_stats(request: Request):
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
