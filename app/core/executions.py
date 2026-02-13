from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.executions import (
    ExecutionDefinition,
    ExecutionRun,
    RUN_STATUS_REQUESTED,
)


DEFAULT_LIMIT = 50
MAX_LIMIT = 200


async def create_definition(
    db: AsyncSession,
    *,
    key: str,
    name: str,
    version: str,
    enabled: bool = True,
) -> ExecutionDefinition:
    definition = ExecutionDefinition(key=key, name=name, version=version, enabled=enabled)
    db.add(definition)
    try:
        await db.commit()
        await db.refresh(definition)
        return definition
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == key))
        if existing is None:
            raise
        return existing


async def create_run_idempotent(
    db: AsyncSession,
    *,
    definition_id: int,
    idempotency_key: str,
    requested_by: str | None,
    input_json: dict,
) -> ExecutionRun:
    run = ExecutionRun(
        definition_id=definition_id,
        idempotency_key=idempotency_key,
        requested_by=requested_by,
        status=RUN_STATUS_REQUESTED,
        input_json=input_json,
        output_json=None,
        error_json=None,
    )
    db.add(run)
    try:
        await db.commit()
        await db.refresh(run)
        return run
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(ExecutionRun).where(
                ExecutionRun.definition_id == definition_id,
                ExecutionRun.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        return existing


async def read_runs(
    db: AsyncSession,
    *,
    definition_id: int,
    cursor: int | None,
    limit: int,
) -> tuple[list[ExecutionRun], int | None]:
    after = cursor or 0
    clamped = min(max(limit, 1), MAX_LIMIT)

    res = await db.execute(
        select(ExecutionRun)
        .where(ExecutionRun.definition_id == definition_id, ExecutionRun.id > after)
        .order_by(ExecutionRun.id.asc())
        .limit(clamped + 1)
    )
    rows = list(res.scalars().all())
    if len(rows) <= clamped:
        return rows, None

    page = rows[:clamped]
    next_cursor = page[-1].id
    return page, next_cursor


async def read_definitions(
    db: AsyncSession,
    *,
    cursor: int | None,
    limit: int,
) -> tuple[list[ExecutionDefinition], int | None]:
    after = cursor or 0
    clamped = min(max(limit, 1), MAX_LIMIT)

    res = await db.execute(
        select(ExecutionDefinition)
        .where(ExecutionDefinition.id > after)
        .order_by(ExecutionDefinition.id.asc())
        .limit(clamped + 1)
    )
    rows = list(res.scalars().all())
    if len(rows) <= clamped:
        return rows, None

    page = rows[:clamped]
    next_cursor = page[-1].id
    return page, next_cursor
