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
from app.api.v1.events import router as events_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY, hash_device_token
from app.db.base import Base
from app.db.models.audit import AuditV1Entry
from app.db.models.device import Device
from app.db.models.events import EventV1
from app.db.models.executions import ExecutionDefinition, ExecutionRun
from app.db.models.pairing import DeviceToken
from app.demo.vertical_demo_v1 import run_demo_bridge


def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            Device.__table__,
            DeviceToken.__table__,
            EventV1.__table__,
            ExecutionDefinition.__table__,
            ExecutionRun.__table__,
            AuditV1Entry.__table__,
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


@pytest.mark.asyncio
async def test_vertical_demo_signal_creates_execution_run_and_audit(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/events/emit")] = ["events.emit"]

    engine, Session = await _mk_session()

    async with Session() as db:
        device = Device(device_uid="demo-device", owner_user_id=1, is_claimed=True)
        db.add(device)
        await db.commit()
        await db.refresh(device)
        token_plain = "plain-token"
        token_hash = hash_device_token(token_plain)
        db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))
        await db.commit()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(events_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    trace_id = "corr-demo-1"
    res = await client.post(
        "/api/v1/events/emit",
        json={"type": "signal.demo_v1", "payload": {"k": "v"}, "trace_id": trace_id},
        headers={
            "Authorization": f"Bearer {_token('1', ['events.emit'])}",
            "X-Device-Token": token_plain,
        },
    )
    assert res.status_code == 200

    async with Session() as db:
        run = await run_demo_bridge(db, device_uid="demo-device", trace_id=trace_id)
        assert run.input_json.get("correlation_id") == trace_id

        res_audit = await db.execute(
            AuditV1Entry.__table__.select().where(AuditV1Entry.trace_id == trace_id)
        )
        rows = res_audit.fetchall()
        actions = [row.action for row in rows]
        assert "demo.execution.create" in actions

    await client.aclose()
    await engine.dispose()
