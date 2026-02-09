"""Test fixtures for engine-backend."""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Base, ModelRun, JobHistory, BlendForecast
from db.models import Forecast as DBForecast


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def seeded_db(session):
    """Seed some model runs and jobs for testing."""
    # Model runs
    for model in ["gfs", "hrrr", "ifs"]:
        run = ModelRun(
            model_id=model,
            run_datetime=datetime(2024, 1, 1, 0, 0),
            status="completed",
            completed_at=datetime(2024, 1, 1, 0, 30),
            resorts_processed=75,
        )
        session.add(run)

    # Failed run
    session.add(ModelRun(
        model_id="gefs",
        run_datetime=datetime(2024, 1, 1, 0, 0),
        status="failed",
        error="Download timeout",
    ))

    # Jobs
    session.add(JobHistory(
        job_type="model_run", model_id="gfs", status="completed",
        started_at=datetime(2024, 1, 1, 0, 0),
        completed_at=datetime(2024, 1, 1, 0, 10),
        duration_seconds=600, resorts_processed=75,
    ))
    session.add(JobHistory(
        job_type="blend", status="completed",
        started_at=datetime(2024, 1, 1, 0, 15),
        completed_at=datetime(2024, 1, 1, 0, 16),
        duration_seconds=60, resorts_processed=150,
    ))
    session.add(JobHistory(
        job_type="model_run", model_id="hrrr", status="failed",
        started_at=datetime(2024, 1, 1, 1, 0),
        error="Network error",
    ))

    session.commit()
    return session


@pytest.fixture
def app_client(session_factory):
    """FastAPI test client with mocked DB session."""
    from fastapi.testclient import TestClient
    from engine_backend_app import create_test_app

    app = create_test_app(session_factory)
    return TestClient(app)
