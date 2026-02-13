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
async def test_claim_next_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        await create_definition(db, key="k", name="n", version="v1", enabled=True)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post("/api/v1/executions/runs/claim-next", json={"definition_key": "k", "worker_id": "w1"})
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
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "k", "worker_id": "w1"},
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
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "missing", "worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res3.status_code == 404

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_next_happy_path_and_order(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        definition = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        for i in range(3):
            await create_run_idempotent(
                db,
                definition_id=definition.id,
                idempotency_key=f"i{i}",
                requested_by=None,
                input_json={"x": i},
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
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "k", "worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200
    first_id = res.json()["id"]

    res2 = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "k", "worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res2.status_code == 200
    second_id = res2.json()["id"]
    assert second_id > first_id

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_next_conflict_and_idempotent(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/claim")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        definition = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        run1 = await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="i1",
            requested_by=None,
            input_json={"x": 1},
        )
        run2 = await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="i2",
            requested_by=None,
            input_json={"x": 2},
        )
        run1_id = run1.id
        run2_id = run2.id

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
        f"/api/v1/executions/runs/{run1_id}/claim",
        json={"worker_id": "worker-a", "lease_seconds": 300},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200

    res2 = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "k", "worker_id": "worker-b"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res2.status_code == 200
    assert res2.json()["id"] == run2_id

    res3 = await client.post(
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "k", "worker_id": "worker-a"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res3.status_code == 200
    assert res3.json()["id"] == run1_id

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_next_no_available(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
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
        run.claimed_by = "worker-a"
        run.claimed_at = datetime.now(timezone.utc)
        run.lease_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
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
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "k", "worker_id": "worker-b"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 404

    await client.aclose()
    await engine.dispose()
