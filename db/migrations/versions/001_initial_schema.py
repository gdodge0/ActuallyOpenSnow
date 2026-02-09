"""Initial schema — resorts, model_runs, forecasts, blend_forecasts, job_history.

Revision ID: 001
Revises: None
Create Date: 2026-02-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Resorts
    op.create_table(
        "resorts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("state", sa.String(10), nullable=False),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("base_elevation_m", sa.Float(), nullable=False),
        sa.Column("summit_elevation_m", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resorts_slug", "resorts", ["slug"])
    op.create_index("ix_resorts_state", "resorts", ["state"])

    # Model runs
    op.create_table(
        "model_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.String(50), nullable=False),
        sa.Column("run_datetime", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("resorts_processed", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("model_id", "run_datetime", name="uq_model_run"),
    )
    op.create_index("ix_model_runs_model_id", "model_runs", ["model_id"])
    op.create_index("ix_model_runs_status", "model_runs", ["status"])
    op.create_index("ix_model_runs_model_status", "model_runs", ["model_id", "status"])

    # Forecasts
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("resort_slug", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(50), nullable=False),
        sa.Column("elevation_type", sa.String(10), nullable=False),
        sa.Column("run_datetime", sa.DateTime(), nullable=False),
        sa.Column("times_utc", sa.JSON(), nullable=False),
        sa.Column("hourly_data", sa.JSON(), nullable=False),
        sa.Column("hourly_units", sa.JSON(), nullable=False),
        sa.Column("enhanced_hourly_data", sa.JSON(), nullable=True),
        sa.Column("enhanced_hourly_units", sa.JSON(), nullable=True),
        sa.Column("ensemble_ranges", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "resort_slug", "model_id", "elevation_type", "run_datetime",
            name="uq_forecast",
        ),
    )
    op.create_index("ix_forecasts_resort_slug", "forecasts", ["resort_slug"])
    op.create_index("ix_forecasts_model_id", "forecasts", ["model_id"])
    op.create_index("ix_forecasts_resort_model", "forecasts", ["resort_slug", "model_id"])
    op.create_index("ix_forecasts_lookup", "forecasts", ["resort_slug", "model_id", "elevation_type"])

    # Blend forecasts
    op.create_table(
        "blend_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("resort_slug", sa.String(100), nullable=False),
        sa.Column("elevation_type", sa.String(10), nullable=False),
        sa.Column("times_utc", sa.JSON(), nullable=False),
        sa.Column("hourly_data", sa.JSON(), nullable=False),
        sa.Column("hourly_units", sa.JSON(), nullable=False),
        sa.Column("enhanced_hourly_data", sa.JSON(), nullable=True),
        sa.Column("enhanced_hourly_units", sa.JSON(), nullable=True),
        sa.Column("ensemble_ranges", sa.JSON(), nullable=True),
        sa.Column("blend_weights", sa.JSON(), nullable=False),
        sa.Column("source_model_runs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("resort_slug", "elevation_type", name="uq_blend_forecast"),
    )
    op.create_index("ix_blend_forecasts_resort_slug", "blend_forecasts", ["resort_slug"])
    op.create_index("ix_blend_forecasts_lookup", "blend_forecasts", ["resort_slug", "elevation_type"])

    # Job history
    op.create_table(
        "job_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("resorts_processed", sa.Integer(), server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_history_job_type", "job_history", ["job_type"])
    op.create_index("ix_job_history_status", "job_history", ["status"])
    op.create_index("ix_job_history_type_status", "job_history", ["job_type", "status"])


def downgrade() -> None:
    op.drop_table("job_history")
    op.drop_table("blend_forecasts")
    op.drop_table("forecasts")
    op.drop_table("model_runs")
    op.drop_table("resorts")
