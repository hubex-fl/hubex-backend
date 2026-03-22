from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.devices import router as devices_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base
from app.db.models.audit import AuditV1Entry
from app.db.models.device import Device
from app.db.models.events import EventV1
from app.db.models.pairing import DeviceToken
from app.db.models.user import User


def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            User.__table__,
            Device.__table__,
            DeviceToken.__table__,
            AuditV1Entry.__table__,
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
    app.include_router(devices_router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_device_unclaim_owner_success_and_audit(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/devices/{device_id}/unclaim")] = ["devices.unclaim"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="owner@example.com", password_hash="x", caps=["devices.unclaim"])
        device = Device(device_uid="dev-1", owner_user_id=1, is_claimed=True)
        db.add_all([user, device])
        await db.commit()
        await db.refresh(device)
        db.add(DeviceToken(device_id=device.id, token_hash="old-1", is_active=True))
        db.add(DeviceToken(device_id=device.id, token_hash="old-2", is_active=True))
        await db.commit()

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        f"/api/v1/devices/{device.id}/unclaim",
        headers={"Authorization": f"Bearer {_token('1', ['devices.unclaim'])}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["device_id"] == device.id
    assert body["device_uid"] == "dev-1"
    assert body["revoked_count"] == 2
    assert body["unclaimed"] is True

    async with Session() as db:
        updated = await db.get(Device, device.id)
        assert updated is not None
        assert updated.owner_user_id is None
        assert updated.is_claimed is False

        res_tokens = await db.execute(
            DeviceToken.__table__.select().where(DeviceToken.device_id == device.id)
        )
        tokens = res_tokens.fetchall()
        assert tokens
        assert all(not t.is_active for t in tokens)

        res_audit = await db.execute(
            AuditV1Entry.__table__.select().order_by(AuditV1Entry.id.asc())
        )
        rows = res_audit.fetchall()
        assert rows
        assert rows[-1].action == "device.unclaim"
        assert rows[-1].metadata.get("device_uid") == "dev-1"
        assert rows[-1].metadata.get("revoked_count") == 2

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_device_unclaim_non_owner_forbidden(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/devices/{device_id}/unclaim")] = ["devices.unclaim"]

    engine, Session = await _mk_session()
    async with Session() as db:
        owner = User(id=1, email="owner@example.com", password_hash="x", caps=[])
        other = User(id=2, email="other@example.com", password_hash="y", caps=[])
        device = Device(device_uid="dev-2", owner_user_id=1, is_claimed=True)
        db.add_all([owner, other, device])
        await db.commit()
        await db.refresh(device)

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        f"/api/v1/devices/{device.id}/unclaim",
        headers={"Authorization": f"Bearer {_token('2', ['devices.unclaim'])}"},
    )
    assert res.status_code == 403
    assert res.json().get("detail", {}).get("code") == "DEVICE_NOT_OWNER"

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_device_unclaim_missing_cap_forbidden(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/devices/{device_id}/unclaim")] = ["devices.unclaim"]

    engine, Session = await _mk_session()
    async with Session() as db:
        owner = User(id=1, email="owner@example.com", password_hash="x", caps=[])
        device = Device(device_uid="dev-3", owner_user_id=1, is_claimed=True)
        db.add_all([owner, device])
        await db.commit()
        await db.refresh(device)

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        f"/api/v1/devices/{device.id}/unclaim",
        headers={"Authorization": f"Bearer {_token('1', [])}"},
    )
    assert res.status_code == 403

    await client.aclose()
    await engine.dispose()
