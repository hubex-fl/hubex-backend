from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy import select
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
from app.worker_v1.config import WorkerConfig, load_config_from_env
from app.worker_v1.service import run_worker


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
async def test_worker_service_e2e_claim_finalize_and_subscription(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/claim-next")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/lease")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/finalize")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/runs/{run_id}/release")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]

    engine, Session = await _mk_session()
    async with Session() as db:
        d1 = await create_definition(db, key="d1", name="n1", version="v1", enabled=True)
        d2 = await create_definition(db, key="d2", name="n2", version="v1", enabled=True)
        await create_run_idempotent(db, definition_id=d2.id, idempotency_key="r1", requested_by=None, input_json={"x": 1})
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)

    token = _make_token(["executions.write"])
    config = WorkerConfig(
        base_url="http://test",
        token=token,
        worker_id="w1",
        lease_seconds=60,
        heartbeat_every=30,
        poll_delay=0.1,
        definition_key=None,
        max_runs=1,
    )

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sub_resp = await client.post(
            "/api/v1/executions/workers/w1/definitions",
            json={"definition_keys": ["d2"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sub_resp.status_code == 200
        code = await asyncio.wait_for(run_worker(config, client), timeout=2)

    assert code == 0
    async with Session() as db:
        worker = await db.get(ExecutionWorker, "w1")
        assert worker is not None
        run = await db.scalar(select(ExecutionRun).where(ExecutionRun.definition_id == d2.id))
        assert run is not None
        assert run.status == "completed"
        assert run.output_json["ok"] is True
        assert run.output_json["echo"] == {"x": 1}

    await engine.dispose()


def test_worker_run_once_env_sets_max_runs(monkeypatch):
    monkeypatch.setenv("HUBEX_TOKEN", "tok")
    monkeypatch.setenv("WORKER_ID", "worker-1")
    monkeypatch.setenv("RUN_ONCE", "1")

    cfg = load_config_from_env()
    assert cfg.max_runs == 1
