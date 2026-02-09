"""Database session management."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/actuallyopensnow"


def get_database_url() -> str:
    """Get the database URL from environment or default."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine(database_url: str | None = None, **kwargs) -> Engine:
    """Create a SQLAlchemy engine.

    Args:
        database_url: Database connection URL. Defaults to DATABASE_URL env var.
        **kwargs: Additional engine kwargs (pool_size, echo, etc.).

    Returns:
        SQLAlchemy Engine instance.
    """
    url = database_url or get_database_url()
    defaults = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }
    defaults.update(kwargs)
    return create_engine(url, **defaults)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Create a session factory.

    Args:
        engine: SQLAlchemy engine. Creates one if not provided.

    Returns:
        Configured sessionmaker.
    """
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    Automatically commits on success and rolls back on error.

    Args:
        engine: SQLAlchemy engine. Creates one if not provided.

    Yields:
        A SQLAlchemy Session.
    """
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
