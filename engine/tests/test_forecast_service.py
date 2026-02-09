"""Tests for forecast service database operations."""

import pytest
from datetime import datetime, timezone

from db.models import Forecast as DBForecast, BlendForecast, ModelRun
from engine.services.forecast_service import (
    upsert_forecast,
    get_latest_forecast,
    upsert_blend_forecast,
    get_blend_forecast,
    get_or_create_model_run,
)


class TestUpsertForecast:
    """Tests for upsert_forecast."""

    def test_insert_new_forecast(self, session, sample_forecast_dict):
        run_dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        result = upsert_forecast(
            session, "jackson-hole", "gfs", "summit",
            sample_forecast_dict, run_dt,
        )
        session.commit()

        assert result is not None
        assert result.resort_slug == "jackson-hole"
        assert result.model_id == "gfs"
        assert session.query(DBForecast).count() == 1

    def test_update_existing_forecast(self, session, sample_forecast_dict):
        run_dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        upsert_forecast(session, "jackson-hole", "gfs", "summit", sample_forecast_dict, run_dt)
        session.commit()

        # Update with new data
        updated_data = {**sample_forecast_dict}
        updated_data["hourly_data"]["temperature_2m"] = [-10.0, -11.0, -12.0]
        upsert_forecast(session, "jackson-hole", "gfs", "summit", updated_data, run_dt)
        session.commit()

        # Should still be just one record
        assert session.query(DBForecast).count() == 1
        f = session.query(DBForecast).first()
        assert f.hourly_data["temperature_2m"][0] == -10.0

    def test_different_elevations_separate(self, session, sample_forecast_dict):
        run_dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        upsert_forecast(session, "jackson-hole", "gfs", "summit", sample_forecast_dict, run_dt)
        upsert_forecast(session, "jackson-hole", "gfs", "base", sample_forecast_dict, run_dt)
        session.commit()

        assert session.query(DBForecast).count() == 2

    def test_different_models_separate(self, session, sample_forecast_dict):
        run_dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        upsert_forecast(session, "jackson-hole", "gfs", "summit", sample_forecast_dict, run_dt)
        upsert_forecast(session, "jackson-hole", "hrrr", "summit", sample_forecast_dict, run_dt)
        session.commit()

        assert session.query(DBForecast).count() == 2


class TestGetLatestForecast:
    """Tests for get_latest_forecast."""

    def test_no_forecast_returns_none(self, session):
        result = get_latest_forecast(session, "jackson-hole", "gfs")
        assert result is None

    def test_returns_latest_run(self, session, sample_forecast_dict):
        for hour in [0, 6, 12]:
            run_dt = datetime(2024, 1, 1, hour, 0, tzinfo=timezone.utc)
            upsert_forecast(session, "jackson-hole", "gfs", "summit", sample_forecast_dict, run_dt)
        session.commit()

        result = get_latest_forecast(session, "jackson-hole", "gfs")
        assert result is not None
        # SQLite strips tzinfo, so compare without it
        assert result.run_datetime.replace(tzinfo=None) == datetime(2024, 1, 1, 12, 0)


class TestUpsertBlendForecast:
    """Tests for blend forecast upsert."""

    def test_insert_blend(self, session, sample_forecast_dict):
        weights = {"gfs": 2.0, "ifs": 2.0}
        sources = {"gfs": "2024-01-01T00:00:00", "ifs": "2024-01-01T00:00:00"}

        result = upsert_blend_forecast(
            session, "jackson-hole", "summit",
            sample_forecast_dict, weights, sources,
        )
        session.commit()

        assert result.resort_slug == "jackson-hole"
        assert result.blend_weights["gfs"] == 2.0

    def test_update_blend(self, session, sample_forecast_dict):
        weights = {"gfs": 2.0}
        sources = {"gfs": "2024-01-01T00:00:00"}

        upsert_blend_forecast(session, "jackson-hole", "summit", sample_forecast_dict, weights, sources)
        session.commit()

        # Update
        new_weights = {"gfs": 3.0, "hrrr": 3.0}
        upsert_blend_forecast(session, "jackson-hole", "summit", sample_forecast_dict, new_weights, sources)
        session.commit()

        assert session.query(BlendForecast).count() == 1
        b = session.query(BlendForecast).first()
        assert b.blend_weights["gfs"] == 3.0


class TestGetBlendForecast:
    """Tests for get_blend_forecast."""

    def test_no_blend_returns_none(self, session):
        assert get_blend_forecast(session, "jackson-hole") is None

    def test_returns_blend(self, session, sample_forecast_dict):
        upsert_blend_forecast(
            session, "jackson-hole", "summit",
            sample_forecast_dict,
            {"gfs": 2.0}, {"gfs": "2024-01-01T00:00:00"},
        )
        session.commit()

        result = get_blend_forecast(session, "jackson-hole", "summit")
        assert result is not None


class TestGetOrCreateModelRun:
    """Tests for get_or_create_model_run."""

    def test_creates_new(self, session):
        run, created = get_or_create_model_run(session, "gfs", datetime(2024, 1, 1))
        session.commit()
        assert created is True
        assert run.model_id == "gfs"
        assert run.status == "pending"

    def test_gets_existing(self, session):
        dt = datetime(2024, 1, 1)
        get_or_create_model_run(session, "gfs", dt)
        session.commit()

        run, created = get_or_create_model_run(session, "gfs", dt)
        assert created is False
        assert session.query(ModelRun).count() == 1
