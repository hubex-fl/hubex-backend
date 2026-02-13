from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.executions import create_definition, create_run_idempotent, read_runs, MAX_LIMIT
from app.db.base import Base
from app.db.models.executions import (
    ExecutionDefinition,
    ExecutionRun,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
)


def _create_execution_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            ExecutionDefinition.__table__,
            ExecutionRun.__table__,
        ],
    )


async def _mk_db():
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
async def test_create_run_idempotent_same_key_returns_same_row():
    engine, Session = await _mk_db()
    async with Session() as db:
        d = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        r1 = await create_run_idempotent(
            db,
            definition_id=d.id,
            idempotency_key="idem-1",
            requested_by="u1",
            input_json={"x": 1},
        )
        r2 = await create_run_idempotent(
            db,
            definition_id=d.id,
            idempotency_key="idem-1",
            requested_by="u1",
            input_json={"x": 1},
        )
        assert r1.id == r2.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_read_runs_deterministic_pagination_and_next_cursor():
    engine, Session = await _mk_db()
    async with Session() as db:
        d = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        for i in range(7):
            await create_run_idempotent(
                db,
                definition_id=d.id,
                idempotency_key=f"idem-{i}",
                requested_by=None,
                input_json={"i": i},
            )

        seen: list[int] = []
        cursor: int | None = None
        while True:
            items, next_cursor = await read_runs(db, definition_id=d.id, status=None, cursor=cursor, limit=3)
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
async def test_read_runs_limit_clamped():
    engine, Session = await _mk_db()
    async with Session() as db:
        d = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        for i in range(MAX_LIMIT + 10):
            await create_run_idempotent(
                db,
                definition_id=d.id,
                idempotency_key=f"idem-{i}",
                requested_by=None,
                input_json={"i": i},
            )

        items, next_cursor = await read_runs(db, definition_id=d.id, status=None, cursor=0, limit=MAX_LIMIT + 1000)
        assert len(items) == MAX_LIMIT
        assert next_cursor is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_run_invariants_write_once_and_final_immutable():
    engine, Session = await _mk_db()
    async with Session() as db:
        d = await create_definition(db, key="k", name="n", version="v1", enabled=True)
        run = await create_run_idempotent(
            db,
            definition_id=d.id,
            idempotency_key="idem-1",
            requested_by=None,
            input_json={"x": 1},
        )

        with pytest.raises(ValueError):
            run.input_json = {"x": 2}

        run.output_json = {"ok": True}
        await db.commit()

        with pytest.raises(ValueError):
            run.output_json = {"ok": False}
        with pytest.raises(ValueError):
            run.error_json = {"err": "nope"}

        run.status = RUN_STATUS_COMPLETED
        await db.commit()

        with pytest.raises(ValueError):
            run.status = RUN_STATUS_FAILED
    await engine.dispose()
