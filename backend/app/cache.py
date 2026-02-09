"""Redis-backed response cache for the backend API."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))  # 5 minutes
CACHE_PREFIX = "backend:cache:"

_redis_client = None


def get_redis():
    """Get or create a Redis client (lazy initialization)."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Caching disabled.")
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> dict[str, Any] | None:
    """Get a cached value.

    Args:
        key: Cache key.

    Returns:
        Cached dict or None.
    """
    client = get_redis()
    if client is None:
        return None

    try:
        data = client.get(f"{CACHE_PREFIX}{key}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache get failed: {e}")

    return None


def cache_set(key: str, value: dict[str, Any], ttl: int | None = None) -> None:
    """Set a cached value.

    Args:
        key: Cache key.
        value: Dict to cache.
        ttl: TTL in seconds. Defaults to CACHE_TTL.
    """
    client = get_redis()
    if client is None:
        return

    try:
        client.setex(
            f"{CACHE_PREFIX}{key}",
            ttl or CACHE_TTL,
            json.dumps(value),
        )
    except Exception as e:
        logger.debug(f"Cache set failed: {e}")


def cache_clear() -> int:
    """Clear all backend cache entries.

    Returns:
        Number of keys cleared.
    """
    client = get_redis()
    if client is None:
        return 0

    try:
        keys = list(client.scan_iter(f"{CACHE_PREFIX}*"))
        if keys:
            return client.delete(*keys)
    except Exception as e:
        logger.debug(f"Cache clear failed: {e}")

    return 0
