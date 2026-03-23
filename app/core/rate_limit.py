"""Redis-based sliding-window rate-limiter middleware.

Route groups and limits (requests per 60-second window):
  - Auth (login / register / refresh):  10 req/min  keyed by client IP
  - Device endpoints (telemetry / edge): 60 req/min  keyed by device-token fingerprint
  - Webhooks / OTA:                      30 req/min  keyed by user_id (JWT sub)
  - API standard (all others):          120 req/min  keyed by user_id (JWT sub)

Routes listed in _WHITELIST_PREFIXES bypass rate-limiting completely.

When Redis is unavailable the middleware degrades gracefully and allows all
requests through (fail-open).
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Callable, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger("uvicorn.error")

_WHITELIST_PREFIXES = (
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi",
)

# (path_prefix, limit_per_min, key_type)
# key_type: "ip" | "user_id" | "device_uid"
_ROUTE_RULES: list[Tuple[str, int, str]] = [
    ("/api/v1/auth/login", 10, "ip"),
    ("/api/v1/auth/register", 10, "ip"),
    ("/api/v1/auth/refresh", 10, "ip"),
    ("/api/v1/telemetry", 60, "device_uid"),
    ("/api/v1/edge", 60, "device_uid"),
    ("/api/v1/webhooks", 30, "user_id"),
    ("/api/v1/ota", 30, "user_id"),
]
_DEFAULT_LIMIT = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _jwt_sub(request: Request) -> Optional[str]:
    """Extract 'sub' from Bearer token without full DB validation."""
    try:
        from jose import jwt as _jwt
        from app.core.security import SECRET_KEY, ALGORITHM, ISSUER

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer=ISSUER)
        return payload.get("sub")
    except Exception:
        return None


def _device_fingerprint(request: Request) -> Optional[str]:
    """Return a short fingerprint of the device token (for rate-limit key only)."""
    token = request.headers.get("X-Device-Token")
    if not token:
        return None
    return hashlib.sha256(token.encode()).hexdigest()[:16]


async def _sliding_window(
    redis,
    key: str,
    limit: int,
    window: int = 60,
) -> Tuple[bool, int]:
    """Sliding-window counter via sorted set.

    Returns (allowed, retry_after_seconds).
    If the request would exceed the limit the entry is NOT added to the set.
    """
    now = time.time()
    cutoff = now - window
    pipe = redis.pipeline()
    # Remove timestamps outside the window
    pipe.zremrangebyscore(key, "-inf", cutoff)
    # Count current window entries
    pipe.zcard(key)
    # Set TTL so keys don't linger forever
    pipe.expire(key, window + 1)
    results = await pipe.execute()
    current_count = results[1]

    if current_count >= limit:
        retry_after = int(window - (now - cutoff)) + 1
        return False, max(1, retry_after)

    # Add current request timestamp (unique score = timestamp, member = timestamp str)
    await redis.zadd(key, {f"{now:.6f}": now})
    return True, 0


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in _WHITELIST_PREFIXES):
            return await call_next(request)

        redis = get_redis()
        if redis is None:
            return await call_next(request)

        # Determine limit and key type for this route
        limit = _DEFAULT_LIMIT
        key_type = "user_id"
        for prefix, lim, ktype in _ROUTE_RULES:
            if path.startswith(prefix):
                limit, key_type = lim, ktype
                break

        # Resolve identifier
        if key_type == "ip":
            identifier: str = _client_ip(request)
        elif key_type == "device_uid":
            identifier = _device_fingerprint(request) or _client_ip(request)
        else:
            identifier = _jwt_sub(request) or _client_ip(request)

        redis_key = f"hubex:rl:{key_type}:{identifier}"

        try:
            allowed, retry_after = await _sliding_window(redis, redis_key, limit)
        except Exception as exc:
            logger.warning("rate_limit: Redis error (%s), allowing request", exc)
            return await call_next(request)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate_limited"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
