from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
from app.core.executions import create_definition, create_run_idempotent
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base
from app.db.models.executions import ExecutionDefinition, ExecutionRun


def _create_execution_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            ExecutionDefinition.__table__,
            ExecutionRun.__table__,
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


@pytest.mark.asyncio
async def test_execution_release_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/release")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        definition = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        run = await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="i1",
            requested_by=None,
            input_json={"x": 1},
        )

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(f"/api/v1/executions/runs/{run.id}/release", json={"worker_id": "w1"})
    assert res.status_code == 401

    now = datetime.now(timezone.utc)
    token_no_cap = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["devices.read"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    res2 = await client.post(
        f"/api/v1/executions/runs/{run.id}/release",
        json={"worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res2.status_code == 403

    token_ok = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["executions.write"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    res3 = await client.post(
        f"/api/v1/executions/runs/{run.id}/release",
        json={"worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res3.status_code == 200

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_release_happy_path_idempotent_and_conflict(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/release")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/claim")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        definition = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        run = await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="i1",
            requested_by=None,
            input_json={"x": 1},
        )

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    now = datetime.now(timezone.utc)
    token_ok = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["executions.write"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    res = await client.post(
        f"/api/v1/executions/runs/{run.id}/claim",
        json={"worker_id": "worker-a", "lease_seconds": 300},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200

    res2 = await client.post(
        f"/api/v1/executions/runs/{run.id}/release",
        json={"worker_id": "worker-a"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res2.status_code == 200
    body = res2.json()
    assert body["claimed_by"] is None
    assert body["claimed_at"] is None
    assert body["lease_expires_at"] is None

    res3 = await client.post(
        f"/api/v1/executions/runs/{run.id}/release",
        json={"worker_id": "worker-a"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res3.status_code == 200

    res4 = await client.post(
        f"/api/v1/executions/runs/{run.id}/claim",
        json={"worker_id": "worker-a", "lease_seconds": 300},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res4.status_code == 200

    res5 = await client.post(
        f"/api/v1/executions/runs/{run.id}/release",
        json={"worker_id": "worker-b"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res5.status_code == 409

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_release_non_requested(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/release")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        definition = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        run = await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="i1",
            requested_by=None,
            input_json={"x": 1},
        )
        run.status = "completed"
        run.output_json = {"ok": True}
        run.error_json = None
        await db.commit()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    now = datetime.now(timezone.utc)
    token_ok = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["executions.write"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    res = await client.post(
        f"/api/v1/executions/runs/{run.id}/release",
        json={"worker_id": "worker-a"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 409

    await client.aclose()
    await engine.dispose()
