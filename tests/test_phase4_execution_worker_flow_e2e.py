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
from app.db.models.executions import ExecutionDefinition, ExecutionRun, ExecutionWorker


def _create_execution_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            ExecutionDefinition.__table__,
            ExecutionRun.__table__,
            ExecutionWorker.__table__,
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
async def test_execution_worker_flow_e2e(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/lease")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/finalize")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        definition = await create_definition(db, key="def-1", name="Def", version="v1", enabled=True)
        await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="run-1",
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
        "/api/v1/executions/runs/claim-next",
        json={"definition_key": "def-1", "worker_id": "worker-1", "lease_seconds": 60},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200
    body = res.json()
    run_id = body["id"]
    assert body["claimed_by"] == "worker-1"
    assert body["lease_expires_at"] is not None

    lease_before = body["lease_expires_at"]
    res2 = await client.post(
        f"/api/v1/executions/runs/{run_id}/lease",
        json={"worker_id": "worker-1", "lease_seconds": 60},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res2.status_code == 200
    lease_after = res2.json()["lease_expires_at"]
    assert lease_after is not None

    res3 = await client.post(
        f"/api/v1/executions/runs/{run_id}/finalize",
        json={"status": "completed", "output_json": {"ok": True}},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res3.status_code == 409

    res4 = await client.post(
        f"/api/v1/executions/runs/{run_id}/finalize",
        json={"status": "completed", "output_json": {"ok": True}, "worker_id": "worker-1"},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res4.status_code == 200
    body2 = res4.json()
    assert body2["status"] == "completed"
    assert body2["output_json"] == {"ok": True}
    assert lease_after >= lease_before

    await client.aclose()
    await engine.dispose()
