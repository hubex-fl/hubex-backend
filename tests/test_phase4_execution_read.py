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


@pytest.mark.asyncio
async def test_executions_endpoint_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/executions/runs")] = ["executions.read"]

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_execution_tables(Base.metadata, c))

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        definition = await create_definition(db, key="def-1", name="Def", version="v1", enabled=True)
        await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="idem-1",
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

    res = await client.get("/api/v1/executions/runs", params={"definition_key": "def-1"})
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
    res = await client.get(
        "/api/v1/executions/runs",
        params={"definition_key": "def-1"},
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res.status_code == 403

    token_ok = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["executions.read"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    res = await client.get(
        "/api/v1/executions/runs",
        params={"definition_key": "def-1", "limit": 10},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "next_cursor" in body

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_executions_runs_status_filter_and_pagination(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/executions/runs")] = ["executions.read"]

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_execution_tables(Base.metadata, c))

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        definition = await create_definition(db, key="def-1", name="Def", version="v1", enabled=True)
        runs = [
            ExecutionRun(
                definition_id=definition.id,
                idempotency_key="r1",
                requested_by=None,
                status="requested",
                input_json={"x": 1},
                output_json=None,
                error_json=None,
            ),
            ExecutionRun(
                definition_id=definition.id,
                idempotency_key="r2",
                requested_by=None,
                status="completed",
                input_json={"x": 2},
                output_json={},
                error_json=None,
            ),
            ExecutionRun(
                definition_id=definition.id,
                idempotency_key="r3",
                requested_by=None,
                status="failed",
                input_json={"x": 3},
                output_json=None,
                error_json={},
            ),
            ExecutionRun(
                definition_id=definition.id,
                idempotency_key="r4",
                requested_by=None,
                status="completed",
                input_json={"x": 4},
                output_json={},
                error_json=None,
            ),
        ]
        db.add_all(runs)
        await db.commit()
        for r in runs:
            await db.refresh(r)

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
            "caps": ["executions.read"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    res = await client.get(
        "/api/v1/executions/runs",
        params={"definition_key": "def-1", "status": "completed", "limit": 1},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "completed"
    cursor = body["next_cursor"]
    assert cursor is not None

    res2 = await client.get(
        "/api/v1/executions/runs",
        params={"definition_key": "def-1", "status": "completed", "cursor": cursor, "limit": 1},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["status"] == "completed"
    assert body2["next_cursor"] is None

    res3 = await client.get(
        "/api/v1/executions/runs",
        params={"definition_key": "def-1", "status": "not-a-status"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res3.status_code == 400

    await client.aclose()
    await engine.dispose()
