"""Redis connection singleton for HUBEX backend.

Returns None if Redis is not configured or not reachable — all callers must
handle None gracefully (rate-limiting and caching degrade to allow-all/no-cache).
"""
from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

_redis: Optional[aioredis.Redis] = None


def get_redis() -> Optional[aioredis.Redis]:
    """Return the shared Redis client, or None if not configured/available."""
    return _redis


async def init_redis() -> None:
    """Initialize the Redis connection pool. Called from lifespan startup."""
    global _redis
    url = settings.redis_url
    if not url:
        logger.warning("redis_client: HUBEX_REDIS_URL not set — Redis features disabled")
        return
    try:
        client = aioredis.from_url(
            url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        await client.ping()
        _redis = client
        logger.info("redis_client: connected to Redis")
    except Exception as exc:
        logger.warning("redis_client: could not connect (%s) — Redis features disabled", exc)
        _redis = None


async def close_redis() -> None:
    """Close the Redis connection pool. Called from lifespan shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
