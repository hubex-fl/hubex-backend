from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.v1.pairing import router as pairing_router, legacy_router as pairing_legacy_router
from app.db.base import Base
from app.db.models.device import Device
from app.db.models.pairing import PairingSession, DeviceToken
from app.db.models.user import User
from app.db.models.audit import AuditV1Entry


def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            Device.__table__,
            PairingSession.__table__,
            DeviceToken.__table__,
            User.__table__,
            AuditV1Entry.__table__,
        ],
    )
    # confirm/claim paths reference tasks; create a minimal table for sqlite tests
    conn.exec_driver_sql(
        """
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            client_id INTEGER NOT NULL,
            lease_expires_at DATETIME NULL,
            lease_token VARCHAR(128) NULL,
            status VARCHAR(32) NULL
        )
        """
    )


async def _mk_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_tables(Base.metadata, c))
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, Session


async def _mk_app(Session):
    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI()
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(pairing_router, prefix="/api/v1")
    app.include_router(pairing_legacy_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_device_pairing_hello_creates_session():
    engine, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-1", "firmware_version": "dev", "capabilities": {}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("claimed") is False
    assert data.get("pairing_active") is True
    assert data.get("pairing_code")
    assert data.get("ttl_seconds") is not None

    async with Session() as db:
        ps = (
            await db.execute(
                PairingSession.__table__.select().where(PairingSession.device_uid == "dev-1")
            )
        ).first()
        assert ps is not None

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_device_pairing_hello_idempotent_same_code():
    engine, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    first = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-2"},
    )
    assert first.status_code == 200
    code1 = first.json().get("pairing_code")

    second = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-2"},
    )
    assert second.status_code == 200
    code2 = second.json().get("pairing_code")

    legacy = await client.post(
        "/api/v1/pairing/hello",
        json={"device_uid": "dev-2"},
    )
    assert legacy.status_code == 200
    code3 = legacy.json().get("pairing_code")

    assert code1 and code1 == code2
    assert code2 == code3

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pairing_confirm_returns_device_token_once():
    engine, Session = await _mk_session()

    async with Session() as db:
        user = User(email="u@example.com", password_hash="x", caps=None)
        db.add(user)
        await db.commit()

    async def _get_user():
        async with Session() as db:
            return await db.get(User, 1)

    app = await _mk_app(Session)
    app.dependency_overrides[get_current_user] = _get_user
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    hello = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-3"},
    )
    assert hello.status_code == 200
    pairing_code = hello.json()["pairing_code"]

    claim = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"device_uid": "dev-3", "pairing_code": pairing_code},
    )
    assert claim.status_code == 200

    confirm = await client.post(
        "/api/v1/devices/pairing/confirm",
        json={"device_uid": "dev-3", "pairing_code": pairing_code},
    )
    assert confirm.status_code == 200
    payload = confirm.json()
    assert payload.get("device_token")

    confirm_again = await client.post(
        "/api/v1/devices/pairing/confirm",
        json={"device_uid": "dev-3", "pairing_code": pairing_code},
    )
    assert confirm_again.status_code == 409

    async with Session() as db:
        persisted = await db.get(Device, 1)
        assert persisted is not None
        assert persisted.owner_user_id == 1
        assert persisted.is_claimed is True

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_post_confirm_hello_returns_no_pairing_code():
    engine, Session = await _mk_session()

    async with Session() as db:
        user = User(email="u2@example.com", password_hash="x", caps=None)
        db.add(user)
        await db.commit()

    async def _get_user():
        async with Session() as db:
            return await db.get(User, 1)

    app = await _mk_app(Session)
    app.dependency_overrides[get_current_user] = _get_user
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    hello = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-4"},
    )
    assert hello.status_code == 200
    pairing_code = hello.json()["pairing_code"]

    claim = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"device_uid": "dev-4", "pairing_code": pairing_code},
    )
    assert claim.status_code == 200

    confirm = await client.post(
        "/api/v1/devices/pairing/confirm",
        json={"device_uid": "dev-4", "pairing_code": pairing_code},
    )
    assert confirm.status_code == 200

    post = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-4"},
    )
    assert post.status_code == 200
    data = post.json()
    assert data.get("claimed") is True
    assert data.get("pairing_active") is False
    assert data.get("pairing_code") is None

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pairing_claim_requires_auth():
    engine, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"pairing_code": "NOPE1234"},
    )
    assert res.status_code == 401

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pairing_claim_idempotent_and_audit():
    engine, Session = await _mk_session()

    async with Session() as db:
        user = User(email="claim@example.com", password_hash="x", caps=None)
        db.add(user)
        await db.commit()

    async def _get_user():
        async with Session() as db:
            return await db.get(User, 1)

    app = await _mk_app(Session)
    app.dependency_overrides[get_current_user] = _get_user
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    hello = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-claim"},
    )
    assert hello.status_code == 200
    pairing_code = hello.json()["pairing_code"]

    claim = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"pairing_code": pairing_code},
    )
    assert claim.status_code == 200

    claim_again = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"pairing_code": pairing_code},
    )
    assert claim_again.status_code == 200

    async with Session() as db:
        res = await db.execute(
            select(AuditV1Entry).where(AuditV1Entry.action == "device.claim")
        )
        entries = res.scalars().all()
        assert len(entries) >= 1

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pairing_claim_other_user_forbidden():
    engine, Session = await _mk_session()

    async with Session() as db:
        user1 = User(email="u1@example.com", password_hash="x", caps=None)
        user2 = User(email="u2@example.com", password_hash="x", caps=None)
        db.add_all([user1, user2])
        await db.commit()

    current_user_id = {"value": 1}

    async def _get_user():
        async with Session() as db:
            return await db.get(User, current_user_id["value"])

    app = await _mk_app(Session)
    app.dependency_overrides[get_current_user] = _get_user
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    hello = await client.post(
        "/api/v1/devices/pairing/hello",
        json={"device_uid": "dev-claim-2"},
    )
    assert hello.status_code == 200
    pairing_code = hello.json()["pairing_code"]

    claim = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"pairing_code": pairing_code},
    )
    assert claim.status_code == 200

    current_user_id["value"] = 2
    claim_other = await client.post(
        "/api/v1/devices/pairing/claim",
        json={"pairing_code": pairing_code},
    )
    assert claim_other.status_code == 403

    await client.aclose()
    await engine.dispose()
