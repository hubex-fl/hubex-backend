"""Phase 7 — JWT Refresh Token flow + Brute-Force lockout tests."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.v1.auth import router as auth_router
from app.db.base import Base
from app.db.models.events import EventV1
from app.db.models.orgs import Organization, OrganizationUser
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

def _create_tables(conn):
    Base.metadata.create_all(
        conn,
        tables=[
            User.__table__,
            Organization.__table__,
            OrganizationUser.__table__,
            RefreshToken.__table__,
            EventV1.__table__,
        ],
    )


async def _mk_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(_create_tables)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, Session


async def _mk_app(Session):
    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(auth_router, prefix="/api/v1")
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_user(client, email="user@example.com", password="pass1234"):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )


async def _login(client, email="user@example.com", password="pass1234"):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# Refresh token tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_returns_refresh_token():
    """Login response includes a refresh_token field."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    # Disable brute-force Redis calls for this test
    with patch("app.api.v1.auth._get_redis", return_value=None):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register_user(client)
            resp = await _login(client)

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] is not None


@pytest.mark.asyncio
async def test_register_returns_refresh_token():
    """Register response also includes a refresh_token."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    with patch("app.api.v1.auth._get_redis", return_value=None):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _register_user(client)

    assert resp.status_code == 200
    data = resp.json()
    assert "refresh_token" in data
    assert data["refresh_token"] is not None


@pytest.mark.asyncio
async def test_refresh_token_issues_new_tokens():
    """POST /refresh with a valid token returns new access + refresh tokens."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    with patch("app.api.v1.auth._get_redis", return_value=None):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register_user(client)
            login_resp = await _login(client)
            old_refresh = login_resp.json()["refresh_token"]

            refresh_resp = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": old_refresh},
            )

    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # New refresh token should be different from the old one
    assert data["refresh_token"] != old_refresh


@pytest.mark.asyncio
async def test_refresh_token_rotation_invalidates_old():
    """After refresh, using the old refresh token returns 401."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    with patch("app.api.v1.auth._get_redis", return_value=None):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register_user(client)
            login_resp = await _login(client)
            old_refresh = login_resp.json()["refresh_token"]

            # First refresh — OK
            await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

            # Second use of old token — must fail
            resp2 = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
            )

    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401():
    """Garbage refresh token → 401."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "totally-invalid-garbage"}
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_refresh_token_returns_401():
    """An expired refresh token must be rejected."""
    _, Session = await _mk_session()

    # Directly insert an expired token
    async with Session() as db:
        user = User(email="e@test.com", password_hash="x")
        db.add(user)
        await db.flush()
        raw = "expiredtokenabc123"
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expired_rt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(expired_rt)
        await db.commit()

    app = await _mk_app(Session)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": raw}
        )

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Brute-force lockout tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_brute_force_lockout_after_5_failures():
    """After 5 failed logins the IP should be locked out (429)."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    # Track Redis state in memory
    counters: dict[str, int] = {}
    locks: dict[str, str] = {}

    async def mock_get(key):
        if key in locks:
            return locks[key]
        return None

    async def mock_incr(key):
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    async def mock_expire(key, ttl):
        pass

    async def mock_setex(key, ttl, val):
        locks[key] = val

    async def mock_ttl(key):
        return 900

    async def mock_delete(*keys):
        for k in keys:
            counters.pop(k, None)
            locks.pop(k, None)

    mock_redis = AsyncMock()
    mock_redis.get = mock_get
    mock_redis.incr = mock_incr
    mock_redis.expire = mock_expire
    mock_redis.setex = mock_setex
    mock_redis.ttl = mock_ttl
    mock_redis.delete = mock_delete

    with patch("app.api.v1.auth._get_redis", return_value=mock_redis):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Register a user so the endpoint is reachable
            await _register_user(client)

            # 5 failed attempts
            for _ in range(5):
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "user@example.com", "password": "WRONG"},
                )
            # 6th attempt → should be 429 (locked)
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "WRONG"},
            )

    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_successful_login_clears_brute_force_counter():
    """A successful login clears the failed-attempt counter."""
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    deleted_keys: list = []
    counters: dict[str, int] = {}

    async def mock_get(key):
        return None  # not locked

    async def mock_incr(key):
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    async def mock_expire(key, ttl):
        pass

    async def mock_setex(key, ttl, val):
        pass

    async def mock_delete(*keys):
        deleted_keys.extend(keys)

    mock_redis = AsyncMock()
    mock_redis.get = mock_get
    mock_redis.incr = mock_incr
    mock_redis.expire = mock_expire
    mock_redis.setex = mock_setex
    mock_redis.delete = mock_delete

    with patch("app.api.v1.auth._get_redis", return_value=mock_redis):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _register_user(client)
            resp = await _login(client)

    assert resp.status_code == 200
    # delete should have been called (to clear counter + lock keys)
    assert len(deleted_keys) > 0
