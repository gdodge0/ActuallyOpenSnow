"""Test fixtures for the backend API."""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add project root to path for db imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Base, Forecast as DBForecast, BlendForecast as DBBlendForecast


@pytest.fixture
def db_engine():
    """In-memory SQLite database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    """Session factory bound to test engine."""
    return sessionmaker(bind=db_engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory):
    """Database session for direct DB manipulation in tests."""
    s = session_factory()
    yield s
    s.close()


@pytest.fixture
def sample_forecast_data():
    """Sample forecast data matching what the engine produces."""
    return {
        "times_utc": [f"2024-01-01T{h:02d}:00:00" for h in range(24)],
        "hourly_data": {
            "temperature_2m": [-5.0 + i * 0.5 for i in range(24)],
            "snowfall": [0.5] * 24,
            "precipitation": [1.0] * 24,
            "wind_speed_10m": [15.0] * 24,
            "wind_gusts_10m": [25.0] * 24,
        },
        "hourly_units": {
            "temperature_2m": "C",
            "snowfall": "cm",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
        },
        "enhanced_hourly_data": {
            "enhanced_snowfall": [0.8] * 24,
            "rain": [0.2] * 24,
        },
        "enhanced_hourly_units": {
            "enhanced_snowfall": "cm",
            "rain": "mm",
        },
    }


@pytest.fixture
def seeded_db(session, sample_forecast_data):
    """Seed database with forecast data for jackson-hole."""
    # Add a GFS forecast
    session.add(DBForecast(
        resort_slug="jackson-hole",
        model_id="gfs",
        elevation_type="summit",
        run_datetime=datetime(2024, 1, 1, 0, 0),
        **sample_forecast_data,
    ))

    # Add an IFS forecast
    session.add(DBForecast(
        resort_slug="jackson-hole",
        model_id="ifs",
        elevation_type="summit",
        run_datetime=datetime(2024, 1, 1, 0, 0),
        **sample_forecast_data,
    ))

    # Add a base elevation forecast
    session.add(DBForecast(
        resort_slug="jackson-hole",
        model_id="gfs",
        elevation_type="base",
        run_datetime=datetime(2024, 1, 1, 0, 0),
        **sample_forecast_data,
    ))

    # Add a blend forecast
    session.add(DBBlendForecast(
        resort_slug="jackson-hole",
        elevation_type="summit",
        times_utc=sample_forecast_data["times_utc"],
        hourly_data=sample_forecast_data["hourly_data"],
        hourly_units=sample_forecast_data["hourly_units"],
        enhanced_hourly_data=sample_forecast_data["enhanced_hourly_data"],
        enhanced_hourly_units=sample_forecast_data["enhanced_hourly_units"],
        blend_weights={"gfs": 2.0, "ifs": 2.0},
        source_model_runs={"gfs": "2024-01-01T00:00:00", "ifs": "2024-01-01T00:00:00"},
    ))

    # Add blend for base
    session.add(DBBlendForecast(
        resort_slug="jackson-hole",
        elevation_type="base",
        times_utc=sample_forecast_data["times_utc"],
        hourly_data=sample_forecast_data["hourly_data"],
        hourly_units=sample_forecast_data["hourly_units"],
        enhanced_hourly_data=sample_forecast_data["enhanced_hourly_data"],
        enhanced_hourly_units=sample_forecast_data["enhanced_hourly_units"],
        blend_weights={"gfs": 2.0, "ifs": 2.0},
        source_model_runs={"gfs": "2024-01-01T00:00:00", "ifs": "2024-01-01T00:00:00"},
    ))

    session.commit()
    return session


@pytest.fixture
def app_client(session_factory, seeded_db):
    """FastAPI TestClient with mocked DB session."""
    from app.main import app, get_db

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.cache_get", return_value=None), \
         patch("app.main.cache_set"):
        client = TestClient(app)
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def empty_app_client():
    """FastAPI TestClient with empty DB (no forecast data)."""
    from app.main import app, get_db

    empty_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(empty_engine)
    empty_factory = sessionmaker(bind=empty_engine, expire_on_commit=False)

    def override_get_db():
        session = empty_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.main.cache_get", return_value=None), \
         patch("app.main.cache_set"):
        client = TestClient(app)
        yield client
    app.dependency_overrides.clear()
    empty_engine.dispose()
