"""Phase 7 — Security hardening tests.

Tests security headers, X-Request-ID, and body/URL size guards.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scope(
    path: str = "/api/v1/health",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 9000),
    }


async def _run_middleware(scope, extra_headers=None):
    """Run SecurityMiddleware and collect send events."""
    from app.core.middleware import SecurityMiddleware

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityMiddleware(app)
    events: list[dict] = []

    async def capture(event):
        events.append(event)

    receive = AsyncMock(return_value={"type": "http.disconnect"})
    await middleware(scope, receive, capture)
    return events


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_headers_present():
    events = await _run_middleware(_make_scope())
    start = next(e for e in events if e.get("type") == "http.response.start")
    headers = {k.lower(): v for k, v in start["headers"]}

    assert headers[b"x-content-type-options"] == b"nosniff"
    assert headers[b"x-frame-options"] == b"DENY"
    assert b"max-age" in headers[b"strict-transport-security"]
    assert headers[b"x-xss-protection"] == b"1; mode=block"
    assert headers[b"referrer-policy"] == b"strict-origin-when-cross-origin"
    assert headers[b"x-api-version"] == b"v1"


@pytest.mark.asyncio
async def test_request_id_present_on_response():
    events = await _run_middleware(_make_scope())
    start = next(e for e in events if e.get("type") == "http.response.start")
    headers = {k.lower(): v for k, v in start["headers"]}
    assert b"x-request-id" in headers
    assert len(headers[b"x-request-id"]) == 32  # UUID hex without dashes


@pytest.mark.asyncio
async def test_request_id_echoed_from_client():
    """If client sends X-Request-ID it should be echoed back."""
    scope = _make_scope(
        headers=[(b"x-request-id", b"my-custom-id-abc")]
    )
    events = await _run_middleware(scope)
    start = next(e for e in events if e.get("type") == "http.response.start")
    headers = {k.lower(): v for k, v in start["headers"]}
    assert headers[b"x-request-id"] == b"my-custom-id-abc"


@pytest.mark.asyncio
async def test_request_id_present_on_every_response():
    """Every response must carry X-Request-ID (run multiple times)."""
    for _ in range(5):
        events = await _run_middleware(_make_scope())
        start = next(e for e in events if e.get("type") == "http.response.start")
        headers = {k.lower(): v for k, v in start["headers"]}
        assert b"x-request-id" in headers


# ---------------------------------------------------------------------------
# Body size guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_body_too_large_returns_413():
    from app.core.middleware import SecurityMiddleware

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityMiddleware(app)
    events: list[dict] = []

    async def capture(event):
        events.append(event)

    scope = _make_scope(
        method="POST",
        headers=[(b"content-length", b"2000000")],  # 2 MB > 1 MB limit
    )
    receive = AsyncMock(return_value={"type": "http.disconnect"})
    await middleware(scope, receive, capture)

    start = next(e for e in events if e.get("type") == "http.response.start")
    assert start["status"] == 413


@pytest.mark.asyncio
async def test_url_too_long_returns_414():
    from app.core.middleware import SecurityMiddleware

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityMiddleware(app)
    events: list[dict] = []

    async def capture(event):
        events.append(event)

    # Build a scope with a very long URL
    long_path = "/api/v1/devices/" + "x" * 3000
    scope = {
        "type": "http",
        "method": "GET",
        "path": long_path,
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 9000),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
    }
    receive = AsyncMock(return_value={"type": "http.disconnect"})
    await middleware(scope, receive, capture)

    start = next(e for e in events if e.get("type") == "http.response.start")
    assert start["status"] == 414
