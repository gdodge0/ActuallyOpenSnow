"""Engine configuration."""

from __future__ import annotations

import os


# Database
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/actuallyopensnow"
)

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# GRIB2 cache
GRIB_CACHE_DIR = os.environ.get("GRIB_CACHE_DIR", "/tmp/grib_cache")
GRIB_CACHE_RETENTION_HOURS = {
    "hrrr": 24,
    "gfs": 72,
    "nbm": 48,
    "ifs": 72,
    "aifs": 72,
    "gefs": 72,
    "ecmwf_ens": 72,
}

# Model schedules (cron-like intervals in minutes)
MODEL_SCHEDULES = {
    "hrrr": 60,       # Every 1 hour
    "gfs": 360,       # Every 6 hours
    "nbm": 180,       # Every 3 hours
    "ifs": 720,        # Every 12 hours
    "aifs": 720,       # Every 12 hours
    "gefs": 360,       # Every 6 hours
    "ecmwf_ens": 720,  # Every 12 hours
}

# Blend weights for the pre-computed blend
BLEND_WEIGHTS = {
    "hrrr": float(os.environ.get("BLEND_WEIGHT_HRRR", "3.0")),
    "gfs": float(os.environ.get("BLEND_WEIGHT_GFS", "2.0")),
    "nbm": float(os.environ.get("BLEND_WEIGHT_NBM", "2.0")),
    "ifs": float(os.environ.get("BLEND_WEIGHT_IFS", "2.0")),
    "aifs": float(os.environ.get("BLEND_WEIGHT_AIFS", "2.0")),
    "gefs": float(os.environ.get("BLEND_WEIGHT_GEFS", "1.0")),
    "ecmwf_ens": float(os.environ.get("BLEND_WEIGHT_ECMWF_ENS", "1.0")),
}

# Processing
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "4"))
BOOTSTRAP_MAX_WORKERS = int(os.environ.get("BOOTSTRAP_MAX_WORKERS", "7"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "20"))  # Resorts per batch

# Redis lock settings
LOCK_TIMEOUT = 600  # 10 minutes
LOCK_PREFIX = "engine:lock:"
