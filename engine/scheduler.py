"""APScheduler-based job scheduler for the engine."""

from __future__ import annotations

import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db.models import Base, ModelRun, Resort as DBResort
from db.session import get_engine, get_session_factory
from db.seed import seed_resorts
from engine.config import (
    BOOTSTRAP_MAX_WORKERS,
    DATABASE_URL,
    GRIB_CACHE_DIR,
    MODEL_SCHEDULES,
    REDIS_URL,
)
from engine.services.grib_service import cleanup_old_files
from engine.workers.blend_worker import compute_all_blends
from engine.workers.model_worker import process_model_run
from weather.clients.herbie_client import HerbieClient
from weather.config.models import get_model_config

logger = logging.getLogger(__name__)


def process_with_fallback(session, herbie_client: HerbieClient, model_id: str) -> int:
    """Try processing a model run, falling back to the previous run on failure.

    Args:
        session: DB session.
        herbie_client: HerbieClient instance.
        model_id: Model to process.

    Returns:
        Number of resorts processed.
    """
    config = get_model_config(model_id)
    candidates = herbie_client.get_candidate_run_dts(config)
    last_error = None
    for run_dt in candidates:
        try:
            return process_model_run(session, herbie_client, model_id, run_dt)
        except ValueError as e:
            last_error = e
            logger.warning(f"No data for {model_id} run {run_dt}, trying previous: {e}")
    logger.error(f"All candidate runs failed for {model_id}: {last_error}")
    return 0


def _bootstrap_model(session_factory, herbie_client, model_id) -> tuple[str, int]:
    """Process a single model during bootstrap. Runs in its own thread."""
    session = session_factory()
    try:
        count = process_with_fallback(session, herbie_client, model_id)
        return (model_id, count)
    except Exception as e:
        logger.error(f"Initial processing failed for {model_id}: {e}")
        return (model_id, 0)
    finally:
        session.close()


def bootstrap_data(session_factory, herbie_client) -> None:
    """Seed resorts and process any missing model data on first startup."""
    session = session_factory()
    try:
        # Seed resorts if table is empty
        resort_count = session.query(DBResort).count()
        if resort_count == 0:
            logger.info("No resorts found — seeding database")
            count = seed_resorts(session)
            session.commit()
            logger.info(f"Seeded {count} resorts")
        else:
            logger.info(f"Found {resort_count} resorts in database")

        # Determine which models need processing (serial check, single session)
        models_to_process = []
        for model_id in MODEL_SCHEDULES:
            completed = (
                session.query(ModelRun)
                .filter_by(model_id=model_id, status="completed")
                .first()
            )
            if completed:
                logger.info(f"Model {model_id} already has data, skipping initial run")
            else:
                models_to_process.append(model_id)

    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        session.rollback()
        return
    finally:
        session.close()

    # Process models in parallel (each thread gets its own session)
    if models_to_process:
        logger.info(f"Processing {len(models_to_process)} models in parallel: {models_to_process}")
        max_workers = min(BOOTSTRAP_MAX_WORKERS, len(models_to_process))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_bootstrap_model, session_factory, herbie_client, mid): mid
                for mid in models_to_process
            }
            for future in as_completed(futures):
                model_id, count = future.result()
                if count > 0:
                    logger.info(f"Bootstrap completed {model_id}: {count} resorts")
                else:
                    logger.warning(f"Bootstrap produced no data for {model_id}")

    # Compute blends after all models finish
    session = session_factory()
    try:
        completed_count = (
            session.query(ModelRun)
            .filter_by(status="completed")
            .count()
        )
        if completed_count > 0:
            logger.info("Computing initial blends")
            try:
                compute_all_blends(session)
            except Exception as e:
                logger.error(f"Initial blend failed: {e}")
    finally:
        session.close()


def create_scheduler() -> BlockingScheduler:
    """Create and configure the APScheduler."""
    scheduler = BlockingScheduler()

    # Database setup
    engine = get_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(engine)

    # Herbie client
    herbie_client = HerbieClient(cache_dir=GRIB_CACHE_DIR)

    # Bootstrap: seed resorts + process missing models on first startup
    bootstrap_data(session_factory, herbie_client)

    # Register model processing jobs
    for model_id, interval_minutes in MODEL_SCHEDULES.items():
        config = get_model_config(model_id)

        def make_job(mid, client):
            def job():
                session = session_factory()
                try:
                    logger.info(f"Processing {mid}")
                    process_with_fallback(session, client, mid)
                except Exception as e:
                    logger.error(f"Job failed for {mid}: {e}")
                finally:
                    session.close()
            return job

        scheduler.add_job(
            make_job(model_id, herbie_client),
            IntervalTrigger(minutes=interval_minutes),
            id=f"model_{model_id}",
            name=f"Process {config.display_name}",
            max_instances=1,
            replace_existing=True,
        )

    # Blend recomputation — every 15 minutes
    def blend_job():
        session = session_factory()
        try:
            compute_all_blends(session)
        except Exception as e:
            logger.error(f"Blend job failed: {e}")
        finally:
            session.close()

    scheduler.add_job(
        blend_job,
        IntervalTrigger(minutes=15),
        id="blend",
        name="Compute blends",
        max_instances=1,
        replace_existing=True,
    )

    # GRIB2 cache cleanup — every hour
    def cleanup_job():
        try:
            removed = cleanup_old_files()
            if removed:
                logger.info(f"Cleaned up {removed} old GRIB2 files")
        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")

    scheduler.add_job(
        cleanup_job,
        IntervalTrigger(hours=1),
        id="cleanup",
        name="GRIB2 cache cleanup",
        max_instances=1,
        replace_existing=True,
    )

    return scheduler


def main():
    """Entry point for the engine service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    logger.info("Starting ActuallyOpenSnow Engine")
    logger.info(f"Database: {DATABASE_URL}")
    logger.info(f"Redis: {REDIS_URL}")
    logger.info(f"GRIB cache: {GRIB_CACHE_DIR}")
    logger.info(f"Models: {list(MODEL_SCHEDULES.keys())}")

    scheduler = create_scheduler()

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Engine stopped")


if __name__ == "__main__":
    main()
