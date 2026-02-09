"""Tests for SQLAlchemy ORM models."""

import pytest
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from db.models import (
    Base,
    Resort,
    ModelRun,
    Forecast,
    BlendForecast,
    JobHistory,
)


class TestResortModel:
    """Tests for the Resort ORM model."""

    def test_create_resort(self, session, sample_resort_data):
        resort = Resort(**sample_resort_data)
        session.add(resort)
        session.commit()

        result = session.query(Resort).filter_by(slug="jackson-hole").first()
        assert result is not None
        assert result.name == "Jackson Hole"
        assert result.state == "WY"
        assert result.lat == pytest.approx(43.5872)

    def test_resort_slug_unique(self, session, sample_resort_data):
        session.add(Resort(**sample_resort_data))
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(Resort(**sample_resort_data))
            session.commit()

    def test_resort_repr(self, sample_resort_data):
        resort = Resort(**sample_resort_data)
        assert "jackson-hole" in repr(resort)

    def test_resort_required_fields(self, session):
        """Slug, name, state, country, lat, lon, elevations are required."""
        resort = Resort(slug="test")
        session.add(resort)
        with pytest.raises(IntegrityError):
            session.commit()


class TestModelRunModel:
    """Tests for the ModelRun ORM model."""

    def test_create_model_run(self, session):
        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1, 0, 0),
            status="pending",
        )
        session.add(run)
        session.commit()

        result = session.query(ModelRun).first()
        assert result.model_id == "gfs"
        assert result.status == "pending"

    def test_model_run_unique_constraint(self, session):
        """Same model + run_datetime should be unique."""
        dt = datetime(2024, 1, 1, 0, 0)
        session.add(ModelRun(model_id="gfs", run_datetime=dt, status="completed"))
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(ModelRun(model_id="gfs", run_datetime=dt, status="pending"))
            session.commit()

    def test_different_models_same_time_ok(self, session):
        dt = datetime(2024, 1, 1, 0, 0)
        session.add(ModelRun(model_id="gfs", run_datetime=dt, status="completed"))
        session.add(ModelRun(model_id="hrrr", run_datetime=dt, status="completed"))
        session.commit()

        count = session.query(ModelRun).count()
        assert count == 2

    def test_model_run_status_values(self, session):
        for status in ["pending", "processing", "completed", "failed"]:
            run = ModelRun(
                model_id=f"test_{status}",
                run_datetime=datetime(2024, 1, 1),
                status=status,
            )
            session.add(run)
        session.commit()
        assert session.query(ModelRun).count() == 4

    def test_model_run_repr(self):
        run = ModelRun(model_id="gfs", run_datetime=datetime(2024, 1, 1), status="completed")
        assert "gfs" in repr(run)


class TestForecastModel:
    """Tests for the Forecast ORM model."""

    def test_create_forecast(self, session, sample_forecast_data):
        forecast = Forecast(**sample_forecast_data)
        session.add(forecast)
        session.commit()

        result = session.query(Forecast).first()
        assert result.resort_slug == "jackson-hole"
        assert result.model_id == "gfs"
        assert result.elevation_type == "summit"
        assert len(result.times_utc) == 2

    def test_forecast_unique_constraint(self, session, sample_forecast_data):
        session.add(Forecast(**sample_forecast_data))
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(Forecast(**sample_forecast_data))
            session.commit()

    def test_forecast_different_elevation_types(self, session, sample_forecast_data):
        session.add(Forecast(**sample_forecast_data))

        base_data = {**sample_forecast_data, "elevation_type": "base"}
        session.add(Forecast(**base_data))
        session.commit()

        assert session.query(Forecast).count() == 2

    def test_forecast_json_data(self, session, sample_forecast_data):
        session.add(Forecast(**sample_forecast_data))
        session.commit()

        result = session.query(Forecast).first()
        assert result.hourly_data["temperature_2m"] == [-5.0, -6.0]
        assert result.hourly_units["snowfall"] == "cm"

    def test_forecast_optional_ensemble_ranges(self, session, sample_forecast_data):
        sample_forecast_data["ensemble_ranges"] = {
            "enhanced_snowfall": {"p10": [0.1, 0.2], "p90": [1.0, 2.0]}
        }
        session.add(Forecast(**sample_forecast_data))
        session.commit()

        result = session.query(Forecast).first()
        assert result.ensemble_ranges is not None
        assert "enhanced_snowfall" in result.ensemble_ranges


