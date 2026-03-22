from __future__ import annotations

from datetime import datetime, timezone, timedelta
from app.core.security import hash_device_token

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.devices import router as devices_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base
from app.db.models.device import Device
from app.db.models.pairing import DeviceToken
from app.db.models.user import User
from app.db.models.telemetry import DeviceTelemetry


def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            User.__table__,
            Device.__table__,
            DeviceToken.__table__,
            DeviceTelemetry.__table__,
        ],
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


def _token(sub: str, caps: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": sub,
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": caps,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


async def _make_app(Session):
    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(telemetry_router, prefix="/api/v1")
    app.include_router(devices_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_telemetry_post_and_get(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/telemetry")] = ["telemetry.emit"]
    CAPABILITY_MAP[("GET", "/api/v1/devices/{device_id}/telemetry")] = ["telemetry.read"]

    engine, Session = await _mk_session()
    token_plain = "device-token"
    token_hash = hash_device_token(token_plain)

    async with Session() as db:
        user = User(id=1, email="owner@example.com", password_hash="x", caps=["telemetry.read"])
        device = Device(device_uid="dev-tele-1", owner_user_id=1, is_claimed=True)
        db.add_all([user, device])
        await db.commit()
        await db.refresh(device)
        db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))
        await db.commit()

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        "/api/v1/telemetry",
        json={"event_type": "demo", "payload": {"k": "v"}},
        headers={"X-Device-Token": token_plain},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["telemetry_id"]
    assert body["received_at"]

    res = await client.get(
        f"/api/v1/devices/{device.id}/telemetry?limit=50",
        headers={"Authorization": f"Bearer {_token('1', ['telemetry.read'])}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["event_type"] == "demo"

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_telemetry_post_missing_token_unauthorized(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/telemetry")] = ["telemetry.emit"]

    engine, Session = await _mk_session()
    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        "/api/v1/telemetry",
        json={"event_type": "demo", "payload": {"k": "v"}},
    )
    assert res.status_code == 401

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_telemetry_get_missing_cap_forbidden(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/devices/{device_id}/telemetry")] = ["telemetry.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="owner@example.com", password_hash="x", caps=[])
        device = Device(device_uid="dev-tele-2", owner_user_id=1, is_claimed=True)
        db.add_all([user, device])
        await db.commit()
        await db.refresh(device)

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.get(
        f"/api/v1/devices/{device.id}/telemetry",
        headers={"Authorization": f"Bearer {_token('1', [])}"},
    )
    assert res.status_code == 403

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_telemetry_get_limit_and_order(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/devices/{device_id}/telemetry")] = ["telemetry.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="owner@example.com", password_hash="x", caps=["telemetry.read"])
        device = Device(device_uid="dev-tele-3", owner_user_id=1, is_claimed=True)
        db.add_all([user, device])
        await db.commit()
        await db.refresh(device)

        now = datetime.now(timezone.utc)
        older = DeviceTelemetry(
            device_id=device.id,
            received_at=now - timedelta(seconds=10),
            event_type="old",
            payload={"v": 1},
        )
        newer = DeviceTelemetry(
            device_id=device.id,
            received_at=now,
            event_type="new",
            payload={"v": 2},
        )
        db.add_all([older, newer])
        await db.commit()

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.get(
        f"/api/v1/devices/{device.id}/telemetry?limit=1",
        headers={"Authorization": f"Bearer {_token('1', ['telemetry.read'])}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["event_type"] == "new"

    await client.aclose()
    await engine.dispose()
