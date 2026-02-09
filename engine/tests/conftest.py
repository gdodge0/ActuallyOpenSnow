"""Shared test fixtures for engine tests."""

import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, Resort as DBResort


@pytest.fixture
def engine():
    """In-memory SQLite engine for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Database session for unit tests."""
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def seeded_session(session):
    """Session with resort data pre-seeded."""
    resorts = [
        DBResort(
            slug="jackson-hole", name="Jackson Hole", state="WY", country="US",
            lat=43.5872, lon=-110.8281, base_elevation_m=1924, summit_elevation_m=3185,
        ),
        DBResort(
            slug="vail", name="Vail", state="CO", country="US",
            lat=39.6403, lon=-106.3742, base_elevation_m=2476, summit_elevation_m=3527,
        ),
        DBResort(
            slug="alta", name="Alta", state="UT", country="US",
            lat=40.5884, lon=-111.6387, base_elevation_m=2600, summit_elevation_m=3216,
        ),
    ]
    session.add_all(resorts)
    session.commit()
    return session


@pytest.fixture
def sample_forecast_dict():
    """Sample forecast data dict as it would be stored in DB."""
    return {
        "times_utc": [
            "2024-01-01T00:00:00+00:00",
            "2024-01-01T01:00:00+00:00",
            "2024-01-01T02:00:00+00:00",
        ],
        "hourly_data": {
            "temperature_2m": [-5.0, -6.0, -7.0],
            "snowfall": [0.5, 1.2, 0.8],
            "precipitation": [0.5, 1.0, 0.7],
            "wind_speed_10m": [20.0, 25.0, 22.0],
            "wind_gusts_10m": [35.0, 40.0, 38.0],
            "freezing_level_height": [2500.0, 2400.0, 2300.0],
        },
        "hourly_units": {
            "temperature_2m": "C",
            "snowfall": "cm",
            "precipitation": "mm",
            "wind_speed_10m": "kmh",
            "wind_gusts_10m": "kmh",
            "freezing_level_height": "m",
        },
        "enhanced_hourly_data": {
            "enhanced_snowfall": [0.8, 1.8, 1.2],
            "rain": [0.0, 0.0, 0.0],
        },
        "enhanced_hourly_units": {
            "enhanced_snowfall": "cm",
            "rain": "mm",
        },
    }
