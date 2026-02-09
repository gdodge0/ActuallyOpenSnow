"""Job management and engine status API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from db.models import ModelRun, JobHistory, BlendForecast

router = APIRouter()


def get_db(request: Request) -> Session:
    """Get a database session from the app state."""
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


@router.get("/status")
async def engine_status(session: Session = Depends(get_db)):
    """Engine health and latest model run times."""
    latest_runs = {}
    models = session.query(ModelRun.model_id).distinct().all()

    for (model_id,) in models:
        latest = (
            session.query(ModelRun)
            .filter_by(model_id=model_id, status="completed")
            .order_by(ModelRun.run_datetime.desc())
            .first()
        )
        if latest:
            latest_runs[model_id] = {
                "run_datetime": latest.run_datetime.isoformat(),
                "completed_at": latest.completed_at.isoformat() if latest.completed_at else None,
                "resorts_processed": latest.resorts_processed,
            }

    return {
        "status": "running",
        "latest_model_runs": latest_runs,
        "models_tracked": len(latest_runs),
    }


@router.get("/models")
async def list_models(session: Session = Depends(get_db)):
    """All models with last run status."""
    from weather.config.models import MODELS

    result = []
    for model_id, config in MODELS.items():
        if not config.herbie_model:
            continue

        latest = (
            session.query(ModelRun)
            .filter_by(model_id=model_id)
            .order_by(ModelRun.created_at.desc())
            .first()
        )

        result.append({
            "model_id": model_id,
            "display_name": config.display_name,
            "provider": config.provider,
            "update_interval_hours": config.update_interval_hours,
            "is_ensemble": config.is_ensemble,
            "last_run": {
                "run_datetime": latest.run_datetime.isoformat() if latest else None,
                "status": latest.status if latest else "never_run",
                "error": latest.error if latest else None,
            },
        })

    return result


@router.post("/models/{model_id}/run")
async def trigger_model_run(model_id: str, session: Session = Depends(get_db)):
    """Trigger an immediate model run."""
    from weather.config.models import get_model_config
    from weather.clients.herbie_client import HerbieClient
    from engine.workers.model_worker import process_model_run
    from engine.config import GRIB_CACHE_DIR

    try:
        config = get_model_config(model_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    if not config.herbie_model:
        raise HTTPException(status_code=400, detail=f"Model '{model_id}' does not support GRIB2")

    client = HerbieClient(cache_dir=GRIB_CACHE_DIR)
    run_dt = client._get_latest_run_dt(config)

    try:
        resorts_processed = process_model_run(session, client, model_id, run_dt)
        return {
            "status": "completed",
            "model_id": model_id,
            "run_datetime": run_dt.isoformat(),
            "resorts_processed": resorts_processed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    job_type: Optional[str] = Query(None),
    session: Session = Depends(get_db),
):
    """Job history (paginated)."""
    query = session.query(JobHistory).order_by(JobHistory.created_at.desc())

    if job_type:
        query = query.filter_by(job_type=job_type)

    total = query.count()
    jobs = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "jobs": [
            {
                "id": j.id,
                "job_type": j.job_type,
                "model_id": j.model_id,
                "status": j.status,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "duration_seconds": j.duration_seconds,
                "resorts_processed": j.resorts_processed,
                "error": j.error,
            }
            for j in jobs
        ],
    }


@router.get("/resorts/{slug}/status")
async def resort_forecast_status(slug: str, session: Session = Depends(get_db)):
    """Forecast freshness for a resort."""
    from db.models import Forecast as DBForecast

    forecasts = (
        session.query(DBForecast)
        .filter_by(resort_slug=slug)
        .order_by(DBForecast.created_at.desc())
        .all()
    )

    blend = (
        session.query(BlendForecast)
        .filter_by(resort_slug=slug)
        .first()
    )

    model_status = {}
    for f in forecasts:
        key = f"{f.model_id}_{f.elevation_type}"
        if key not in model_status:
            model_status[key] = {
                "model_id": f.model_id,
                "elevation_type": f.elevation_type,
                "run_datetime": f.run_datetime.isoformat(),
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "hours": len(f.times_utc) if f.times_utc else 0,
            }

    return {
        "resort_slug": slug,
        "model_forecasts": model_status,
        "blend_available": blend is not None,
        "blend_updated_at": blend.updated_at.isoformat() if blend and blend.updated_at else None,
    }


@router.get("/metrics")
async def engine_metrics(session: Session = Depends(get_db)):
    """Processing stats, error rates, cache size."""
    from engine.services.grib_service import get_cache_size_bytes

    # Job stats from last 24 hours
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    total_jobs = session.query(JobHistory).filter(JobHistory.started_at >= cutoff).count()
    failed_jobs = (
        session.query(JobHistory)
        .filter(JobHistory.started_at >= cutoff, JobHistory.status == "failed")
        .count()
    )
    completed_jobs = (
        session.query(JobHistory)
        .filter(JobHistory.started_at >= cutoff, JobHistory.status == "completed")
        .count()
    )

    # Cache size
    try:
        cache_bytes = get_cache_size_bytes()
    except Exception:
        cache_bytes = 0

    return {
        "last_24h": {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "error_rate": failed_jobs / total_jobs if total_jobs > 0 else 0.0,
        },
        "cache_size_mb": round(cache_bytes / (1024 * 1024), 2),
        "total_model_runs": session.query(ModelRun).count(),
        "total_blend_forecasts": session.query(BlendForecast).count(),
    }
