"""Tests for model worker with mocked HerbieClient."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from db.models import ModelRun, Forecast as DBForecast, JobHistory, Resort as DBResort
from engine.workers.model_worker import process_model_run, get_stale_timeout, STALE_LOCK_FALLBACK


class TestProcessModelRun:
    """Tests for the model_worker.process_model_run function."""

    def _mock_herbie_client(self, batch_results=None, available_fxx=None):
        """Create a mocked HerbieClient using extract_all_hours_batch."""
        client = MagicMock()

        if batch_results is None:
            # Default: return valid data for 3 points
            point_data = [
                {
                    "temperature": 268.15,  # -5°C
                    "precipitation": 0.0,
                    "snowfall": 0.0,
                    "wind_u": 5.0,
                    "wind_v": 3.0,
                    "wind_gusts": 12.0,
                    "freezing_level": 2500.0,
                }
            ] * 3  # 3 resorts
            batch_results = {0: point_data}

        if available_fxx is None:
            available_fxx = sorted(batch_results.keys())

        client.extract_all_hours_batch.return_value = (available_fxx, batch_results)
        return client

    def test_skips_completed_run(self, seeded_session):
        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1),
            status="completed",
        )
        seeded_session.add(run)
        seeded_session.commit()

        client = self._mock_herbie_client()
        result = process_model_run(seeded_session, client, "gfs", datetime(2024, 1, 1))

        assert result == 0
        client.extract_all_hours_batch.assert_not_called()

    def test_skips_recent_processing_run(self, seeded_session):
        """A run that started recently should still be skipped."""
        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1),
            status="processing",
            started_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
        seeded_session.add(run)
        seeded_session.commit()

        client = self._mock_herbie_client()
        result = process_model_run(seeded_session, client, "gfs", datetime(2024, 1, 1))

        assert result == 0
        client.extract_all_hours_batch.assert_not_called()

    @patch("engine.workers.model_worker.get_model_config")
    def test_resets_stale_processing_run(self, mock_config, seeded_session):
        """A run stuck in processing beyond stale timeout should be reset and re-processed."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1),
            status="processing",
            started_at=datetime.now(timezone.utc) - timedelta(seconds=3000),
        )
        seeded_session.add(run)
        seeded_session.commit()

        client = self._mock_herbie_client()
        result = process_model_run(seeded_session, client, "gfs", datetime(2024, 1, 1))

        assert result == 3
        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "completed"

    @patch("engine.workers.model_worker.get_model_config")
    def test_resets_processing_run_without_started_at(self, mock_config, seeded_session):
        """A run stuck in processing with no started_at should be reset and re-processed."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1),
            status="processing",
            started_at=None,
        )
        seeded_session.add(run)
        seeded_session.commit()

        client = self._mock_herbie_client()
        result = process_model_run(seeded_session, client, "gfs", datetime(2024, 1, 1))

        assert result == 3
        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "completed"

    @patch("engine.workers.model_worker.get_model_config")
    def test_stale_timeout_uses_history(self, mock_config, seeded_session):
        """With job history, stale timeout = max(2*avg, 2500). A run within that window is skipped."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        # Seed job history with avg duration of 1000s → timeout = max(2000, 2500) = 2500
        for i in range(3):
            seeded_session.add(JobHistory(
                job_type="model_run", model_id="gfs", status="completed",
                started_at=datetime(2024, 1, 1), completed_at=datetime(2024, 1, 1),
                duration_seconds=1000,
            ))
        seeded_session.commit()

        # 2400s elapsed — within 2500s timeout, should be skipped
        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1),
            status="processing",
            started_at=datetime.now(timezone.utc) - timedelta(seconds=2400),
        )
        seeded_session.add(run)
        seeded_session.commit()

        client = self._mock_herbie_client()
        result = process_model_run(seeded_session, client, "gfs", datetime(2024, 1, 1))
        assert result == 0  # skipped, not stale yet

    @patch("engine.workers.model_worker.get_model_config")
    def test_stale_timeout_resets_beyond_history(self, mock_config, seeded_session):
        """With job history avg=1500s → timeout=max(3000, 2500)=3000. A run at 3100s is stale."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        # Seed job history with avg duration of 1500s → timeout = max(3000, 2500) = 3000
        for i in range(3):
            seeded_session.add(JobHistory(
                job_type="model_run", model_id="gfs", status="completed",
                started_at=datetime(2024, 1, 1), completed_at=datetime(2024, 1, 1),
                duration_seconds=1500,
            ))
        seeded_session.commit()

        run = ModelRun(
            model_id="gfs",
            run_datetime=datetime(2024, 1, 1),
            status="processing",
            started_at=datetime.now(timezone.utc) - timedelta(seconds=3100),
        )
        seeded_session.add(run)
        seeded_session.commit()

        client = self._mock_herbie_client()
        result = process_model_run(seeded_session, client, "gfs", datetime(2024, 1, 1))
        assert result == 3  # stale, reset and re-processed
        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "completed"

    def test_get_stale_timeout_no_history(self, session):
        """With no job history, returns fallback."""
        timeout = get_stale_timeout(session, "gfs")
        assert timeout == STALE_LOCK_FALLBACK

    def test_get_stale_timeout_with_history(self, session):
        """With history, returns max(2*avg, fallback)."""
        for _ in range(3):
            session.add(JobHistory(
                job_type="model_run", model_id="gfs", status="completed",
                started_at=datetime(2024, 1, 1), completed_at=datetime(2024, 1, 1),
                duration_seconds=2000,
            ))
        session.commit()
        # avg=2000, 2*2000=4000, max(4000, 2500)=4000
        timeout = get_stale_timeout(session, "gfs")
        assert timeout == 4000

    @patch("engine.workers.model_worker.get_model_config")
    def test_processes_new_run(self, mock_config, seeded_session):
        """Test processing a new model run."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,  # 0 days = just fxx=0
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        client = self._mock_herbie_client()
        run_dt = datetime(2024, 1, 1, 0, 0)

        result = process_model_run(seeded_session, client, "gfs", run_dt)

        # Should process all 3 seeded resorts
        assert result == 3

        # Model run should be marked completed
        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "completed"
        assert model_run.resorts_processed == 3

        # Job history should be recorded
        job = seeded_session.query(JobHistory).first()
        assert job.status == "completed"
        assert job.job_type == "model_run"

    @patch("engine.workers.model_worker.get_model_config")
    def test_handles_extraction_failure(self, mock_config, seeded_session):
        """Test handling when batch extraction raises an exception."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        client = MagicMock()
        client.extract_all_hours_batch.side_effect = Exception("Download failed")

        with pytest.raises(Exception, match="Download failed"):
            process_model_run(
                seeded_session, client, "gfs", datetime(2024, 1, 1)
            )

        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "failed"

    @patch("engine.workers.model_worker.get_model_config")
    def test_handles_no_available_hours(self, mock_config, seeded_session):
        """Test handling when batch returns no available hours."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        client = MagicMock()
        client.extract_all_hours_batch.return_value = ([], {})

        with pytest.raises(Exception, match="No forecast hours"):
            process_model_run(
                seeded_session, client, "gfs", datetime(2024, 1, 1)
            )

        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "failed"

    @patch("engine.workers.model_worker.get_model_config")
    def test_partial_hour_availability(self, mock_config, seeded_session):
        """Test that partial hours still produce valid results."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="hrrr", api_model="", display_name="HRRR",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.03, description="Test",
            herbie_model="hrrr", herbie_product="sfc",
            update_interval_hours=1,
        )

        point_data = [
            {
                "temperature": 268.15,
                "precipitation": 0.0,
                "snowfall": 0.0,
                "wind_u": 5.0,
                "wind_v": 3.0,
                "wind_gusts": 12.0,
                "freezing_level": 2500.0,
            }
        ] * 3

        # Only fxx=0 available out of requested [0]
        client = self._mock_herbie_client(
            batch_results={0: point_data},
            available_fxx=[0],
        )

        result = process_model_run(
            seeded_session, client, "hrrr", datetime(2024, 1, 1)
        )
        assert result == 3

        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "completed"

    def test_no_resorts_raises(self, session):
        """Test that missing resorts raises error."""
        client = self._mock_herbie_client()
        # Empty DB with no resorts — need to create ModelRun first
        with pytest.raises(Exception):
            process_model_run(session, client, "gfs", datetime(2024, 1, 1))

    @patch("engine.workers.model_worker.get_model_config")
    def test_all_null_data_raises_error(self, mock_config, seeded_session):
        """Test that all-null forecast data marks run as failed."""
        from weather.config.models import ModelConfig
        mock_config.return_value = ModelConfig(
            model_id="gfs", api_model="gfs_seamless", display_name="GFS",
            provider="NOAA", max_forecast_days=0,
            resolution_degrees=0.25, description="Test",
            herbie_model="gfs", herbie_product="atmos.25",
        )

        # All values are None — simulates broken extraction
        all_null_data = [
            {
                "temperature": None,
                "precipitation": None,
                "snowfall": None,
                "wind_u": None,
                "wind_v": None,
                "wind_gusts": None,
                "freezing_level": None,
            }
        ] * 3  # 3 resorts

        client = self._mock_herbie_client(
            batch_results={0: all_null_data},
            available_fxx=[0],
        )

        with pytest.raises(ValueError, match="All forecast data null"):
            process_model_run(
                seeded_session, client, "gfs", datetime(2024, 1, 1)
            )

        model_run = seeded_session.query(ModelRun).first()
        assert model_run.status == "failed"


class TestBlendWorker:
    """Tests for blend_worker functions."""

    def test_compute_resort_blend_no_data(self, session):
        """Test blend with no forecast data returns False."""
        from engine.workers.blend_worker import compute_resort_blend
        result = compute_resort_blend(session, "jackson-hole")
        assert result is False

    def test_compute_resort_blend_with_data(self, session, sample_forecast_dict):
        """Test blend with forecast data."""
        from engine.services.forecast_service import upsert_forecast
        from engine.workers.blend_worker import compute_resort_blend

        run_dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

        # Add forecasts for a couple of models
        for model in ["gfs", "ifs"]:
            upsert_forecast(session, "jackson-hole", model, "summit", sample_forecast_dict, run_dt)
        session.commit()

        result = compute_resort_blend(session, "jackson-hole", "summit")
        assert result is True

        # Verify blend was stored
        from db.models import BlendForecast
        blend = session.query(BlendForecast).filter_by(
            resort_slug="jackson-hole", elevation_type="summit"
        ).first()
        assert blend is not None
        assert "gfs" in blend.source_model_runs
