"""FastAPI application for ActuallyOpenSnow (read-only, DB-backed)."""

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sqlalchemy.orm import Session

# Add weather package and db package to path
weather_path = Path(__file__).parent.parent.parent / "weather" / "src"
db_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(weather_path))
sys.path.insert(0, str(db_path))

from weather.config.models import list_available_models, MODELS

from app.models import (
    ForecastResponse,
    ComparisonResponse,
    ModelInfo,
    ErrorResponse,
)
from app.resorts import RESORTS, get_resort_by_slug, Resort
from app.cache import cache_get, cache_set, cache_clear

from db.models import (
    Forecast as DBForecast,
    BlendForecast as DBBlendForecast,
)
from db.session import get_engine, get_session_factory


# ============================================================================
# Configuration
# ============================================================================

PRODUCTION_MODE = os.environ.get("ENVIRONMENT", "development").lower() == "production"
ENGINE_BACKEND_URL = os.environ.get("ENGINE_BACKEND_URL", "http://localhost:8001")

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Unique coordinates rate limiting (per IP)
UNIQUE_COORDS_WINDOW = 3600  # 1 hour window
UNIQUE_COORDS_LIMIT = 100    # Max 100 unique coordinate pairs per hour per IP
unique_coords_tracker: dict[str, dict[str, float]] = defaultdict(dict)

# Blend models and weights (for display/config endpoint only — actual blending is in engine)
DEFAULT_BLEND_WEIGHTS = {
    "hrrr": 3.0,
    "gfs": 2.0,
    "nbm": 2.0,
    "ifs": 2.0,
    "aifs": 2.0,
    "gefs": 1.0,
    "ecmwf_ens": 1.0,
}
BLEND_MODELS = list(DEFAULT_BLEND_WEIGHTS.keys())

# DB session factory (initialized on startup)
_session_factory = None


# ============================================================================
# Database dependency
# ============================================================================


