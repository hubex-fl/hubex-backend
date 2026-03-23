"""Redis-based response-cache middleware.

Cached endpoints and TTLs:
  GET /api/v1/devices          5 s
  GET /api/v1/entities         5 s
  GET /api/v1/modules         30 s
  GET /api/v1/metrics         10 s
  GET /api/v1/ota/firmware    60 s

Cache key  : hubex:cache:{org_id}:{path}:{query_hash}
ETag       : MD5 of response body; If-None-Match → 304 Not Modified
Invalidation: POST / PUT / PATCH / DELETE on the same resource prefix
              flushes matching cache keys.

Degrades gracefully when Redis is unavailable (no-cache / pass-through).
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger("uvicorn.error")

# (path_prefix, ttl_seconds)
_CACHE_RULES: list[tuple[str, int]] = [
    ("/api/v1/devices", 5),
    ("/api/v1/entities", 5),
    ("/api/v1/modules", 30),
    ("/api/v1/metrics", 10),
    ("/api/v1/ota/firmware", 60),
]

_INVALIDATE_PREFIXES = [
    "/api/v1/devices",
    "/api/v1/entities",
    "/api/v1/modules",
    "/api/v1/metrics",
    "/api/v1/ota",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _org_id_from_request(request: Request) -> str:
    """Extract org_id claim from Bearer token for scoped cache keys."""
    try:
        from jose import jwt as _jwt
        from app.core.security import SECRET_KEY, ALGORITHM, ISSUER

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return "anon"
        token = auth[7:]
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer=ISSUER)
        return str(payload.get("org_id", "anon"))
    except Exception:
        return "anon"


def _cache_ttl(path: str) -> Optional[int]:
    for prefix, ttl in _CACHE_RULES:
        if path.startswith(prefix):
            return ttl
    return None


def _invalidation_prefix(path: str) -> Optional[str]:
    for prefix in _INVALIDATE_PREFIXES:
        if path.startswith(prefix):
            return prefix
    return None


def _build_key(org_id: str, path: str, query: str) -> str:
    qhash = hashlib.md5(query.encode()).hexdigest()[:8]
    return f"hubex:cache:{org_id}:{path}:{qhash}"


def _etag(body: bytes) -> str:
    return '"' + hashlib.md5(body).hexdigest() + '"'


async def _consume_body(response: Response) -> bytes:
    """Drain a streaming response body into bytes."""
    body = b""
    async for chunk in response.body_iterator:  # type: ignore[attr-defined]
        body += chunk if isinstance(chunk, bytes) else chunk.encode("latin-1")
    return body


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class CacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.cache_enabled:
            return await call_next(request)

        redis = get_redis()
        path = request.url.path
        method = request.method.upper()

        # --- Invalidation on write methods ---
        if method in ("POST", "PUT", "PATCH", "DELETE") and redis:
            prefix = _invalidation_prefix(path)
            if prefix:
                try:
                    pattern = f"hubex:cache:*{prefix}*"
                    keys = await redis.keys(pattern)
                    if keys:
                        await redis.delete(*keys)
                except Exception as exc:
                    logger.warning("cache: invalidation error (%s)", exc)

        # Only cache GET requests when Redis is available
        if method != "GET" or redis is None:
            return await call_next(request)

        ttl = _cache_ttl(path)
        if ttl is None:
            return await call_next(request)

        org_id = _org_id_from_request(request)
        cache_key = _build_key(org_id, path, str(request.url.query))

        # --- Cache read ---
        try:
            cached_raw = await redis.get(cache_key)
            if cached_raw:
                data = json.loads(cached_raw)
                body = data["body"].encode("latin-1")
                etag = _etag(body)
                if_none_match = request.headers.get("If-None-Match", "")
                if if_none_match and if_none_match == etag:
                    return Response(status_code=304, headers={"ETag": etag})
                return Response(
                    content=body,
                    status_code=data["status_code"],
                    headers={**data["headers"], "ETag": etag, "X-Cache": "HIT"},
                    media_type=data.get("media_type", "application/json"),
                )
        except Exception as exc:
            logger.warning("cache: read error (%s)", exc)

        # --- Cache miss: call handler ---
        response = await call_next(request)

        if response.status_code == 200:
            try:
                body = await _consume_body(response)
                etag = _etag(body)
                cache_data = json.dumps({
                    "body": body.decode("latin-1"),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                })
                await redis.setex(cache_key, ttl, cache_data)
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers={**dict(response.headers), "ETag": etag, "X-Cache": "MISS"},
                    media_type=response.media_type,
                )
            except Exception as exc:
                logger.warning("cache: write error (%s)", exc)

        return response
