"""Phase 7 — Rate-limiting tests.

All tests mock Redis so no real Redis instance is required.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.rate_limit import RateLimitMiddleware, _sliding_window


# ---------------------------------------------------------------------------
# Unit: sliding window algorithm
# ---------------------------------------------------------------------------

def _make_pipe(count: int):
    """Build a synchronous MagicMock pipeline with async execute()."""
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock()
    pipe.zcard = MagicMock()
    pipe.expire = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, count, 1])
    return pipe


@pytest.mark.asyncio
async def test_sliding_window_allows_within_limit():
    redis = MagicMock()
    redis.pipeline.return_value = _make_pipe(count=5)
    redis.zadd = AsyncMock()

    allowed, retry_after = await _sliding_window(redis, "hubex:rl:user_id:42", limit=10)
    assert allowed is True
    assert retry_after == 0


@pytest.mark.asyncio
async def test_sliding_window_blocks_at_limit():
    redis = MagicMock()
    redis.pipeline.return_value = _make_pipe(count=10)  # count == limit

    allowed, retry_after = await _sliding_window(redis, "hubex:rl:user_id:42", limit=10)
    assert allowed is False
    assert retry_after >= 1


# ---------------------------------------------------------------------------
# Integration: middleware with mocked Redis
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


@pytest.mark.asyncio
async def test_rate_limit_middleware_allows_when_disabled():
    """Middleware is a no-op when rate_limit_enabled=False."""
    called = []

    async def app(scope, receive, send):
        called.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RateLimitMiddleware(app)

    with patch("app.core.rate_limit.settings") as mock_settings:
        mock_settings.rate_limit_enabled = False
        scope = _make_scope()
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        send = AsyncMock()
        await middleware(scope, receive, send)

    assert called


@pytest.mark.asyncio
async def test_rate_limit_middleware_passes_when_redis_none():
    """No Redis → allow all requests."""
    called = []

    async def app(scope, receive, send):
        called.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RateLimitMiddleware(app)

    with (
        patch("app.core.rate_limit.settings") as mock_settings,
        patch("app.core.rate_limit.get_redis", return_value=None),
    ):
        mock_settings.rate_limit_enabled = True
        scope = _make_scope()
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        send = AsyncMock()
        await middleware(scope, receive, send)

    assert called


@pytest.mark.asyncio
async def test_rate_limit_429_with_retry_after():
    """Middleware returns 429 + Retry-After when Redis says limit exceeded."""
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RateLimitMiddleware(app)

    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = _make_pipe(count=120)  # count >= default limit 120

    responses: list[dict] = []

    async def capture_send(event):
        responses.append(event)

    with (
        patch("app.core.rate_limit.settings") as mock_settings,
        patch("app.core.rate_limit.get_redis", return_value=mock_redis),
        patch("app.core.rate_limit._jwt_sub", return_value="user-42"),
    ):
        mock_settings.rate_limit_enabled = True
        scope = _make_scope("/api/v1/devices")
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        await middleware(scope, receive, capture_send)

    start_event = next(e for e in responses if e.get("type") == "http.response.start")
    assert start_event["status"] == 429
    headers = dict(start_event["headers"])
    assert b"retry-after" in headers


@pytest.mark.asyncio
async def test_rate_limit_whitelist_skips_health():
    """Health endpoints are never rate-limited."""
    called = []

    async def app(scope, receive, send):
        called.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RateLimitMiddleware(app)

    mock_redis = MagicMock()
    mock_redis.pipeline.return_value = _make_pipe(count=9999)  # way over limit

    with (
        patch("app.core.rate_limit.settings") as mock_settings,
        patch("app.core.rate_limit.get_redis", return_value=mock_redis),
    ):
        mock_settings.rate_limit_enabled = True
        scope = _make_scope("/health")
        receive = AsyncMock(return_value={"type": "http.disconnect"})
        send = AsyncMock()
        await middleware(scope, receive, send)

    assert called


@pytest.mark.asyncio
async def test_rate_limit_auth_uses_ip_scope():
    """Auth routes key on IP and use limit=10."""
    import app.core.rate_limit as rl_mod

    auth_rules = [r for r in rl_mod._ROUTE_RULES if "/auth/" in r[0]]
    for prefix, limit, key_type in auth_rules:
        assert limit == 10
        assert key_type == "ip"


@pytest.mark.asyncio
async def test_rate_limit_device_scope():
    """Device/telemetry routes use device_uid scope and limit=60."""
    import app.core.rate_limit as rl_mod

    device_rules = [r for r in rl_mod._ROUTE_RULES if "telemetry" in r[0] or "edge" in r[0]]
    for prefix, limit, key_type in device_rules:
        assert limit == 60
        assert key_type == "device_uid"


@pytest.mark.asyncio
async def test_rate_limit_webhook_ota_scope():
    """Webhooks/OTA routes use user_id scope and limit=30."""
    import app.core.rate_limit as rl_mod

    rules = [r for r in rl_mod._ROUTE_RULES if "webhook" in r[0] or "/ota" in r[0]]
    for prefix, limit, key_type in rules:
        assert limit == 30
        assert key_type == "user_id"
