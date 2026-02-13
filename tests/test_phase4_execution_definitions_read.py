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
from app.core.executions import MAX_LIMIT, create_definition, read_definitions
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
async def test_execution_definitions_read_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/executions/definitions")] = ["executions.read"]

    engine, Session = await _mk_session()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(executions_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.get("/api/v1/executions/definitions")
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
        "/api/v1/executions/definitions",
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
        "/api/v1/executions/definitions",
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "next_cursor" in body

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_read_definitions_pagination_deterministic_and_monotonic():
    engine, Session = await _mk_session()
    async with Session() as db:
        for i in range(7):
            await create_definition(db, key=f"k{i}", name=f"n{i}", version="v1", enabled=True)

        seen: list[int] = []
        cursor: int | None = None
        while True:
            items, next_cursor = await read_definitions(db, cursor=cursor, limit=3)
            ids = [it.id for it in items]
            assert ids == sorted(ids)
            assert not (set(ids) & set(seen))
            seen.extend(ids)
            if next_cursor is None:
                break
            assert cursor is None or next_cursor > cursor
            cursor = next_cursor

        assert len(seen) == 7
        assert seen == sorted(seen)
    await engine.dispose()


@pytest.mark.asyncio
async def test_read_definitions_limit_clamped():
    engine, Session = await _mk_session()
    async with Session() as db:
        for i in range(MAX_LIMIT + 10):
            await create_definition(db, key=f"k{i}", name=f"n{i}", version="v1", enabled=True)

        items, next_cursor = await read_definitions(db, cursor=0, limit=MAX_LIMIT + 1000)
        assert len(items) == MAX_LIMIT
        assert next_cursor is not None
    await engine.dispose()