class TestBlendForecastModel:
    """Tests for the BlendForecast ORM model."""

    def test_create_blend_forecast(self, session):
        blend = BlendForecast(
            resort_slug="jackson-hole",
            elevation_type="summit",
            times_utc=["2024-01-01T00:00:00"],
            hourly_data={"temperature_2m": [-5.0]},
            hourly_units={"temperature_2m": "C"},
            blend_weights={"gfs": 2.0, "ifs": 2.0},
            source_model_runs={"gfs": "2024-01-01T00:00:00", "ifs": "2024-01-01T00:00:00"},
        )
        session.add(blend)
        session.commit()

        result = session.query(BlendForecast).first()
        assert result.resort_slug == "jackson-hole"
        assert result.blend_weights["gfs"] == 2.0

    def test_blend_unique_per_resort_elevation(self, session):
        data = dict(
            resort_slug="jackson-hole",
            elevation_type="summit",
            times_utc=["2024-01-01T00:00:00"],
            hourly_data={"temperature_2m": [-5.0]},
            hourly_units={"temperature_2m": "C"},
            blend_weights={"gfs": 2.0},
            source_model_runs={"gfs": "2024-01-01T00:00:00"},
        )
        session.add(BlendForecast(**data))
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(BlendForecast(**data))
            session.commit()

    def test_blend_ensemble_ranges(self, session):
        blend = BlendForecast(
            resort_slug="vail",
            elevation_type="summit",
            times_utc=["2024-01-01T00:00:00"],
            hourly_data={"temperature_2m": [-5.0]},
            hourly_units={"temperature_2m": "C"},
            ensemble_ranges={"enhanced_snowfall": {"p10": [0.5], "p90": [3.0]}},
            blend_weights={"gfs": 2.0},
            source_model_runs={"gfs": "2024-01-01T00:00:00"},
        )
        session.add(blend)
        session.commit()

        result = session.query(BlendForecast).first()
        assert result.ensemble_ranges["enhanced_snowfall"]["p90"] == [3.0]


class TestJobHistoryModel:
    """Tests for the JobHistory ORM model."""

    def test_create_job(self, session):
        job = JobHistory(
            job_type="model_run",
            model_id="gfs",
            status="completed",
            started_at=datetime(2024, 1, 1, 0, 0),
            completed_at=datetime(2024, 1, 1, 0, 10),
            duration_seconds=600.0,
            resorts_processed=75,
        )
        session.add(job)
        session.commit()

        result = session.query(JobHistory).first()
        assert result.job_type == "model_run"
        assert result.duration_seconds == 600.0
        assert result.resorts_processed == 75

    def test_job_with_error(self, session):
        job = JobHistory(
            job_type="model_run",
            model_id="hrrr",
            status="failed",
            started_at=datetime(2024, 1, 1, 0, 0),
            error="Download timeout after 30s",
        )
        session.add(job)
        session.commit()

        result = session.query(JobHistory).first()
        assert result.status == "failed"
        assert "timeout" in result.error

    def test_job_with_metadata(self, session):
        job = JobHistory(
            job_type="cleanup",
            status="completed",
            started_at=datetime(2024, 1, 1, 0, 0),
            metadata_={"files_deleted": 42, "bytes_freed": 1024000},
        )
        session.add(job)
        session.commit()

        result = session.query(JobHistory).first()
        assert result.metadata_["files_deleted"] == 42

    def test_job_repr(self):
        job = JobHistory(
            job_type="model_run",
            model_id="gfs",
            status="completed",
            started_at=datetime(2024, 1, 1),
        )
        assert "model_run" in repr(job)


class TestSeedData:
    """Tests for seed data integration."""

    def test_seed_resort_count(self, session):
        """Test that seed produces correct number of resorts."""
        from db.seed import get_resort_data

        resorts = get_resort_data()
        assert len(resorts) > 70  # We have 75+ resorts

    def test_seed_resort_data_format(self):
        """Test that seed data has expected fields."""
        from db.seed import get_resort_data

        resorts = get_resort_data()
        for r in resorts:
            assert "slug" in r
            assert "name" in r
            assert "state" in r
            assert "country" in r
            assert "lat" in r
            assert "lon" in r
            assert "base_elevation_m" in r
            assert "summit_elevation_m" in r

    def test_seed_to_db(self, session):
        """Test seeding resorts into the database."""
        from db.seed import seed_resorts

        count = seed_resorts(session)
        session.commit()

        assert count > 70
        assert session.query(Resort).count() == count

        # Verify a known resort
        jh = session.query(Resort).filter_by(slug="jackson-hole").first()
        assert jh is not None
        assert jh.state == "WY"

    def test_seed_idempotent(self, session):
        """Test that re-seeding doesn't create duplicates."""
        from db.seed import seed_resorts

        count1 = seed_resorts(session)
        session.commit()

        count2 = seed_resorts(session)
        session.commit()

        assert count1 == count2
        assert session.query(Resort).count() == count1
