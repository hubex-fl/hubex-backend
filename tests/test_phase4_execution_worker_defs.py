from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.executions import router as executions_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.execution_workers import upsert_worker_heartbeat
from app.core.executions import create_definition
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


@pytest.mark.asyncio
async def test_execution_worker_definitions_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.read"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/definitions/{definition_key}/workers")] = ["executions.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)
        await create_definition(db, key="d1", name="n1", version="v1", enabled=True)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d1"]},
    )
    assert res.status_code == 401
    res2 = await client.get("/api/v1/executions/workers/w1/definitions")
    assert res2.status_code == 401
    res3 = await client.get("/api/v1/executions/definitions/d1/workers")
    assert res3.status_code == 401

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
    res4 = await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d1"]},
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res4.status_code == 403
    res5 = await client.get(
        "/api/v1/executions/workers/w1/definitions",
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res5.status_code == 403
    res6 = await client.get(
        "/api/v1/executions/definitions/d1/workers",
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res6.status_code == 403

    token_write = jwt.encode(
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
    token_read = jwt.encode(
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

    res7 = await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d1"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res7.status_code == 200

    res8 = await client.get(
        "/api/v1/executions/workers/w1/definitions",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res8.status_code == 200

    res9 = await client.get(
        "/api/v1/executions/definitions/d1/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res9.status_code == 200

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_worker_definitions_happy_path_and_replace(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.read"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/definitions/{definition_key}/workers")] = ["executions.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)
        await create_definition(db, key="d1", name="n1", version="v1", enabled=True)
        await create_definition(db, key="d2", name="n2", version="v1", enabled=True)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    now = datetime.now(timezone.utc)
    token_write = jwt.encode(
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
    token_read = jwt.encode(
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

    res = await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d1", "d2"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res.status_code == 200
    assert res.json()["definition_keys"] == ["d1", "d2"]

    res2 = await client.get(
        "/api/v1/executions/workers/w1/definitions",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res2.status_code == 200
    assert res2.json()["definition_keys"] == ["d1", "d2"]

    res3 = await client.get(
        "/api/v1/executions/definitions/d1/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res3.status_code == 200
    assert res3.json()["worker_ids"] == ["w1"]

    res4 = await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d2"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res4.status_code == 200
    assert res4.json()["definition_keys"] == ["d2"]

    res5 = await client.get(
        "/api/v1/executions/workers/w1/definitions",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res5.status_code == 200
    assert res5.json()["definition_keys"] == ["d2"]

    res6 = await client.get(
        "/api/v1/executions/definitions/d1/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res6.status_code == 200
    assert res6.json()["worker_ids"] == []

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_worker_definitions_unknowns(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.read"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/definitions/{definition_key}/workers")] = ["executions.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        await upsert_worker_heartbeat(db, worker_id="w1", meta_json=None)
        await create_definition(db, key="d1", name="n1", version="v1", enabled=True)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    now = datetime.now(timezone.utc)
    token_write = jwt.encode(
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
    token_read = jwt.encode(
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

    res = await client.post(
        "/api/v1/executions/workers/unknown/definitions",
        json={"definition_keys": ["d1"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res.status_code == 404

    res2 = await client.get(
        "/api/v1/executions/workers/unknown/definitions",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res2.status_code == 404

    res3 = await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["missing"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res3.status_code == 404

    res4 = await client.get(
        "/api/v1/executions/definitions/missing/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res4.status_code == 404

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_definition_workers_active_within_filter(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/{worker_id}/definitions")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/definitions/{definition_key}/workers")] = ["executions.read"]

    engine, Session = await _mk_session()
    async with Session() as db:
        await create_definition(db, key="d1", name="n1", version="v1", enabled=True)

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    now = datetime.now(timezone.utc)
    token_write = jwt.encode(
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
    token_read = jwt.encode(
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

    await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "w2"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    await client.post(
        "/api/v1/executions/workers/w1/definitions",
        json={"definition_keys": ["d1"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    await client.post(
        "/api/v1/executions/workers/w2/definitions",
        json={"definition_keys": ["d1"]},
        headers={"Authorization": f"Bearer {token_write}"},
    )

    async with Session() as db:
        await db.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.id == "w1")
            .values(last_seen_at=now - timedelta(seconds=600))
        )
        await db.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.id == "w2")
            .values(last_seen_at=now - timedelta(seconds=10))
        )
        await db.commit()

    res = await client.get(
        "/api/v1/executions/definitions/d1/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res.status_code == 200
    assert res.json()["worker_ids"] == ["w1", "w2"]

    res2 = await client.get(
        "/api/v1/executions/definitions/d1/workers",
        params={"active_within_seconds": 120},
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res2.status_code == 200
    assert res2.json()["worker_ids"] == ["w2"]

    await client.aclose()
    await engine.dispose()
