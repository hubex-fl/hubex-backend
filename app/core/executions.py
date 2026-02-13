from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.executions import (
    ExecutionDefinition,
    ExecutionRun,
    RUN_STATUS_FINAL,
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
    status: str | None,
    cursor: int | None,
    limit: int,
) -> tuple[list[ExecutionRun], int | None]:
    after = cursor or 0
    clamped = min(max(limit, 1), MAX_LIMIT)

    stmt = (
        select(ExecutionRun)
        .where(ExecutionRun.definition_id == definition_id, ExecutionRun.id > after)
        .order_by(ExecutionRun.id.asc())
        .limit(clamped + 1)
    )
    if status is not None:
        stmt = stmt.where(ExecutionRun.status == status)

    res = await db.execute(stmt)
    rows = list(res.scalars().all())
    if len(rows) <= clamped:
        return rows, None

    page = rows[:clamped]
    next_cursor = page[-1].id
    return page, next_cursor


class ClaimConflictError(RuntimeError):
    pass


class ClaimNotFoundError(RuntimeError):
    pass


async def claim_run(
    db: AsyncSession,
    *,
    run_id: int,
    worker_id: str,
    lease_seconds: int,
) -> ExecutionRun:
    now = datetime.now(timezone.utc)
    lease_expires_at = now + timedelta(seconds=lease_seconds)

    stmt = (
        update(ExecutionRun)
        .where(
            ExecutionRun.id == run_id,
            ExecutionRun.status == RUN_STATUS_REQUESTED,
            or_(
                ExecutionRun.claimed_by.is_(None),
                ExecutionRun.lease_expires_at.is_(None),
                ExecutionRun.lease_expires_at < now,
            ),
        )
        .values(
            claimed_by=worker_id,
            claimed_at=now,
            lease_expires_at=lease_expires_at,
        )
        .returning(ExecutionRun)
        .execution_options(synchronize_session=False)
    )
    res = await db.execute(stmt)
    updated = res.scalar_one_or_none()
    if updated is not None:
        await db.commit()
        return updated

    run = await db.scalar(select(ExecutionRun).where(ExecutionRun.id == run_id))
    if run is None:
        raise ClaimNotFoundError("run not found")
    if run.status in RUN_STATUS_FINAL or run.status != RUN_STATUS_REQUESTED:
        raise ClaimConflictError("run status not claimable")

    lease_at = _as_aware(run.lease_expires_at)
    if (
        run.claimed_by == worker_id
        and lease_at is not None
        and lease_at > now
    ):
        return run

    if run.claimed_by is not None and lease_at is not None and lease_at > now:
        raise ClaimConflictError("run already claimed")

    if run.claimed_by is None or lease_at is None or lease_at <= now:
        res2 = await db.execute(stmt)
        updated2 = res2.scalar_one_or_none()
        if updated2 is not None:
            await db.commit()
            return updated2

    raise ClaimConflictError("run not claimable")


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def extend_lease(
    db: AsyncSession,
    *,
    run_id: int,
    worker_id: str,
    lease_seconds: int,
) -> ExecutionRun:
    now = datetime.now(timezone.utc)
    lease_expires_at = now + timedelta(seconds=lease_seconds)

    stmt = (
        update(ExecutionRun)
        .where(
            ExecutionRun.id == run_id,
            ExecutionRun.status == RUN_STATUS_REQUESTED,
            ExecutionRun.claimed_by == worker_id,
            ExecutionRun.lease_expires_at.is_not(None),
            ExecutionRun.lease_expires_at > now,
        )
        .values(
            lease_expires_at=lease_expires_at,
            updated_at=now,
        )
        .returning(ExecutionRun)
        .execution_options(synchronize_session=False)
    )
    res = await db.execute(stmt)
    updated = res.scalar_one_or_none()
    if updated is not None:
        await db.commit()
        return updated

    run = await db.scalar(select(ExecutionRun).where(ExecutionRun.id == run_id))
    if run is None:
        raise ClaimNotFoundError("run not found")
    if run.status in RUN_STATUS_FINAL or run.status != RUN_STATUS_REQUESTED:
        raise ClaimConflictError("run status not leasable")

    lease_at = _as_aware(run.lease_expires_at)
    if run.claimed_by != worker_id and lease_at is not None and lease_at > now:
        raise ClaimConflictError("run already claimed")

    raise ClaimConflictError("lease expired or not owned")


async def claim_next_run(
    db: AsyncSession,
    *,
    definition_id: int,
    worker_id: str,
    lease_seconds: int,
    max_attempts: int = 5,
) -> ExecutionRun:
    attempts = max(1, max_attempts)
    for _ in range(attempts):
        now = datetime.now(timezone.utc)
        res = await db.execute(
            select(ExecutionRun.id)
            .where(
                ExecutionRun.definition_id == definition_id,
                ExecutionRun.status == RUN_STATUS_REQUESTED,
                or_(
                    ExecutionRun.claimed_by.is_(None),
                    ExecutionRun.lease_expires_at.is_(None),
                    ExecutionRun.lease_expires_at < now,
                ),
            )
            .order_by(ExecutionRun.id.asc())
            .limit(1)
        )
        candidate_id = res.scalar_one_or_none()
        if candidate_id is None:
            res_same = await db.execute(
                select(ExecutionRun.id)
                .where(
                    ExecutionRun.definition_id == definition_id,
                    ExecutionRun.status == RUN_STATUS_REQUESTED,
                    ExecutionRun.claimed_by == worker_id,
                    ExecutionRun.lease_expires_at > now,
                )
                .order_by(ExecutionRun.id.asc())
                .limit(1)
            )
            candidate_id = res_same.scalar_one_or_none()
        if candidate_id is None:
            raise ClaimNotFoundError("no run available")
        try:
            return await claim_run(
                db,
                run_id=candidate_id,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )
        except ClaimConflictError:
            continue

    raise ClaimConflictError("no run available")


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
