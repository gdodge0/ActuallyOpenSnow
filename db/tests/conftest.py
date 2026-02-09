"""Shared fixtures for database tests."""

import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def sample_resort_data():
    """Sample resort data for testing."""
    return {
        "slug": "jackson-hole",
        "name": "Jackson Hole",
        "state": "WY",
        "country": "US",
        "lat": 43.5872,
        "lon": -110.8281,
        "base_elevation_m": 1924.0,
        "summit_elevation_m": 3185.0,
    }


@pytest.fixture
def sample_forecast_data():
    """Sample forecast data for testing."""
    return {
        "resort_slug": "jackson-hole",
        "model_id": "gfs",
        "elevation_type": "summit",
        "run_datetime": datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        "times_utc": ["2024-01-01T00:00:00+00:00", "2024-01-01T01:00:00+00:00"],
        "hourly_data": {
            "temperature_2m": [-5.0, -6.0],
            "snowfall": [0.5, 1.2],
        },
        "hourly_units": {
            "temperature_2m": "C",
            "snowfall": "cm",
        },
    }
