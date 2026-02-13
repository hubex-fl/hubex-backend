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
async def test_execution_workers_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/workers")] = ["executions.read"]

    engine, Session = await _mk_session()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.post("/api/v1/executions/workers/heartbeat", json={"worker_id": "w1"})
    assert res.status_code == 401
    res2 = await client.get("/api/v1/executions/workers")
    assert res2.status_code == 401

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
    res3 = await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res3.status_code == 403
    res4 = await client.get(
        "/api/v1/executions/workers",
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res4.status_code == 403

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

    res5 = await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "w1"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res5.status_code == 200

    res6 = await client.get(
        "/api/v1/executions/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res6.status_code == 200

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_workers_heartbeat_upsert_and_list(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/workers")] = ["executions.read"]

    engine, Session = await _mk_session()

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
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "a", "meta_json": {"v": 1}},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res.status_code == 200
    first = res.json()
    assert first["id"] == "a"
    assert first["meta_json"] == {"v": 1}

    res2 = await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "a"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    assert res2.status_code == 200
    second = res2.json()
    assert second["id"] == "a"
    assert second["meta_json"] == {"v": 1}

    await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "b"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "c"},
        headers={"Authorization": f"Bearer {token_write}"},
    )

    res3 = await client.get(
        "/api/v1/executions/workers",
        params={"limit": 2},
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res3.status_code == 200
    body = res3.json()
    assert [w["id"] for w in body["items"]] == ["a", "b"]
    assert body["next_cursor"] == "b"

    res4 = await client.get(
        "/api/v1/executions/workers",
        params={"cursor": body["next_cursor"], "limit": 2},
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res4.status_code == 200
    body2 = res4.json()
    assert [w["id"] for w in body2["items"]] == ["c"]
    assert body2["next_cursor"] is None

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_execution_workers_active_within_filter(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/executions/workers/heartbeat")] = ["executions.write"]
    CAPABILITY_MAP[("GET", "/api/v1/executions/workers")] = ["executions.read"]

    engine, Session = await _mk_session()

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
        json={"worker_id": "a"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "b"},
        headers={"Authorization": f"Bearer {token_write}"},
    )
    await client.post(
        "/api/v1/executions/workers/heartbeat",
        json={"worker_id": "c"},
        headers={"Authorization": f"Bearer {token_write}"},
    )

    async with Session() as db:
        await db.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.id == "a")
            .values(last_seen_at=now - timedelta(seconds=600))
        )
        await db.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.id == "b")
            .values(last_seen_at=now - timedelta(seconds=60))
        )
        await db.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.id == "c")
            .values(last_seen_at=now - timedelta(seconds=10))
        )
        await db.commit()

    res = await client.get(
        "/api/v1/executions/workers",
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res.status_code == 200
    assert [w["id"] for w in res.json()["items"]] == ["a", "b", "c"]

    res2 = await client.get(
        "/api/v1/executions/workers",
        params={"active_within_seconds": 120},
        headers={"Authorization": f"Bearer {token_read}"},
    )
    assert res2.status_code == 200
    assert [w["id"] for w in res2.json()["items"]] == ["b", "c"]

    await client.aclose()
    await engine.dispose()
