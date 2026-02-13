from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.executions import create_definition, create_run_idempotent
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


def _patch_commit_raise_once(monkeypatch):
    called = {"raised": False}
    original = AsyncSession.commit

    async def _commit(self):
        if not called["raised"]:
            called["raised"] = True
            raise IntegrityError("forced integrityerror", None, Exception("orig"))
        return await original(self)

    monkeypatch.setattr(AsyncSession, "commit", _commit, raising=True)


@pytest.mark.asyncio
async def test_create_definition_integrityerror_fallback(monkeypatch):
    engine, Session = await _mk_session()
    async with Session() as db:
        existing = ExecutionDefinition(key="k", name="n", version="v1", enabled=True)
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        existing_id = existing.id

    _patch_commit_raise_once(monkeypatch)

    async with Session() as db:
        definition = await create_definition(db, key="k", name="n2", version="v2", enabled=True)
        assert definition.id == existing_id

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_run_integrityerror_fallback(monkeypatch):
    engine, Session = await _mk_session()
    async with Session() as db:
        definition = ExecutionDefinition(key="k", name="n", version="v1", enabled=True)
        db.add(definition)
        await db.commit()
        await db.refresh(definition)

        run = ExecutionRun(
            definition_id=definition.id,
            idempotency_key="idem-1",
            requested_by=None,
            status="requested",
            input_json={"x": 1},
            output_json=None,
            error_json=None,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        existing_id = run.id

    _patch_commit_raise_once(monkeypatch)

    async with Session() as db:
        created = await create_run_idempotent(
            db,
            definition_id=definition.id,
            idempotency_key="idem-1",
            requested_by=None,
            input_json={"x": 2},
        )
        assert created.id == existing_id

    await engine.dispose()
