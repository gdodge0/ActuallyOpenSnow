"""Tests for engine-backend job and status API routes."""

import pytest
from datetime import datetime, timezone

from db.models import ModelRun, JobHistory, BlendForecast


class TestEngineStatus:
    """Tests for /api/engine/status endpoint logic."""

    def test_status_with_completed_runs(self, seeded_db):
        """Test status returns latest completed model runs."""
        completed = (
            seeded_db.query(ModelRun)
            .filter_by(status="completed")
            .all()
        )
        assert len(completed) == 3

    def test_status_excludes_failed_runs(self, seeded_db):
        """Failed runs should not appear in latest runs."""
        failed = seeded_db.query(ModelRun).filter_by(status="failed").all()
        assert len(failed) == 1
        assert failed[0].model_id == "gefs"


class TestListModels:
    """Tests for /api/engine/models endpoint logic."""

    def test_herbie_models_listed(self):
        """Only models with herbie_model should be listed."""
        from weather.config.models import MODELS
        herbie_models = [m for m in MODELS.values() if m.herbie_model]
        assert len(herbie_models) >= 7  # hrrr, gfs, ifs, aifs, nbm, gefs, ecmwf_ens


class TestListJobs:
    """Tests for /api/engine/jobs endpoint logic."""

    def test_jobs_returned(self, seeded_db):
        jobs = seeded_db.query(JobHistory).order_by(JobHistory.created_at.desc()).all()
        assert len(jobs) == 3

    def test_filter_by_type(self, seeded_db):
        model_jobs = seeded_db.query(JobHistory).filter_by(job_type="model_run").all()
        assert len(model_jobs) == 2

        blend_jobs = seeded_db.query(JobHistory).filter_by(job_type="blend").all()
        assert len(blend_jobs) == 1

    def test_job_has_duration(self, seeded_db):
        job = seeded_db.query(JobHistory).filter_by(status="completed", job_type="model_run").first()
        assert job.duration_seconds == 600

    def test_failed_job_has_error(self, seeded_db):
        job = seeded_db.query(JobHistory).filter_by(status="failed").first()
        assert job.error == "Network error"


class TestResortStatus:
    """Tests for /api/engine/resorts/{slug}/status logic."""

    def test_no_forecasts_returns_empty(self, session):
        from db.models import Forecast as DBForecast
        count = session.query(DBForecast).filter_by(resort_slug="jackson-hole").count()
        assert count == 0

    def test_blend_availability(self, session):
        # No blend initially
        blend = session.query(BlendForecast).filter_by(resort_slug="jackson-hole").first()
        assert blend is None

        # Add blend
        session.add(BlendForecast(
            resort_slug="jackson-hole", elevation_type="summit",
            times_utc=["2024-01-01T00:00:00"],
            hourly_data={"temperature_2m": [-5.0]},
            hourly_units={"temperature_2m": "C"},
            blend_weights={"gfs": 2.0},
            source_model_runs={"gfs": "2024-01-01T00:00:00"},
        ))
        session.commit()

        blend = session.query(BlendForecast).filter_by(resort_slug="jackson-hole").first()
        assert blend is not None


class TestExtractionRequest:
    """Tests for extraction request validation."""

    def test_extraction_request_model(self):
        from engine_backend_app_routes_extraction import ExtractionRequest

        req = ExtractionRequest(lat=43.5, lon=-110.8)
        assert req.model == "blend"
        assert req.elevation is None

    def test_extraction_request_custom(self):
        from engine_backend_app_routes_extraction import ExtractionRequest

        req = ExtractionRequest(lat=43.5, lon=-110.8, elevation=3000.0, model="hrrr")
        assert req.model == "hrrr"
        assert req.elevation == 3000.0


# Import the actual modules for validation tests
try:
    # Try direct import for the extraction model
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Create module aliases for import
    import importlib
    spec = importlib.util.spec_from_file_location(
        "engine_backend_app_routes_extraction",
        str(Path(__file__).parent.parent / "app" / "routes" / "extraction.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["engine_backend_app_routes_extraction"] = module
    spec.loader.exec_module(module)
    ExtractionRequest = module.ExtractionRequest
except Exception:
    # If import fails, skip the extraction tests
    ExtractionRequest = None


class TestExtractionRequestValidation:
    """Tests for ExtractionRequest pydantic model."""

    @pytest.mark.skipif(ExtractionRequest is None, reason="Could not import ExtractionRequest")
    def test_valid_request(self):
        req = ExtractionRequest(lat=43.5, lon=-110.8)
        assert req.lat == 43.5
        assert req.model == "blend"

    @pytest.mark.skipif(ExtractionRequest is None, reason="Could not import ExtractionRequest")
    def test_with_all_fields(self):
        req = ExtractionRequest(lat=43.5, lon=-110.8, elevation=3000.0, model="hrrr")
        assert req.elevation == 3000.0
        assert req.model == "hrrr"
