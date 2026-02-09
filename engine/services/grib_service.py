"""GRIB2 disk cache management."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from engine.config import GRIB_CACHE_DIR, GRIB_CACHE_RETENTION_HOURS

logger = logging.getLogger(__name__)


def get_cache_dir() -> Path:
    """Get the GRIB2 cache directory, creating it if needed."""
    cache_dir = Path(GRIB_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_size_bytes() -> int:
    """Get total size of cached GRIB2 files in bytes."""
    cache_dir = get_cache_dir()
    total = 0
    for f in cache_dir.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def cleanup_old_files(model_id: str | None = None) -> int:
    """Remove expired GRIB2 files from the cache.

    Args:
        model_id: Optional model to clean up. If None, cleans all models.

    Returns:
        Number of files removed.
    """
    cache_dir = get_cache_dir()
    now = time.time()
    removed = 0

    for f in cache_dir.rglob("*.grib2"):
        if not f.is_file():
            continue

        # Determine retention based on model ID in path
        retention_hours = 72  # Default
        for mid, hours in GRIB_CACHE_RETENTION_HOURS.items():
            if mid in str(f):
                retention_hours = hours
                break

        if model_id and model_id not in str(f):
            continue

        age_hours = (now - f.stat().st_mtime) / 3600
        if age_hours > retention_hours:
            try:
                f.unlink()
                removed += 1
            except OSError as e:
                logger.warning(f"Failed to remove {f}: {e}")

    if removed > 0:
        logger.info(f"Cleaned up {removed} expired GRIB2 files")

    return removed
