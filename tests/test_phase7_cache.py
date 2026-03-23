"""Phase 7 — Response-cache middleware tests.

All tests mock Redis so no real Redis instance is required.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scope(path: str = "/api/v1/devices", method: str = "GET") -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_disabled_passthrough():
    """CacheMiddleware is a no-op when cache_enabled=False."""
    from app.core.cache import CacheMiddleware

    called = []

    async def app(scope, receive, send):
        called.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    middleware = CacheMiddleware(app)

    with patch("app.core.cache.settings") as mock_settings:
        mock_settings.cache_enabled = False
        scope = _make_scope()
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        send = AsyncMock()
        await middleware(scope, receive, send)

    assert called


@pytest.mark.asyncio
async def test_cache_miss_stores_response():
    """On a cache miss the response body is stored in Redis."""
    from app.core.cache import CacheMiddleware

    body_bytes = b'{"devices": []}'
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # cache miss
    mock_redis.setex = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[])

    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": body_bytes})

    middleware = CacheMiddleware(app)

    responses: list[dict] = []

    async def capture_send(event):
        responses.append(event)

    with (
        patch("app.core.cache.settings") as mock_settings,
        patch("app.core.cache.get_redis", return_value=mock_redis),
        patch("app.core.cache._org_id_from_request", return_value="99"),
    ):
        mock_settings.cache_enabled = True
        scope = _make_scope("/api/v1/devices")
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        await middleware(scope, receive, capture_send)

    mock_redis.setex.assert_called_once()
    # Response should include X-Cache: MISS
    start = next(e for e in responses if e.get("type") == "http.response.start")
    headers = dict(start["headers"])
    assert headers.get(b"x-cache") == b"MISS"


@pytest.mark.asyncio
async def test_cache_hit_returns_cached():
    """On a cache hit the response comes from Redis without calling the handler."""
    from app.core.cache import CacheMiddleware

    cached_body = b'{"devices": [{"id":1}]}'
    import hashlib
    etag = '"' + hashlib.md5(cached_body).hexdigest() + '"'
    cache_payload = json.dumps({
        "body": cached_body.decode("latin-1"),
        "status_code": 200,
        "headers": {"content-type": "application/json"},
        "media_type": "application/json",
    })

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cache_payload)
    mock_redis.keys = AsyncMock(return_value=[])

    handler_called = []

    async def app(scope, receive, send):
        handler_called.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = CacheMiddleware(app)
    responses: list[dict] = []

    async def capture_send(event):
        responses.append(event)

    with (
        patch("app.core.cache.settings") as mock_settings,
        patch("app.core.cache.get_redis", return_value=mock_redis),
        patch("app.core.cache._org_id_from_request", return_value="99"),
    ):
        mock_settings.cache_enabled = True
        scope = _make_scope("/api/v1/devices")
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        await middleware(scope, receive, capture_send)

    # Handler must NOT have been called
    assert not handler_called
    start = next(e for e in responses if e.get("type") == "http.response.start")
    headers = dict(start["headers"])
    assert headers.get(b"x-cache") == b"HIT"


@pytest.mark.asyncio
async def test_cache_etag_304():
    """If-None-Match matching ETag returns 304 Not Modified."""
    from app.core.cache import CacheMiddleware

    cached_body = b'{"devices": []}'
    import hashlib
    etag = '"' + hashlib.md5(cached_body).hexdigest() + '"'
    cache_payload = json.dumps({
        "body": cached_body.decode("latin-1"),
        "status_code": 200,
        "headers": {"content-type": "application/json"},
        "media_type": "application/json",
    })

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cache_payload)

    async def app(scope, receive, send):
        pass  # should not be called

    middleware = CacheMiddleware(app)
    responses: list[dict] = []

    async def capture_send(event):
        responses.append(event)

    headers_with_etag = [
        (b"if-none-match", etag.encode()),
        (b"authorization", b"Bearer dummy"),
    ]

    with (
        patch("app.core.cache.settings") as mock_settings,
        patch("app.core.cache.get_redis", return_value=mock_redis),
        patch("app.core.cache._org_id_from_request", return_value="99"),
    ):
        mock_settings.cache_enabled = True
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/devices",
            "query_string": b"",
            "headers": headers_with_etag,
            "client": ("127.0.0.1", 12345),
        }
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        await middleware(scope, receive, capture_send)

    start = next(e for e in responses if e.get("type") == "http.response.start")
    assert start["status"] == 304


@pytest.mark.asyncio
async def test_cache_invalidation_on_post():
    """POST to a cached prefix flushes matching cache keys."""
    from app.core.cache import CacheMiddleware

    mock_redis = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[b"hubex:cache:99:/api/v1/devices:abc123"])
    mock_redis.delete = AsyncMock()

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b'{"id":1}'})

    middleware = CacheMiddleware(app)

    with (
        patch("app.core.cache.settings") as mock_settings,
        patch("app.core.cache.get_redis", return_value=mock_redis),
    ):
        mock_settings.cache_enabled = True
        scope = _make_scope("/api/v1/devices", method="POST")
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        send = AsyncMock()
        await middleware(scope, receive, send)

    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_cache_non_cacheable_path_no_store():
    """Non-cached paths are passed through without touching Redis store."""
    from app.core.cache import CacheMiddleware

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[])

    called = []

    async def app(scope, receive, send):
        called.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    middleware = CacheMiddleware(app)

    with (
        patch("app.core.cache.settings") as mock_settings,
        patch("app.core.cache.get_redis", return_value=mock_redis),
    ):
        mock_settings.cache_enabled = True
        scope = _make_scope("/api/v1/users")  # not in cache rules
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        send = AsyncMock()
        await middleware(scope, receive, send)

    # Handler was called
    assert called
    # setex should NOT have been called
    mock_redis.setex.assert_not_called()
