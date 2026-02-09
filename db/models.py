"""SQLAlchemy ORM models for ActuallyOpenSnow."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Boolean,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Resort(Base):
    """Ski resort definitions."""

    __tablename__ = "resorts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    state = Column(String(10), nullable=False, index=True)
    country = Column(String(10), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    base_elevation_m = Column(Float, nullable=False)
    summit_elevation_m = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Resort(slug={self.slug!r}, name={self.name!r})>"


class ModelRun(Base):
    """Track processed model runs."""

    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(50), nullable=False, index=True)
    run_datetime = Column(DateTime, nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, processing, completed, failed
    error = Column(Text, nullable=True)
    resorts_processed = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("model_id", "run_datetime", name="uq_model_run"),
        Index("ix_model_runs_model_status", "model_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ModelRun(model={self.model_id!r}, run={self.run_datetime}, status={self.status!r})>"


class Forecast(Base):
    """Hourly forecast data per resort/model/run."""

    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resort_slug = Column(String(100), nullable=False, index=True)
    model_id = Column(String(50), nullable=False, index=True)
    elevation_type = Column(String(10), nullable=False)  # "summit" or "base"
    run_datetime = Column(DateTime, nullable=False)
    times_utc = Column(JSON, nullable=False)  # list of ISO datetime strings
    hourly_data = Column(JSON, nullable=False)  # {var: [values]}
    hourly_units = Column(JSON, nullable=False)  # {var: unit_str}
    enhanced_hourly_data = Column(JSON, nullable=True)  # {enhanced_snowfall: [...], rain: [...]}
    enhanced_hourly_units = Column(JSON, nullable=True)
    ensemble_ranges = Column(JSON, nullable=True)  # {var: {p10: [...], p90: [...]}}
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "resort_slug", "model_id", "elevation_type", "run_datetime",
            name="uq_forecast",
        ),
        Index("ix_forecasts_resort_model", "resort_slug", "model_id"),
        Index("ix_forecasts_lookup", "resort_slug", "model_id", "elevation_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<Forecast(resort={self.resort_slug!r}, model={self.model_id!r}, "
            f"elev={self.elevation_type!r}, run={self.run_datetime})>"
        )


class BlendForecast(Base):
    """Pre-computed blended forecasts."""

    __tablename__ = "blend_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resort_slug = Column(String(100), nullable=False, index=True)
    elevation_type = Column(String(10), nullable=False)
    times_utc = Column(JSON, nullable=False)
    hourly_data = Column(JSON, nullable=False)
    hourly_units = Column(JSON, nullable=False)
    enhanced_hourly_data = Column(JSON, nullable=True)
    enhanced_hourly_units = Column(JSON, nullable=True)
    ensemble_ranges = Column(JSON, nullable=True)
    blend_weights = Column(JSON, nullable=False)  # {model_id: weight}
    source_model_runs = Column(JSON, nullable=False)  # {model_id: run_datetime_iso}
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "resort_slug", "elevation_type",
            name="uq_blend_forecast",
        ),
        Index("ix_blend_forecasts_lookup", "resort_slug", "elevation_type"),
    )

    def __repr__(self) -> str:
        return f"<BlendForecast(resort={self.resort_slug!r}, elev={self.elevation_type!r})>"


class JobHistory(Base):
    """Engine job tracking for monitoring and debugging."""

    __tablename__ = "job_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False, index=True)  # model_run, blend, cleanup
    model_id = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, index=True)  # started, completed, failed
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    resorts_processed = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_job_history_type_status", "job_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<JobHistory(type={self.job_type!r}, model={self.model_id!r}, status={self.status!r})>"
