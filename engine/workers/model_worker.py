"""Worker for processing a single model run."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from sqlalchemy import func

from db.models import ModelRun, JobHistory, Resort as DBResort
from engine.config import MAX_CONCURRENT_DOWNLOADS
from engine.services.forecast_service import upsert_forecast, get_or_create_model_run
from weather.clients.herbie_client import HerbieClient
from weather.config.models import get_fxx_range, get_model_config

logger = logging.getLogger(__name__)

STALE_LOCK_FALLBACK = 2500  # seconds — fallback when no history exists


def get_stale_timeout(session: Session, model_id: str) -> float:
    """Return stale lock timeout based on historical run durations.

    Uses 2x the average completed duration for this model.
    Falls back to STALE_LOCK_FALLBACK (2500s) if no history.
    """
    avg_duration = session.query(func.avg(JobHistory.duration_seconds)).filter(
        JobHistory.model_id == model_id,
        JobHistory.status == "completed",
        JobHistory.job_type == "model_run",
    ).scalar()

    if avg_duration and avg_duration > 0:
        return max(avg_duration * 2, STALE_LOCK_FALLBACK)
    return STALE_LOCK_FALLBACK


def process_model_run(
    session: Session,
    herbie_client: HerbieClient,
    model_id: str,
    run_dt: datetime,
) -> int:
    """Download GRIB2 data and extract forecasts for all resorts.

    Args:
        session: DB session.
        herbie_client: HerbieClient instance.
        model_id: Model to process.
        run_dt: Model run datetime.

    Returns:
        Number of resorts processed.
    """
    config = get_model_config(model_id)
    start_time = time.time()

    # Get or create model run record
    model_run, created = get_or_create_model_run(session, model_id, run_dt)

    if model_run.status == "completed":
        logger.info(f"Model run {model_id} {run_dt} already completed, skipping")
        return 0

    if model_run.status == "processing":
        # Check for stale lock — if started_at exceeds history-based timeout, reset it
        if model_run.started_at:
            elapsed = (datetime.now(timezone.utc) - model_run.started_at.replace(tzinfo=timezone.utc)).total_seconds()
            stale_timeout = get_stale_timeout(session, model_id)
            if elapsed > stale_timeout:
                logger.warning(
                    f"Model run {model_id} {run_dt} stuck in processing for {elapsed:.0f}s, resetting"
                )
                model_run.status = "failed"
                model_run.error = f"Stale lock reset after {elapsed:.0f}s"
                session.commit()
                # Fall through to re-process below
            else:
                logger.info(f"Model run {model_id} {run_dt} already processing ({elapsed:.0f}s ago), skipping")
                return 0
        else:
            # No started_at recorded — treat as stale
            logger.warning(f"Model run {model_id} {run_dt} stuck in processing (no started_at), resetting")
            model_run.status = "failed"
            model_run.error = "Stale lock reset (no started_at)"
            session.commit()

    # Mark as processing
    model_run.status = "processing"
    model_run.started_at = datetime.now(timezone.utc)
    session.commit()

    # Record job start
    job = JobHistory(
        job_type="model_run",
        model_id=model_id,
        status="started",
        started_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.commit()

    try:
        # Get all resorts from DB
        resorts = session.query(DBResort).all()
        if not resorts:
            raise ValueError("No resorts found in database")

        resorts_processed = 0

        # Build points list for batch extraction
        points = [(r.lat, r.lon) for r in resorts]

        # Batch-extract all forecast hours in parallel using FastHerbie
        all_resort_data: dict[str, list[dict]] = {r.slug: [] for r in resorts}
        times_utc: list[str] = []

        fxx_range = get_fxx_range(config)
        available_fxx, all_fxx_results = herbie_client.extract_all_hours_batch(
            model_id, run_dt, fxx_range, points,
            max_concurrent=MAX_CONCURRENT_DOWNLOADS,
        )

        for fxx in available_fxx:
            valid_time = run_dt + timedelta(hours=fxx)
            if valid_time.tzinfo is None:
                valid_time = valid_time.replace(tzinfo=timezone.utc)
            times_utc.append(valid_time.isoformat())

            batch_results = all_fxx_results[fxx]
            for i, resort in enumerate(resorts):
                all_resort_data[resort.slug].append(batch_results[i])

        if not times_utc:
            raise ValueError(f"No forecast hours extracted for {model_id}")

        resorts_with_valid_data = 0

        # Build and store forecasts for each resort
        from weather.parsing.grib2_parser import build_hourly_data
        from weather.utils.snow import calculate_hourly_snowfall

        for resort in resorts:
            try:
                extracted = all_resort_data[resort.slug]
                if not extracted:
                    continue

                hourly_data, hourly_units = build_hourly_data(extracted, model_id)

                # Validate: skip if all values are null
                all_null = all(
                    v is None or (isinstance(v, (list, tuple)) and all(x is None for x in v))
                    for v in hourly_data.values()
                )
                if all_null:
                    logger.warning(
                        f"All data null for {resort.slug} ({model_id}), skipping upsert"
                    )
                    continue

                # Compute enhanced snowfall
                enhanced_data = {}
                enhanced_units = {"enhanced_snowfall": "cm", "rain": "mm"}

                precip = hourly_data.get("precipitation", ())
                temp = hourly_data.get("temperature_2m", ())

                if precip and temp:
                    for elev_type, elev_m in [
                        ("summit", resort.summit_elevation_m),
                        ("base", resort.base_elevation_m),
                    ]:
                        snowfall, rain, _ = calculate_hourly_snowfall(
                            precip_values=precip,
                            temp_values=temp,
                            freezing_levels=hourly_data.get("freezing_level_height"),
                            elevation_m=elev_m,
                        )
                        enhanced_data_elev = {
                            "enhanced_snowfall": list(snowfall),
                            "rain": list(rain),
                        }

                        forecast_data = {
                            "times_utc": times_utc,
                            "hourly_data": {k: list(v) for k, v in hourly_data.items()},
                            "hourly_units": hourly_units,
                            "enhanced_hourly_data": enhanced_data_elev,
                            "enhanced_hourly_units": enhanced_units,
                        }

                        upsert_forecast(
                            session, resort.slug, model_id, elev_type,
                            forecast_data, run_dt,
                        )

                resorts_with_valid_data += 1
                resorts_processed += 1

            except Exception as e:
                logger.error(f"Failed to process {resort.slug} for {model_id}: {e}")

        if resorts_with_valid_data == 0:
            raise ValueError(
                f"All forecast data null for {model_id} run {run_dt} — "
                f"extraction produced no valid data for any resort"
            )

        # Mark model run as completed
        model_run.status = "completed"
        model_run.completed_at = datetime.now(timezone.utc)
        model_run.resorts_processed = resorts_processed
        session.commit()

        # Update job record
        duration = time.time() - start_time
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.duration_seconds = duration
        job.resorts_processed = resorts_processed
        session.commit()

        logger.info(
            f"Completed {model_id} run {run_dt}: {resorts_processed} resorts in {duration:.1f}s"
        )
        return resorts_processed

    except Exception as e:
        logger.error(f"Model run {model_id} {run_dt} failed: {e}")
        model_run.status = "failed"
        model_run.error = str(e)
        job.status = "failed"
        job.error = str(e)
        job.completed_at = datetime.now(timezone.utc)
        job.duration_seconds = time.time() - start_time
        session.commit()
        raise
