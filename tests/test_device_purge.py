from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.devices import router as devices_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base
from app.db.models.device import Device
from app.db.models.device_runtime import DeviceRuntimeSetting
from app.db.models.audit import AuditV1Entry
from app.db.models.entities import Entity, EntityDeviceBinding
from app.db.models.pairing import DeviceToken, PairingSession
from app.db.models.telemetry import DeviceTelemetry
from app.db.models.user import User


def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            User.__table__,
            Device.__table__,
            DeviceTelemetry.__table__,
            PairingSession.__table__,
            DeviceToken.__table__,
            Entity.__table__,
            EntityDeviceBinding.__table__,
            DeviceRuntimeSetting.__table__,
            AuditV1Entry.__table__,
        ],
    )

    # Minimal SQLite tables for JSONB-backed models used by purge deletes.
    conn.execute(text("CREATE TABLE IF NOT EXISTS tasks (client_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS execution_contexts (client_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS variable_snapshot_items (device_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS variable_applied_acks (device_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS variable_audits (device_id INTEGER, actor_device_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS variable_values (device_id INTEGER, updated_by_device_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS variable_snapshots (device_id INTEGER)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS variable_effects (device_id INTEGER, device_uid TEXT)"))


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
async def test_device_purge_deletes_dependents(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/devices/{device_id}/purge")] = ["devices.purge"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="admin@example.com", password_hash="x", caps=["devices.purge"])
        device = Device(device_uid="dev-1", owner_user_id=None, is_claimed=False)
        db.add_all([user, device])
        await db.commit()
        await db.refresh(device)

        db.add(DeviceTelemetry(device_id=device.id, event_type="t", payload={"ok": True}))
        db.add(PairingSession(device_uid=device.device_uid, pairing_code="PCODE1", user_id=None,
                              expires_at=datetime.now(timezone.utc), is_used=False))
        db.add(DeviceToken(device_id=device.id, token_hash="hash", is_active=True))

        db.add(DeviceRuntimeSetting(device_id=device.id, telemetry_interval_ms=1000))
        ent = Entity(entity_id="ent-1", type="sensor", name="E1")
        db.add(ent)
        await db.commit()
        db.add(EntityDeviceBinding(entity_id="ent-1", device_id=device.id, enabled=True, priority=0))
        await db.commit()

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        f"/api/v1/devices/{device.id}/purge",
        json={"reason": "cleanup"},
        headers={"Authorization": f"Bearer {_token('1', ['devices.purge'])}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["device_id"] == device.id
    assert body["device_uid"] == "dev-1"
    assert body["deleted_counts"]["devices"] == 1

    async with Session() as db:
        assert await db.get(Device, device.id) is None
        res_tel = await db.execute(DeviceTelemetry.__table__.select())
        assert res_tel.fetchall() == []
        res_token = await db.execute(DeviceToken.__table__.select())
        assert res_token.fetchall() == []
        res_pairing = await db.execute(PairingSession.__table__.select())
        assert res_pairing.fetchall() == []
        res_bind = await db.execute(EntityDeviceBinding.__table__.select())
        assert res_bind.fetchall() == []
        res_rt = await db.execute(DeviceRuntimeSetting.__table__.select())
        assert res_rt.fetchall() == []
        res_audit = await db.execute(select(AuditV1Entry))
        audit_rows = res_audit.scalars().all()
        assert audit_rows
        row = audit_rows[0]
        assert row.action == "device.purge"
        assert row.audit_metadata["deleted_counts"]["devices"] == 1
        assert row.audit_metadata["reason"] == "cleanup"
        assert row.audit_metadata["bulk"] is False

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_device_purge_requires_admin(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/devices/{device_id}/purge")] = ["devices.purge"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="user@example.com", password_hash="x", caps=[])
        device = Device(device_uid="dev-2", owner_user_id=None, is_claimed=False)
        db.add_all([user, device])
        await db.commit()
        await db.refresh(device)

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        f"/api/v1/devices/{device.id}/purge",
        json={"reason": "x"},
        headers={"Authorization": f"Bearer {_token('1', [])}"},
    )
    assert res.status_code == 403
    body = res.json()
    assert body.get("detail", {}).get("code") == "DEVICE_PURGE_FORBIDDEN"

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_device_bulk_purge_writes_audit(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/devices/purge")] = ["devices.purge"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="admin@example.com", password_hash="x", caps=["devices.purge"])
        d1 = Device(device_uid="dev-a", owner_user_id=None, is_claimed=False)
        d2 = Device(device_uid="dev-b", owner_user_id=None, is_claimed=False)
        db.add_all([user, d1, d2])
        await db.commit()
        await db.refresh(d1)
        await db.refresh(d2)
        db.add(DeviceTelemetry(device_id=d1.id, event_type="t", payload={"ok": True}))
        db.add(DeviceTelemetry(device_id=d2.id, event_type="t", payload={"ok": True}))
        await db.commit()

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        "/api/v1/devices/purge",
        json={"device_ids": [d1.id, d2.id], "reason": "bulk-clean"},
        headers={"Authorization": f"Bearer {_token('1', ['devices.purge'])}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["results"]) == 2

    async with Session() as db:
        res_audit = await db.execute(select(AuditV1Entry))
        audit_rows = res_audit.scalars().all()
        assert len(audit_rows) == 2
        for row in audit_rows:
            assert row.action == "device.purge"
            assert row.audit_metadata["bulk"] is True
            assert row.audit_metadata["reason"] == "bulk-clean"
            assert row.audit_metadata["requested_device_ids_count"] == 2

    await client.aclose()
    await engine.dispose()
