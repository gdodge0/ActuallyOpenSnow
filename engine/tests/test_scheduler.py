"""Tests for scheduler fallback logic."""

from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

from engine.scheduler import _bootstrap_model, bootstrap_data, process_with_fallback


class TestProcessWithFallback:
    """Tests for process_with_fallback()."""

    @patch("engine.scheduler.process_model_run")
    @patch("engine.scheduler.get_model_config")
    def test_success_on_first_candidate(self, mock_get_config, mock_process):
        """Test that first candidate run succeeds without fallback."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_candidate_run_dts.return_value = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 0, 0),
        ]

        mock_process.return_value = 70
        mock_session = MagicMock()

        result = process_with_fallback(mock_session, mock_client, "gfs")

        assert result == 70
        mock_process.assert_called_once_with(
            mock_session, mock_client, "gfs", datetime(2024, 1, 1, 12, 0)
        )

    @patch("engine.scheduler.process_model_run")
    @patch("engine.scheduler.get_model_config")
    def test_fallback_on_valueerror(self, mock_get_config, mock_process):
        """Test that ValueError triggers fallback to previous run."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_candidate_run_dts.return_value = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 0, 0),
        ]

        # First call fails, second succeeds
        mock_process.side_effect = [
            ValueError("No forecast hours extracted"),
            50,
        ]
        mock_session = MagicMock()

        result = process_with_fallback(mock_session, mock_client, "ifs")

        assert result == 50
        assert mock_process.call_count == 2
        # Second call should use the previous run_dt
        mock_process.assert_called_with(
            mock_session, mock_client, "ifs", datetime(2024, 1, 1, 0, 0)
        )

    @patch("engine.scheduler.process_model_run")
    @patch("engine.scheduler.get_model_config")
    def test_no_fallback_on_non_valueerror(self, mock_get_config, mock_process):
        """Test that non-ValueError exceptions propagate immediately."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_candidate_run_dts.return_value = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 0, 0),
        ]

        mock_process.side_effect = RuntimeError("DB connection lost")
        mock_session = MagicMock()

        with pytest.raises(RuntimeError, match="DB connection lost"):
            process_with_fallback(mock_session, mock_client, "gfs")

        # Should have only tried once (no fallback for non-ValueError)
        mock_process.assert_called_once()

    @patch("engine.scheduler.process_model_run")
    @patch("engine.scheduler.get_model_config")
    def test_all_candidates_fail_returns_zero(self, mock_get_config, mock_process):
        """Test that if all candidates fail with ValueError, returns 0."""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_candidate_run_dts.return_value = [
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 0, 0),
        ]

        mock_process.side_effect = ValueError("No data")
        mock_session = MagicMock()

        result = process_with_fallback(mock_session, mock_client, "aifs")

        assert result == 0
        assert mock_process.call_count == 2


class TestBootstrapModel:
    """Tests for _bootstrap_model()."""

    @patch("engine.scheduler.process_with_fallback")
    def test_returns_model_id_and_count(self, mock_process):
        """Test successful model processing returns (model_id, count)."""
        mock_process.return_value = 70
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        result = _bootstrap_model(mock_factory, MagicMock(), "gfs")

        assert result == ("gfs", 70)
        mock_session.close.assert_called_once()

    @patch("engine.scheduler.process_with_fallback")
    def test_catches_exception_returns_zero(self, mock_process):
        """Test that exceptions are caught and (model_id, 0) is returned."""
        mock_process.side_effect = RuntimeError("DB error")
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)

        result = _bootstrap_model(mock_factory, MagicMock(), "hrrr")

        assert result == ("hrrr", 0)
        mock_session.close.assert_called_once()


class TestBootstrapData:
    """Tests for bootstrap_data() parallel processing."""

    def _make_session_factory(self):
        """Create a mock session factory that returns fresh mocks."""
        sessions = []

        def factory():
            s = MagicMock()
            sessions.append(s)
            return s

        return factory, sessions

    @patch("engine.scheduler.compute_all_blends")
    @patch("engine.scheduler._bootstrap_model")
    @patch("engine.scheduler.MODEL_SCHEDULES", {"gfs": 360, "hrrr": 60, "ifs": 720})
    @patch("engine.scheduler.seed_resorts")
    def test_processes_models_in_parallel(self, mock_seed, mock_bootstrap, mock_blend):
        """Test that models without completed runs are submitted to ThreadPoolExecutor."""
        mock_bootstrap.side_effect = lambda sf, hc, mid: (mid, 70)

        factory, sessions = self._make_session_factory()

        # Mock query chain: no resorts, no completed runs for any model
        for i in range(10):
            s = factory()
            # .query().count() for resort check
            s.query.return_value.count.return_value = 0
            # .query().filter_by().first() for model run check
            s.query.return_value.filter_by.return_value.first.return_value = None

        # Reset factory to produce fresh sessions
        factory, sessions = self._make_session_factory()

        mock_session = MagicMock()
        # Resort count = 5 (skip seeding), no completed runs
        mock_session.query.return_value.count.return_value = 5
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # Post-parallel session for blend check
        mock_blend_session = MagicMock()
        mock_blend_session.query.return_value.filter_by.return_value.count.return_value = 3

        call_count = [0]
        mock_factory = MagicMock()

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_session
            return mock_blend_session

        mock_factory.side_effect = side_effect

        with patch("engine.scheduler.ThreadPoolExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor_cls.return_value.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor_cls.return_value.__exit__ = MagicMock(return_value=False)

            # Create mock futures that return results
            mock_futures = {}
            for mid in ["gfs", "hrrr", "ifs"]:
                f = MagicMock()
                f.result.return_value = (mid, 70)
                mock_futures[f] = mid

            mock_executor.submit.side_effect = list(mock_futures.keys())

            with patch("engine.scheduler.as_completed", return_value=list(mock_futures.keys())):
                bootstrap_data(mock_factory, MagicMock())

            # All 3 models should be submitted
            assert mock_executor.submit.call_count == 3

    @patch("engine.scheduler.compute_all_blends")
    @patch("engine.scheduler._bootstrap_model")
    @patch("engine.scheduler.MODEL_SCHEDULES", {"gfs": 360, "hrrr": 60})
    def test_skips_completed_models(self, mock_bootstrap, mock_blend):
        """Test that models with completed runs are not submitted."""
        mock_session = MagicMock()
        completed_run = MagicMock()

        # All models have completed runs
        mock_session.query.return_value.count.return_value = 5
        mock_session.query.return_value.filter_by.return_value.first.return_value = completed_run

        # Blend session
        mock_blend_session = MagicMock()
        mock_blend_session.query.return_value.filter_by.return_value.count.return_value = 2

        call_count = [0]
        mock_factory = MagicMock()

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_session
            return mock_blend_session

        mock_factory.side_effect = side_effect

        bootstrap_data(mock_factory, MagicMock())

        # _bootstrap_model should never be called since all models are completed
        mock_bootstrap.assert_not_called()

    @patch("engine.scheduler.compute_all_blends")
    @patch("engine.scheduler._bootstrap_model")
    @patch("engine.scheduler.MODEL_SCHEDULES", {"gfs": 360, "hrrr": 60})
    def test_computes_blends_after_all_complete(self, mock_bootstrap, mock_blend):
        """Test that compute_all_blends is called after all parallel work finishes."""
        mock_session = MagicMock()
        mock_session.query.return_value.count.return_value = 5
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        mock_blend_session = MagicMock()
        mock_blend_session.query.return_value.filter_by.return_value.count.return_value = 2

        call_count = [0]
        mock_factory = MagicMock()

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_session
            return mock_blend_session

        mock_factory.side_effect = side_effect

        with patch("engine.scheduler.ThreadPoolExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor_cls.return_value.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor_cls.return_value.__exit__ = MagicMock(return_value=False)

            futures = []
            for mid in ["gfs", "hrrr"]:
                f = MagicMock()
                f.result.return_value = (mid, 70)
                futures.append(f)

            mock_executor.submit.side_effect = futures

            with patch("engine.scheduler.as_completed", return_value=futures):
                bootstrap_data(mock_factory, MagicMock())

        mock_blend.assert_called_once_with(mock_blend_session)

    @patch("engine.scheduler.compute_all_blends")
    @patch("engine.scheduler._bootstrap_model")
    @patch("engine.scheduler.MODEL_SCHEDULES", {"gfs": 360, "hrrr": 60, "ifs": 720})
    def test_individual_failure_doesnt_block_others(self, mock_bootstrap, mock_blend):
        """Test that one model failing doesn't prevent others from completing."""
        mock_session = MagicMock()
        mock_session.query.return_value.count.return_value = 5
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        mock_blend_session = MagicMock()
        mock_blend_session.query.return_value.filter_by.return_value.count.return_value = 2

        call_count = [0]
        mock_factory = MagicMock()

        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_session
            return mock_blend_session

        mock_factory.side_effect = side_effect

        with patch("engine.scheduler.ThreadPoolExecutor") as mock_executor_cls:
            mock_executor = MagicMock()
            mock_executor_cls.return_value.__enter__ = MagicMock(return_value=mock_executor)
            mock_executor_cls.return_value.__exit__ = MagicMock(return_value=False)

            # gfs fails (returns 0), hrrr and ifs succeed
            futures = []
            results = [("gfs", 0), ("hrrr", 70), ("ifs", 50)]
            for mid, count in results:
                f = MagicMock()
                f.result.return_value = (mid, count)
                futures.append(f)

            mock_executor.submit.side_effect = futures

            with patch("engine.scheduler.as_completed", return_value=futures):
                bootstrap_data(mock_factory, MagicMock())

        # All 3 models should have been submitted
        assert mock_executor.submit.call_count == 3
        # Blends should still be computed
        mock_blend.assert_called_once()
