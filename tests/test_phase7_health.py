"""Phase 7 — Health and Readiness endpoint tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Build a minimal app with /health and /ready for testing
# ---------------------------------------------------------------------------

def _build_app():
    """Re-create just the health endpoints from main without workers."""
    from app.db.session import AsyncSessionLocal

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/ready")
    async def ready():
        checks: dict[str, str] = {}
        overall = "ok"

        try:
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "error"
            overall = "degraded"

        from app.core.redis_client import get_redis
        redis = get_redis()
        if redis is None:
            checks["redis"] = "disabled"
        else:
            try:
                await redis.ping()
                checks["redis"] = "ok"
            except Exception:
                checks["redis"] = "error"
                overall = "degraded"

        status_code = 200 if overall == "ok" else 503
        return JSONResponse(
            status_code=status_code,
            content={"status": overall, "checks": checks, "version": "0.1.0"},
        )

    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_returns_200():
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_ready_degraded_when_db_down():
    """When DB is unavailable, /ready returns 503 degraded."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.db.session.AsyncSessionLocal", return_value=mock_ctx),
        patch("app.core.redis_client.get_redis", return_value=None),
    ):
        app = _build_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["checks"]["db"] == "error"


@pytest.mark.asyncio
async def test_ready_redis_disabled_when_none():
    """When Redis is not configured, /ready shows redis=disabled."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.db.session.AsyncSessionLocal", return_value=mock_session),
        patch("app.core.redis_client.get_redis", return_value=None),
    ):
        app = _build_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")

    data = resp.json()
    assert data["checks"]["redis"] == "disabled"


@pytest.mark.asyncio
async def test_ready_ok_when_db_and_redis_up():
    """When both DB and Redis are healthy, /ready returns 200 ok."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()

    with (
        patch("app.db.session.AsyncSessionLocal", return_value=mock_session),
        patch("app.core.redis_client.get_redis", return_value=mock_redis),
    ):
        app = _build_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["checks"]["db"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_no_db_check():
    """Liveness /health must succeed even when DB is unavailable."""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)

    # Even with DB patches, /health should succeed
    with patch("app.db.session.AsyncSessionLocal", side_effect=Exception("DB down")):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")

    assert resp.status_code == 200
