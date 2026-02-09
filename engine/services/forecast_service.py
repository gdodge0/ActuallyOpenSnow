"""Database operations for forecast data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from db.models import Forecast as DBForecast, BlendForecast, ModelRun


def upsert_forecast(
    session: Session,
    resort_slug: str,
    model_id: str,
    elevation_type: str,
    data: dict[str, Any],
    run_datetime: datetime,
) -> DBForecast:
    """Insert or update a forecast record.

    Args:
        session: DB session.
        resort_slug: Resort slug.
        model_id: Model ID.
        elevation_type: "summit" or "base".
        data: Forecast data dict with times_utc, hourly_data, etc.
        run_datetime: Model run datetime.

    Returns:
        The upserted Forecast record.
    """
    existing = (
        session.query(DBForecast)
        .filter_by(
            resort_slug=resort_slug,
            model_id=model_id,
            elevation_type=elevation_type,
            run_datetime=run_datetime,
        )
        .first()
    )

    if existing:
        existing.times_utc = data["times_utc"]
        existing.hourly_data = data["hourly_data"]
        existing.hourly_units = data["hourly_units"]
        existing.enhanced_hourly_data = data.get("enhanced_hourly_data")
        existing.enhanced_hourly_units = data.get("enhanced_hourly_units")
        existing.ensemble_ranges = data.get("ensemble_ranges")
        return existing

    forecast = DBForecast(
        resort_slug=resort_slug,
        model_id=model_id,
        elevation_type=elevation_type,
        run_datetime=run_datetime,
        times_utc=data["times_utc"],
        hourly_data=data["hourly_data"],
        hourly_units=data["hourly_units"],
        enhanced_hourly_data=data.get("enhanced_hourly_data"),
        enhanced_hourly_units=data.get("enhanced_hourly_units"),
        ensemble_ranges=data.get("ensemble_ranges"),
    )
    session.add(forecast)
    return forecast


def get_latest_forecast(
    session: Session,
    resort_slug: str,
    model_id: str,
    elevation_type: str = "summit",
) -> DBForecast | None:
    """Get the latest forecast for a resort/model/elevation.

    Args:
        session: DB session.
        resort_slug: Resort slug.
        model_id: Model ID.
        elevation_type: "summit" or "base".

    Returns:
        Latest Forecast or None.
    """
    return (
        session.query(DBForecast)
        .filter_by(
            resort_slug=resort_slug,
            model_id=model_id,
            elevation_type=elevation_type,
        )
        .order_by(DBForecast.run_datetime.desc())
        .first()
    )


def upsert_blend_forecast(
    session: Session,
    resort_slug: str,
    elevation_type: str,
    data: dict[str, Any],
    blend_weights: dict[str, float],
    source_model_runs: dict[str, str],
) -> BlendForecast:
    """Insert or update a blend forecast.

    Args:
        session: DB session.
        resort_slug: Resort slug.
        elevation_type: "summit" or "base".
        data: Blend data dict.
        blend_weights: Weights used.
        source_model_runs: Source model run times.

    Returns:
        The upserted BlendForecast record.
    """
    existing = (
        session.query(BlendForecast)
        .filter_by(resort_slug=resort_slug, elevation_type=elevation_type)
        .first()
    )

    if existing:
        existing.times_utc = data["times_utc"]
        existing.hourly_data = data["hourly_data"]
        existing.hourly_units = data["hourly_units"]
        existing.enhanced_hourly_data = data.get("enhanced_hourly_data")
        existing.enhanced_hourly_units = data.get("enhanced_hourly_units")
        existing.ensemble_ranges = data.get("ensemble_ranges")
        existing.blend_weights = blend_weights
        existing.source_model_runs = source_model_runs
        return existing

    blend = BlendForecast(
        resort_slug=resort_slug,
        elevation_type=elevation_type,
        times_utc=data["times_utc"],
        hourly_data=data["hourly_data"],
        hourly_units=data["hourly_units"],
        enhanced_hourly_data=data.get("enhanced_hourly_data"),
        enhanced_hourly_units=data.get("enhanced_hourly_units"),
        ensemble_ranges=data.get("ensemble_ranges"),
        blend_weights=blend_weights,
        source_model_runs=source_model_runs,
    )
    session.add(blend)
    return blend


def get_blend_forecast(
    session: Session,
    resort_slug: str,
    elevation_type: str = "summit",
) -> BlendForecast | None:
    """Get the current blend forecast for a resort.

    Args:
        session: DB session.
        resort_slug: Resort slug.
        elevation_type: "summit" or "base".

    Returns:
        BlendForecast or None.
    """
    return (
        session.query(BlendForecast)
        .filter_by(resort_slug=resort_slug, elevation_type=elevation_type)
        .first()
    )


def get_or_create_model_run(
    session: Session,
    model_id: str,
    run_datetime: datetime,
) -> tuple[ModelRun, bool]:
    """Get or create a model run record.

    Args:
        session: DB session.
        model_id: Model ID.
        run_datetime: Run datetime.

    Returns:
        Tuple of (ModelRun, created_flag).
    """
    existing = (
        session.query(ModelRun)
        .filter_by(model_id=model_id, run_datetime=run_datetime)
        .first()
    )
    if existing:
        return existing, False

    run = ModelRun(model_id=model_id, run_datetime=run_datetime, status="pending")
    session.add(run)
    return run, True
