"""Tests for GRIB2 cache management."""

import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from engine.services.grib_service import cleanup_old_files, get_cache_size_bytes


class TestCleanupOldFiles:
    """Tests for GRIB2 cache cleanup."""

    def test_cleanup_empty_dir(self, tmp_path):
        with patch("engine.services.grib_service.get_cache_dir", return_value=tmp_path):
            removed = cleanup_old_files()
        assert removed == 0

    def test_cleanup_removes_old_files(self, tmp_path):
        # Create some old .grib2 files
        old_file = tmp_path / "hrrr_old.grib2"
        old_file.write_text("data")
        # Set modification time to 48 hours ago
        old_time = time.time() - 48 * 3600
        os.utime(old_file, (old_time, old_time))

        with patch("engine.services.grib_service.get_cache_dir", return_value=tmp_path):
            removed = cleanup_old_files()

        assert removed == 1
        assert not old_file.exists()

    def test_cleanup_keeps_recent_files(self, tmp_path):
        # Create a recent file
        recent_file = tmp_path / "gfs_recent.grib2"
        recent_file.write_text("data")

        with patch("engine.services.grib_service.get_cache_dir", return_value=tmp_path):
            removed = cleanup_old_files()

        assert removed == 0
        assert recent_file.exists()

    def test_cleanup_model_specific(self, tmp_path):
        # Create old files for different models
        hrrr_file = tmp_path / "hrrr_old.grib2"
        hrrr_file.write_text("data")
        gfs_file = tmp_path / "gfs_old.grib2"
        gfs_file.write_text("data")

        old_time = time.time() - 100 * 3600
        os.utime(hrrr_file, (old_time, old_time))
        os.utime(gfs_file, (old_time, old_time))

        with patch("engine.services.grib_service.get_cache_dir", return_value=tmp_path):
            removed = cleanup_old_files(model_id="hrrr")

        assert removed == 1
        assert not hrrr_file.exists()
        assert gfs_file.exists()


class TestGetCacheSize:
    """Tests for cache size calculation."""

    def test_empty_dir(self, tmp_path):
        with patch("engine.services.grib_service.get_cache_dir", return_value=tmp_path):
            size = get_cache_size_bytes()
        assert size == 0

    def test_with_files(self, tmp_path):
        (tmp_path / "test.grib2").write_bytes(b"x" * 1024)
        with patch("engine.services.grib_service.get_cache_dir", return_value=tmp_path):
            size = get_cache_size_bytes()
        assert size == 1024
