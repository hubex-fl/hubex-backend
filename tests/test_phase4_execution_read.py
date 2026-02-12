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
