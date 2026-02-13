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
from app.api.v1.executions import router as executions_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.execution_workers import upsert_worker_heartbeat
from app.core.executions import create_definition, create_run_idempotent
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base
from app.db.models.executions import (
    ExecutionDefinition,
    ExecutionRun,
    ExecutionWorker,
    ExecutionWorkerDefinition,
)


def _create_execution_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            ExecutionDefinition.__table__,
            ExecutionRun.__table__,
            ExecutionWorker.__table__,
            ExecutionWorkerDefinition.__table__,
        ],
    )


async def _mk_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_execution_tables(Base.metadata, c))
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, Session


def _make_token(caps: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": caps,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


@pytest.mark.asyncio
async def test_claim_next_uses_subscriptions_when_definition_key_missing(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        d1 = await create_definition(db, key="d1", name="n1", version="v1", enabled=True)
        d2 = await create_definition(db, key="d2", name="n2", version="v1", enabled=True)
        await create_run_idempotent(db, definition_id=d1.id, idempotency_key="i1", requested_by=None, input_json={})
        await create_run_idempotent(db, definition_id=d2.id, idempotency_key="i2", requested_by=None, input_json={})
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    token = _make_token(["executions.write"])
    await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d2"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    res = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"worker_id": "w1", "lease_seconds": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["definition_id"] == d2.id

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_next_rejects_unsubscribed_definition(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        d1 = await create_definition(db, key="d1", name="n1", version="v1", enabled=True)
        await create_definition(db, key="d2", name="n2", version="v1", enabled=True)
        await create_run_idempotent(db, definition_id=d1.id, idempotency_key="i1", requested_by=None, input_json={})
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    token = _make_token(["executions.write"])
    await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d2"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    res = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "d1", "worker_id": "w1", "lease_seconds": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_next_requires_definition_key_without_subscriptions(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        d1 = await create_definition(db, key="d1", name="n1", version="v1", enabled=True)
        await create_run_idempotent(db, definition_id=d1.id, idempotency_key="i1", requested_by=None, input_json={})
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    token = _make_token(["executions.write"])
    res = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"worker_id": "w1", "lease_seconds": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_next_with_definition_key_when_no_subscriptions(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        d1 = await create_definition(db, key="d1", name="n1", version="v1", enabled=True)
        await create_run_idempotent(db, definition_id=d1.id, idempotency_key="i1", requested_by=None, input_json={})

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    token = _make_token(["executions.write"])
    res = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "d1", "worker_id": "w1", "lease_seconds": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["definition_id"] == d1.id

    await client.aclose()
    await engine.dispose()