def get_db() -> Session:
    """FastAPI dependency for database sessions."""
    if _session_factory is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# Application setup
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection on startup."""
    global _session_factory
    try:
        engine = get_engine()
        # Auto-create tables if they don't exist
        from db.models import Base
        Base.metadata.create_all(engine)
        _session_factory = get_session_factory(engine)
        print(f"[Startup] Production mode: {PRODUCTION_MODE}")
        print(f"[Startup] Debug endpoints: {'DISABLED' if PRODUCTION_MODE else 'ENABLED'}")
        print(f"[Startup] Database connected, tables ensured")
        print(f"[Startup] Engine-backend URL: {ENGINE_BACKEND_URL}")
    except Exception as e:
        print(f"[Startup] WARNING: Database connection failed: {e}")
        print(f"[Startup] API will return 503 for forecast endpoints")
    yield
    _session_factory = None


app = FastAPI(
    title="ActuallyOpenSnow API",
    description="Mountain weather forecasts for skiers and snowboarders",
    version="2.0.0",
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
    """Check if IP has exceeded unique coordinates limit."""
    ip = get_remote_address(request)
    coord_key = f"{lat:.4f}:{lon:.4f}"
    now = time.time()

    if ip in unique_coords_tracker:
        unique_coords_tracker[ip] = {
            k: v for k, v in unique_coords_tracker[ip].items()
            if now - v < UNIQUE_COORDS_WINDOW
        }

    if coord_key in unique_coords_tracker[ip]:
        unique_coords_tracker[ip][coord_key] = now
        return

    if len(unique_coords_tracker[ip]) >= UNIQUE_COORDS_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Unique coordinates limit exceeded: max {UNIQUE_COORDS_LIMIT} unique locations per hour",
        )

    unique_coords_tracker[ip][coord_key] = now


# ============================================================================
# Database query helpers
# ============================================================================


def db_forecast_to_response(row: DBForecast, resort: Resort) -> ForecastResponse:
    """Convert a DB Forecast row to ForecastResponse."""
    return ForecastResponse(
        lat=resort.lat,
        lon=resort.lon,
        api_lat=resort.lat,
        api_lon=resort.lon,
        elevation_m=resort.summit_elevation_m if row.elevation_type == "summit" else resort.base_elevation_m,
        model_id=row.model_id,
        model_run_utc=row.run_datetime.isoformat() if row.run_datetime else None,
        times_utc=row.times_utc,
        hourly_data=row.hourly_data,
        hourly_units=row.hourly_units,
        enhanced_hourly_data=row.enhanced_hourly_data,
        enhanced_hourly_units=row.enhanced_hourly_units,
        ensemble_ranges=row.ensemble_ranges,
    )


def db_blend_to_response(row: DBBlendForecast, resort: Resort) -> ForecastResponse:
    """Convert a DB BlendForecast row to ForecastResponse."""
    # Find the latest source model run time
    latest_run = None
    if row.source_model_runs:
        run_times = list(row.source_model_runs.values())
        if run_times:
            latest_run = max(run_times)

    return ForecastResponse(
        lat=resort.lat,
        lon=resort.lon,
        api_lat=resort.lat,
        api_lon=resort.lon,
        elevation_m=resort.summit_elevation_m if row.elevation_type == "summit" else resort.base_elevation_m,
        model_id="blend",
        model_run_utc=latest_run,
        times_utc=row.times_utc,
        hourly_data=row.hourly_data,
        hourly_units=row.hourly_units,
        enhanced_hourly_data=row.enhanced_hourly_data,
        enhanced_hourly_units=row.enhanced_hourly_units,
        ensemble_ranges=row.ensemble_ranges,
    )


def get_resort_forecast_from_db(
    db: Session,
    slug: str,
    model_id: str,
    elevation_type: str,
) -> DBForecast | DBBlendForecast | None:
    """Query the latest forecast for a resort from the database."""
    try:
        if model_id == "blend":
            return (
                db.query(DBBlendForecast)
                .filter_by(resort_slug=slug, elevation_type=elevation_type)
                .first()
            )

        return (
            db.query(DBForecast)
            .filter_by(resort_slug=slug, model_id=model_id, elevation_type=elevation_type)
            .order_by(DBForecast.run_datetime.desc())
            .first()
        )
    except Exception:
        # Table may not exist yet or DB error — treat as no data
        db.rollback()
        return None


def resolve_elevation(resort: Resort, elevation: str | None) -> tuple[float | None, str]:
    """Resolve elevation parameter to (elevation_m, elevation_type)."""
    if elevation is None or elevation == "summit":
        return resort.summit_elevation_m, "summit"
    elif elevation == "base":
        return resort.base_elevation_m, "base"
    else:
        try:
            elev_m = float(elevation)
            if elev_m < 0 or elev_m > 9000:
                raise HTTPException(
                    status_code=400,
                    detail="Elevation must be between 0 and 9000 meters",
                )
            # Custom elevations use summit type for DB lookup
            return elev_m, "summit"
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Elevation must be 'base', 'summit', or a number in meters (0-9000)",
            )


def proxy_to_engine_backend(lat: float, lon: float, model: str, elevation: float | None) -> ForecastResponse | None:
    """Proxy a forecast request to engine-backend for on-demand extraction."""
    try:
        import httpx
        resp = httpx.post(
            f"{ENGINE_BACKEND_URL}/api/engine/extract",
            json={"lat": lat, "lon": lon, "model": model, "elevation": elevation},
            timeout=30.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return ForecastResponse(**data)
    except Exception:
        pass
    return None


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


def get_blend_description() -> str:
    """Generate blend model description from weights."""
    weight_groups: dict[float, list[str]] = {}
    for model_id, weight in DEFAULT_BLEND_WEIGHTS.items():
        if weight not in weight_groups:
            weight_groups[weight] = []
        weight_groups[weight].append(model_id.upper())

    parts = []
    for weight in sorted(weight_groups.keys(), reverse=True):
        models_list = ", ".join(sorted(weight_groups[weight]))
        weight_str = f"{weight:g}x" if weight != int(weight) else f"{int(weight)}x"
        parts.append(f"{models_list} ({weight_str})")

    return f"Weighted multi-model blend: {'; '.join(parts)}"


@app.get("/api/models", response_model=list[ModelInfo])
@limiter.limit("120/minute")
async def get_models(request: Request):
    """List all available forecast models."""
    models = list_available_models()

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
    db: Session = Depends(get_db),
):
    """Fetch forecasts for multiple resorts in a single request."""
    slug_list = [s.strip() for s in slugs.split(",") if s.strip()]
    if not slug_list:
        raise HTTPException(status_code=400, detail="At least one resort slug required")
    if len(slug_list) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 resorts per batch request")

    forecasts: dict[str, ForecastResponse] = {}
    errors: dict[str, str] = {}

    for slug in slug_list:
        resort = get_resort_by_slug(slug)
        if not resort:
            errors[slug] = f"Resort '{slug}' not found"
            continue

        elev_m, elev_type = resolve_elevation(resort, elevation)

        # Check Redis cache
        cache_key = f"forecast:{slug}:{model}:{elev_type}"
        cached = cache_get(cache_key)
        if cached:
            forecasts[slug] = ForecastResponse(**cached)
            continue

        row = get_resort_forecast_from_db(db, slug, model, elev_type)
        if row is None:
            errors[slug] = f"No forecast data available for model '{model}'"
            continue

        if model == "blend":
            resp = db_blend_to_response(row, resort)
        else:
            resp = db_forecast_to_response(row, resort)

        cache_set(cache_key, resp.model_dump())
        forecasts[slug] = resp

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
    db: Session = Depends(get_db),
):
    """Get a weather forecast for coordinates.

    For known resort coordinates, reads from the database.
    For custom coordinates, proxies to engine-backend for on-demand extraction.
    """
    check_unique_coords_limit(request, lat, lon)

    # Try to find a matching resort
    matching_resort = None
    for r in RESORTS:
        if abs(r.lat - lat) < 0.01 and abs(r.lon - lon) < 0.01:
            matching_resort = r
            break

    if matching_resort:
        elev_type = "summit"
        if elevation is not None and matching_resort.base_elevation_m and abs(elevation - matching_resort.base_elevation_m) < 1:
            elev_type = "base"

        cache_key = f"forecast:{matching_resort.slug}:{model}:{elev_type}"
        cached = cache_get(cache_key)
        if cached:
            return ForecastResponse(**cached)

        row = get_resort_forecast_from_db(db, matching_resort.slug, model, elev_type)
        if row:
            if model == "blend":
                resp = db_blend_to_response(row, matching_resort)
            else:
                resp = db_forecast_to_response(row, matching_resort)
            cache_set(cache_key, resp.model_dump())
            return resp

    # Custom coordinates — proxy to engine-backend
    result = proxy_to_engine_backend(lat, lon, model, elevation)
    if result:
        return result

    raise HTTPException(
        status_code=404,
        detail="No forecast data available. The engine may not have processed this location yet.",
    )


@app.get("/api/resorts/{slug}/forecast", response_model=ForecastResponse)
@limiter.limit("120/minute")
async def get_resort_forecast(
    request: Request,
    slug: str,
    model: str = Query("blend", description="Forecast model ID (default: blend)"),
    elevation: Optional[str] = Query("summit", description="'base', 'summit', or meters (0-9000)"),
    db: Session = Depends(get_db),
):
    """Get forecast for a resort."""
    resort = get_resort_by_slug(slug)
    if not resort:
        raise HTTPException(status_code=404, detail=f"Resort '{slug}' not found")

    elev_m, elev_type = resolve_elevation(resort, elevation)

    # Check Redis cache
    cache_key = f"forecast:{slug}:{model}:{elev_type}"
    cached = cache_get(cache_key)
    if cached:
        return ForecastResponse(**cached)

    # Query database
    row = get_resort_forecast_from_db(db, slug, model, elev_type)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast data available for '{slug}' with model '{model}'. Engine may not have processed it yet.",
        )

    if model == "blend":
        resp = db_blend_to_response(row, resort)
    else:
        resp = db_forecast_to_response(row, resort)

    cache_set(cache_key, resp.model_dump())
    return resp


@app.get("/api/compare", response_model=ComparisonResponse)
@limiter.limit("10/minute")
async def compare_models(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    models: str = Query("blend,gfs,ifs,aifs", description="Comma-separated model IDs"),
    elevation: Optional[float] = Query(None, ge=0, le=9000, description="Elevation override in meters (0-9000)"),
    db: Session = Depends(get_db),
):
    """Compare forecasts from multiple models."""
    check_unique_coords_limit(request, lat, lon)

    model_ids = [m.strip() for m in models.split(",") if m.strip()]
    if not model_ids:
        raise HTTPException(status_code=400, detail="At least one model required")

    # Try to find a matching resort
    matching_resort = None
    for r in RESORTS:
        if abs(r.lat - lat) < 0.01 and abs(r.lon - lon) < 0.01:
            matching_resort = r
            break

    forecasts: dict[str, ForecastResponse] = {}
    errors: list[str] = []

    if matching_resort:
        elev_type = "summit"
        if elevation is not None and matching_resort.base_elevation_m and abs(elevation - matching_resort.base_elevation_m) < 1:
            elev_type = "base"

        for mid in model_ids:
            row = get_resort_forecast_from_db(db, matching_resort.slug, mid, elev_type)
            if row:
                if mid == "blend":
                    forecasts[mid] = db_blend_to_response(row, matching_resort)
                else:
                    forecasts[mid] = db_forecast_to_response(row, matching_resort)
            else:
                errors.append(f"{mid}: no data available")
    else:
        # Custom coordinates — try engine-backend for each model
        for mid in model_ids:
            result = proxy_to_engine_backend(lat, lon, mid, elevation)
            if result:
                forecasts[mid] = result
            else:
                errors.append(f"{mid}: extraction failed")

    if not forecasts:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast data available: {'; '.join(errors)}",
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
    db: Session = Depends(get_db),
):
    """Compare forecasts from multiple models for a resort."""
    resort = get_resort_by_slug(slug)
    if not resort:
        raise HTTPException(status_code=404, detail=f"Resort '{slug}' not found")

    elev_m, elev_type = resolve_elevation(resort, elevation)

    model_ids = [m.strip() for m in models.split(",") if m.strip()]
    if not model_ids:
        raise HTTPException(status_code=400, detail="At least one model required")

    forecasts: dict[str, ForecastResponse] = {}
    errors: list[str] = []

    for mid in model_ids:
        row = get_resort_forecast_from_db(db, slug, mid, elev_type)
        if row:
            if mid == "blend":
                forecasts[mid] = db_blend_to_response(row, resort)
            else:
                forecasts[mid] = db_forecast_to_response(row, resort)
        else:
            errors.append(f"{mid}: no data available")

    if not forecasts:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast data available: {'; '.join(errors)}",
        )

    return ComparisonResponse(
        lat=resort.lat,
        lon=resort.lon,
        elevation_m=elev_m,
        forecasts=forecasts,
    )


# ============================================================================
# Blend Configuration (read-only display)
# ============================================================================


@app.get("/api/blend/config")
@limiter.limit("60/minute")
async def get_blend_config(request: Request):
    """Get current blend model configuration."""
    return {
        "models": BLEND_MODELS,
        "weights": DEFAULT_BLEND_WEIGHTS,
        "description": get_blend_description(),
        "total_weight": sum(DEFAULT_BLEND_WEIGHTS.values()),
        "config_method": "engine_precomputed",
    }


@app.get("/api/blend/debug")
async def debug_blend(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    elevation: Optional[float] = Query(None, ge=0, le=9000, description="Elevation in meters (0-9000)"),
    db: Session = Depends(get_db),
):
    """Debug endpoint to see individual model data. Disabled in production."""
    if PRODUCTION_MODE:
        raise HTTPException(status_code=404, detail="Not found")

    # Find matching resort
    matching_resort = None
    for r in RESORTS:
        if abs(r.lat - lat) < 0.01 and abs(r.lon - lon) < 0.01:
            matching_resort = r
            break

    if not matching_resort:
        return {"error": "No matching resort found for these coordinates"}

    elev_type = "summit"
    model_totals = {}
    model_errors = {}

    for model_id in BLEND_MODELS:
        row = get_resort_forecast_from_db(db, matching_resort.slug, model_id, elev_type)
        if row:
            snowfall = row.hourly_data.get("snowfall", [])
            total_cm = sum(v for v in snowfall if v is not None)
            total_inches = total_cm / 2.54
            model_totals[model_id] = {
                "total_cm": round(total_cm, 2),
                "total_inches": round(total_inches, 2),
                "hours": len(snowfall),
                "weight": DEFAULT_BLEND_WEIGHTS.get(model_id, 1.0),
            }
        else:
            model_errors[model_id] = "No data in database"

    weighted_sum_cm = sum(
        info["total_cm"] * info["weight"]
        for info in model_totals.values()
    )
    total_weight = sum(info["weight"] for info in model_totals.values())

    blend_total_cm = weighted_sum_cm / total_weight if total_weight > 0 else 0
    blend_total_inches = blend_total_cm / 2.54

    return {
        "location": {"lat": lat, "lon": lon, "elevation": elevation, "resort": matching_resort.slug},
        "weights_config": DEFAULT_BLEND_WEIGHTS,
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
    if PRODUCTION_MODE:
        raise HTTPException(status_code=404, detail="Not found")

    cleared = cache_clear()
    return {"status": "ok", "message": f"Cleared {cleared} cache entries"}


@app.get("/api/cache/stats")
@limiter.limit("60/minute")
async def cache_stats(request: Request):
    """Get cache statistics."""
    from app.cache import get_redis, CACHE_PREFIX

    client = get_redis()
    total_entries = 0
    if client:
        try:
            total_entries = sum(1 for _ in client.scan_iter(f"{CACHE_PREFIX}*"))
        except Exception:
            pass

    return {
        "redis_cache": {
            "total_entries": total_entries,
            "backend": "redis" if client else "disabled",
        }
    }
