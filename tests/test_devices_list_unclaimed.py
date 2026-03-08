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
from app.db.models.device import Device
from app.db.models.user import User
from app.db.models.pairing import PairingSession


def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            User.__table__,
            Device.__table__,
            PairingSession.__table__,
        ],
    )
    # sqlite: create minimal tasks table used by fetch_busy_device_ids
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
async def test_list_devices_includes_unclaimed_after_hello(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/devices")] = ["devices.read"]
    CAPABILITY_MAP[("POST", "/devices/hello")] = ["devices.hello"]
    CAPABILITY_MAP[("GET", "/devices")] = ["devices.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        user = User(id=1, email="user@example.com", password_hash="x", caps=["devices.read", "cap.admin"])
        db.add(user)
        await db.commit()

    app = await _make_app(Session)
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")
    res_hello = await client.post(
        "/api/v1/devices/hello",
        json={"device_uid": "dev-unc", "firmware_version": "dev", "capabilities": {}},
    )
    assert res_hello.status_code == 200
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")

    res_list = await client.get(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {_token('1', ['devices.read'])}"},
    )
    assert res_list.status_code == 200
    data = res_list.json()
    assert not any(d["device_uid"] == "dev-unc" for d in data)

    res_list_all = await client.get(
        "/api/v1/devices?include_unclaimed=1",
        headers={"Authorization": f"Bearer {_token('1', ['devices.read', 'cap.admin'])}"},
    )
    assert res_list_all.status_code == 200
    data_all = res_list_all.json()
    assert any(d["device_uid"] == "dev-unc" for d in data_all)
    unclaimed = next(d for d in data_all if d["device_uid"] == "dev-unc")
    assert unclaimed["claimed"] is False

    await client.aclose()
    await engine.dispose()
