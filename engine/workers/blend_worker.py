"""Worker for computing blended forecasts."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import JobHistory, Resort as DBResort
from engine.config import BLEND_WEIGHTS
from engine.services.blend_service import compute_blend, compute_ensemble_ranges
from engine.services.forecast_service import (
    get_latest_forecast,
    upsert_blend_forecast,
)

logger = logging.getLogger(__name__)

# Models included in the blend
BLEND_MODEL_IDS = list(BLEND_WEIGHTS.keys())

# Ensemble models for confidence ranges
ENSEMBLE_MODEL_IDS = ["gefs", "ecmwf_ens"]


def compute_resort_blend(
    session: Session,
    resort_slug: str,
    elevation_type: str = "summit",
) -> bool:
    """Compute and store blend forecast for a single resort.

    Args:
        session: DB session.
        resort_slug: Resort slug.
        elevation_type: "summit" or "base".

    Returns:
        True if blend was computed successfully.
    """
    # Gather latest forecast from each model
    forecasts: dict[str, dict] = {}
    source_runs: dict[str, str] = {}

    for model_id in BLEND_MODEL_IDS:
        forecast = get_latest_forecast(session, resort_slug, model_id, elevation_type)
        if forecast is not None:
            forecasts[model_id] = {
                "times_utc": forecast.times_utc,
                "hourly_data": forecast.hourly_data,
                "hourly_units": forecast.hourly_units,
                "enhanced_hourly_data": forecast.enhanced_hourly_data,
                "enhanced_hourly_units": forecast.enhanced_hourly_units,
            }
            source_runs[model_id] = forecast.run_datetime.isoformat()

    if not forecasts:
        logger.warning(f"No forecasts available for {resort_slug} blend")
        return False

    # Compute blend
    blend_data = compute_blend(forecasts, BLEND_WEIGHTS)

    # Compute ensemble ranges from ensemble models
    ensemble_forecasts = {
        mid: forecasts[mid] for mid in ENSEMBLE_MODEL_IDS if mid in forecasts
    }
    if ensemble_forecasts:
        ranges = compute_ensemble_ranges(ensemble_forecasts)
        blend_data["ensemble_ranges"] = ranges

    # Store in DB
    upsert_blend_forecast(
        session, resort_slug, elevation_type,
        blend_data, BLEND_WEIGHTS, source_runs,
    )

    return True


def compute_all_blends(session: Session) -> int:
    """Compute blend forecasts for all resorts, both elevations.

    Args:
        session: DB session.

    Returns:
        Number of blends computed.
    """
    start_time = time.time()

    # Record job
    job = JobHistory(
        job_type="blend",
        status="started",
        started_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.commit()

    resorts = session.query(DBResort).all()
    count = 0
    errors = 0

    for resort in resorts:
        for elev_type in ["summit", "base"]:
            try:
                if compute_resort_blend(session, resort.slug, elev_type):
                    count += 1
            except Exception as e:
                logger.error(f"Blend failed for {resort.slug}/{elev_type}: {e}")
                errors += 1

    session.commit()

    duration = time.time() - start_time
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    job.duration_seconds = duration
    job.resorts_processed = count
    if errors:
        job.error = f"{errors} blends failed"
    session.commit()

    logger.info(f"Computed {count} blends in {duration:.1f}s ({errors} errors)")
    return count
