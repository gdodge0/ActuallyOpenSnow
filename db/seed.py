"""Seed the resorts table from the hardcoded resort list."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from db.models import Base, Resort as DBResort
from db.session import get_engine, get_session_factory


def get_resort_data() -> list[dict]:
    """Get resort data from the backend's hardcoded list.

    Returns:
        List of resort dicts with all fields.
    """
    # Add backend to path so we can import its resort list
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    from app.resorts import RESORTS

    return [
        {
            "slug": r.slug,
            "name": r.name,
            "state": r.state,
            "country": r.country,
            "lat": r.lat,
            "lon": r.lon,
            "base_elevation_m": r.base_elevation_m,
            "summit_elevation_m": r.summit_elevation_m,
        }
        for r in RESORTS
    ]


def seed_resorts(session: Session) -> int:
    """Seed or update the resorts table.

    Uses upsert logic: inserts new resorts, updates existing ones.

    Args:
        session: SQLAlchemy session.

    Returns:
        Number of resorts seeded/updated.
    """
    resorts = get_resort_data()
    count = 0

    for data in resorts:
        existing = session.query(DBResort).filter_by(slug=data["slug"]).first()
        if existing:
            # Update existing resort
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            # Insert new resort
            session.add(DBResort(**data))
        count += 1

    return count


def run_seed(database_url: str | None = None) -> None:
    """Run the full seed process.

    Args:
        database_url: Optional database URL override.
    """
    engine = get_engine(database_url)

    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    factory = get_session_factory(engine)
    session = factory()

    try:
        count = seed_resorts(session)
        session.commit()
        print(f"Seeded {count} resorts successfully.")
    except Exception as e:
        session.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()
