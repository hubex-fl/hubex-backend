from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.executions import ExecutionWorker, ExecutionWorkerDefinition


DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class WorkerNotFoundError(RuntimeError):
    pass


async def upsert_worker_heartbeat(
    db: AsyncSession,
    *,
    worker_id: str,
    meta_json: dict | None,
) -> ExecutionWorker:
    now = datetime.now(timezone.utc)
    stmt = (
        update(ExecutionWorker)
        .where(ExecutionWorker.id == worker_id)
        .values(
            last_seen_at=now,
            meta_json=ExecutionWorker.meta_json if meta_json is None else meta_json,
            updated_at=now,
        )
        .returning(ExecutionWorker)
        .execution_options(synchronize_session=False)
    )
    res = await db.execute(stmt)
    updated = res.scalar_one_or_none()
    if updated is not None:
        await db.commit()
        return updated

    worker = ExecutionWorker(
        id=worker_id,
        last_seen_at=now,
        meta_json=meta_json,
        created_at=now,
        updated_at=now,
    )
    db.add(worker)
    try:
        await db.commit()
        await db.refresh(worker)
        return worker
    except IntegrityError:
        await db.rollback()
        res2 = await db.execute(stmt)
        updated2 = res2.scalar_one_or_none()
        if updated2 is None:
            raise
        await db.commit()
        return updated2


async def read_workers(
    db: AsyncSession,
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[ExecutionWorker], str | None]:
    after = cursor or ""
    clamped = min(max(limit, 1), MAX_LIMIT)

    res = await db.execute(
        select(ExecutionWorker)
        .where(ExecutionWorker.id > after)
        .order_by(ExecutionWorker.id.asc())
        .limit(clamped + 1)
    )
    rows = list(res.scalars().all())
    if len(rows) <= clamped:
        return rows, None

    page = rows[:clamped]
    next_cursor = page[-1].id
    return page, next_cursor


async def set_worker_definitions(
    db: AsyncSession,
    *,
    worker_id: str,
    definition_ids: list[int],
) -> list[int]:
    worker = await db.scalar(select(ExecutionWorker.id).where(ExecutionWorker.id == worker_id))
    if worker is None:
        raise WorkerNotFoundError("worker not found")

    unique_ids = list(dict.fromkeys(definition_ids))
    await db.execute(
        delete(ExecutionWorkerDefinition).where(ExecutionWorkerDefinition.worker_id == worker_id)
    )
    if unique_ids:
        db.add_all(
            [
                ExecutionWorkerDefinition(worker_id=worker_id, definition_id=definition_id)
                for definition_id in unique_ids
            ]
        )
    await db.commit()
    return unique_ids


async def read_worker_definitions(
    db: AsyncSession,
    *,
    worker_id: str,
) -> list[int]:
    worker = await db.scalar(select(ExecutionWorker.id).where(ExecutionWorker.id == worker_id))
    if worker is None:
        raise WorkerNotFoundError("worker not found")

    res = await db.execute(
        select(ExecutionWorkerDefinition.definition_id)
        .where(ExecutionWorkerDefinition.worker_id == worker_id)
        .order_by(ExecutionWorkerDefinition.definition_id.asc())
    )
    return list(res.scalars().all())


async def read_definition_workers(
    db: AsyncSession,
    *,
    definition_id: int,
) -> list[str]:
    res = await db.execute(
        select(ExecutionWorkerDefinition.worker_id)
        .where(ExecutionWorkerDefinition.definition_id == definition_id)
        .order_by(ExecutionWorkerDefinition.worker_id.asc())
    )
    return list(res.scalars().all())
