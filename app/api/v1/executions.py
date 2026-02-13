from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.execution_workers import (
    WorkerNotFoundError,
    read_definition_workers,
    read_worker_definitions,
    read_workers,
    set_worker_definitions,
    upsert_worker_heartbeat,
)
from app.core.executions import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ClaimConflictError,
    ClaimNotFoundError,
    claim_run,
    claim_next_run,
    extend_lease,
    release_claim,
    create_definition,
    create_run_idempotent,
    read_definitions,
    read_runs,
)
from app.db.models.executions import (
    ExecutionDefinition,
    ExecutionRun,
    RUN_STATUS_CANCELED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_FINAL,
    RUN_STATUS_REQUESTED,
)


router = APIRouter(prefix="/executions", tags=["executions"])


class ExecutionRunOut(BaseModel):
    id: int
    definition_id: int
    idempotency_key: str
    requested_by: str | None
    status: str
    input_json: dict
    output_json: dict | None
    error_json: dict | None
    claimed_by: str | None
    claimed_at: datetime | None
    lease_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionRunReadOut(BaseModel):
    items: list[ExecutionRunOut]
    next_cursor: int | None


class ExecutionDefinitionIn(BaseModel):
    key: str
    name: str
    version: str
    enabled: bool | None = True


class ExecutionDefinitionOut(BaseModel):
    id: int
    key: str
    name: str
    version: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionDefinitionReadOut(BaseModel):
    items: list[ExecutionDefinitionOut]
    next_cursor: int | None


class ExecutionWorkerIn(BaseModel):
    worker_id: str
    meta_json: dict | None = None


class ExecutionWorkerOut(BaseModel):
    id: str
    last_seen_at: datetime
    meta_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionWorkerReadOut(BaseModel):
    items: list[ExecutionWorkerOut]
    next_cursor: str | None


class ExecutionWorkerDefinitionsIn(BaseModel):
    definition_keys: list[str]


class ExecutionWorkerDefinitionsOut(BaseModel):
    worker_id: str
    definition_keys: list[str]


class ExecutionDefinitionWorkersOut(BaseModel):
    definition_key: str
    worker_ids: list[str]


class ExecutionRunIn(BaseModel):
    definition_key: str
    idempotency_key: str
    requested_by: str | None = None
    input_json: dict


class ExecutionFinalizeIn(BaseModel):
    status: str
    output_json: dict | None = None
    error_json: dict | None = None
    worker_id: str | None = None


class ExecutionClaimIn(BaseModel):
    worker_id: str
    lease_seconds: int | None = 60


class ExecutionLeaseIn(BaseModel):
    worker_id: str
    lease_seconds: int | None = 60


class ExecutionClaimNextIn(BaseModel):
    definition_key: str
    worker_id: str
    lease_seconds: int | None = 60


class ExecutionReleaseIn(BaseModel):
    worker_id: str


@router.get("/runs", response_model=ExecutionRunReadOut)
async def list_execution_runs(
    definition_key: str = Query(..., min_length=1, max_length=96),
    status: str | None = Query(default=None, min_length=1, max_length=24),
    cursor: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    if status is not None and status not in {
        RUN_STATUS_REQUESTED,
        RUN_STATUS_COMPLETED,
        RUN_STATUS_FAILED,
        RUN_STATUS_CANCELED,
    }:
        raise HTTPException(status_code=400, detail="invalid status")

    definition = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == definition_key))
    if definition is None:
        raise HTTPException(status_code=404, detail="definition not found")

    eff_limit = DEFAULT_LIMIT if limit is None else min(max(limit, 1), MAX_LIMIT)
    items, next_cursor = await read_runs(
        db,
        definition_id=definition.id,
        status=status,
        cursor=cursor,
        limit=eff_limit,
    )
    return ExecutionRunReadOut(items=items, next_cursor=next_cursor)


@router.get("/definitions", response_model=ExecutionDefinitionReadOut)
async def list_execution_definitions(
    cursor: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    eff_limit = DEFAULT_LIMIT if limit is None else min(max(limit, 1), MAX_LIMIT)
    items, next_cursor = await read_definitions(db, cursor=cursor, limit=eff_limit)
    return ExecutionDefinitionReadOut(items=items, next_cursor=next_cursor)


@router.post("/workers/heartbeat", response_model=ExecutionWorkerOut)
async def upsert_execution_worker_heartbeat(
    data: ExecutionWorkerIn,
    db: AsyncSession = Depends(get_db),
):
    worker_id = data.worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")
    worker = await upsert_worker_heartbeat(db, worker_id=worker_id, meta_json=data.meta_json)
    return ExecutionWorkerOut.model_validate(worker)


@router.get("/workers", response_model=ExecutionWorkerReadOut)
async def list_execution_workers(
    cursor: str | None = Query(default=None, min_length=1, max_length=96),
    limit: int | None = Query(default=None, ge=1),
    active_within_seconds: int | None = Query(default=None, ge=1, le=86400),
    db: AsyncSession = Depends(get_db),
):
    eff_limit = DEFAULT_LIMIT if limit is None else min(max(limit, 1), MAX_LIMIT)
    items, next_cursor = await read_workers(
        db,
        cursor=cursor,
        limit=eff_limit,
        active_within_seconds=active_within_seconds,
    )
    return ExecutionWorkerReadOut(items=items, next_cursor=next_cursor)


@router.post("/workers/{worker_id}/definitions", response_model=ExecutionWorkerDefinitionsOut)
async def set_execution_worker_definitions(
    worker_id: str,
    data: ExecutionWorkerDefinitionsIn,
    db: AsyncSession = Depends(get_db),
):
    worker_id = worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")
    if not data.definition_keys or len(data.definition_keys) > 100:
        raise HTTPException(status_code=400, detail="invalid definition_keys")

    keys: list[str] = []
    for key in data.definition_keys:
        key = key.strip()
        if not (1 <= len(key) <= 96):
            raise HTTPException(status_code=400, detail="invalid definition_keys")
        keys.append(key)
    unique_keys = list(dict.fromkeys(keys))

    res = await db.execute(
        select(ExecutionDefinition).where(ExecutionDefinition.key.in_(unique_keys))
    )
    defs = res.scalars().all()
    if len(defs) != len(unique_keys):
        raise HTTPException(status_code=404, detail="definition not found")
    defs_by_key = {d.key: d for d in defs}
    definition_ids = [defs_by_key[k].id for k in unique_keys]

    try:
        await set_worker_definitions(db, worker_id=worker_id, definition_ids=definition_ids)
    except WorkerNotFoundError:
        raise HTTPException(status_code=404, detail="worker not found")

    return ExecutionWorkerDefinitionsOut(worker_id=worker_id, definition_keys=unique_keys)


@router.get("/workers/{worker_id}/definitions", response_model=ExecutionWorkerDefinitionsOut)
async def get_execution_worker_definitions(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
):
    worker_id = worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")
    try:
        definition_ids = await read_worker_definitions(db, worker_id=worker_id)
    except WorkerNotFoundError:
        raise HTTPException(status_code=404, detail="worker not found")

    if not definition_ids:
        return ExecutionWorkerDefinitionsOut(worker_id=worker_id, definition_keys=[])

    res = await db.execute(
        select(ExecutionDefinition.id, ExecutionDefinition.key).where(
            ExecutionDefinition.id.in_(definition_ids)
        )
    )
    by_id = {row.id: row.key for row in res.all()}
    keys = [by_id[definition_id] for definition_id in definition_ids if definition_id in by_id]
    return ExecutionWorkerDefinitionsOut(worker_id=worker_id, definition_keys=keys)


@router.get("/definitions/{definition_key}/workers", response_model=ExecutionDefinitionWorkersOut)
async def get_execution_definition_workers(
    definition_key: str,
    active_within_seconds: int | None = Query(default=None, ge=1, le=86400),
    db: AsyncSession = Depends(get_db),
):
    definition_key = definition_key.strip()
    if not (1 <= len(definition_key) <= 96):
        raise HTTPException(status_code=400, detail="invalid definition_key")

    definition = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == definition_key))
    if definition is None:
        raise HTTPException(status_code=404, detail="definition not found")

    worker_ids = await read_definition_workers(
        db,
        definition_id=definition.id,
        active_within_seconds=active_within_seconds,
    )
    return ExecutionDefinitionWorkersOut(definition_key=definition_key, worker_ids=worker_ids)


@router.get("/definitions/{definition_key}", response_model=ExecutionDefinitionOut)
async def get_execution_definition(
    definition_key: str,
    db: AsyncSession = Depends(get_db),
):
    definition = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == definition_key))
    if definition is None:
        raise HTTPException(status_code=404, detail="definition not found")
    return ExecutionDefinitionOut.model_validate(definition)


@router.post("/definitions", response_model=ExecutionDefinitionOut)
async def create_execution_definition(
    data: ExecutionDefinitionIn,
    db: AsyncSession = Depends(get_db),
):
    definition = await create_definition(
        db,
        key=data.key,
        name=data.name,
        version=data.version,
        enabled=bool(data.enabled),
    )
    return ExecutionDefinitionOut.model_validate(definition)


@router.post("/runs", response_model=ExecutionRunOut)
async def create_execution_run(
    data: ExecutionRunIn,
    db: AsyncSession = Depends(get_db),
):
    definition = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == data.definition_key))
    if definition is None:
        raise HTTPException(status_code=404, detail="definition not found")

    run = await create_run_idempotent(
        db,
        definition_id=definition.id,
        idempotency_key=data.idempotency_key,
        requested_by=data.requested_by,
        input_json=data.input_json,
    )
    return ExecutionRunOut.model_validate(run)


@router.post("/runs/{run_id}/finalize", response_model=ExecutionRunOut)
async def finalize_execution_run(
    run_id: int,
    data: ExecutionFinalizeIn,
    db: AsyncSession = Depends(get_db),
):
    worker_id = data.worker_id.strip() if data.worker_id is not None else None
    if worker_id is not None and not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")

    if data.status not in {RUN_STATUS_COMPLETED, RUN_STATUS_FAILED, RUN_STATUS_CANCELED}:
        raise HTTPException(status_code=400, detail="invalid status")

    if data.status == RUN_STATUS_COMPLETED:
        if data.output_json is None:
            raise HTTPException(status_code=400, detail="completed requires output_json")
        if data.error_json is not None:
            raise HTTPException(status_code=400, detail="completed forbids error_json")
    elif data.status == RUN_STATUS_FAILED:
        if data.error_json is None:
            raise HTTPException(status_code=400, detail="failed requires error_json")
        if data.output_json is not None:
            raise HTTPException(status_code=400, detail="failed forbids output_json")
    elif data.status == RUN_STATUS_CANCELED:
        if data.output_json is not None or data.error_json is not None:
            raise HTTPException(status_code=400, detail="canceled forbids output_json and error_json")

    ownership_guard = or_(
        ExecutionRun.claimed_by.is_(None),
        ExecutionRun.lease_expires_at.is_(None),
        ExecutionRun.lease_expires_at <= func.now(),
    )
    if worker_id is not None:
        ownership_guard = or_(
            ownership_guard,
            and_(
                ExecutionRun.claimed_by == worker_id,
                ExecutionRun.lease_expires_at > func.now(),
            ),
        )

    stmt = (
        update(ExecutionRun)
        .where(
            ExecutionRun.id == run_id,
            ExecutionRun.status == RUN_STATUS_REQUESTED,
            ownership_guard,
        )
        .values(
            status=data.status,
            output_json=data.output_json,
            error_json=data.error_json,
            updated_at=func.now(),
        )
        .returning(ExecutionRun)
        .execution_options(synchronize_session=False)
    )
    res = await db.execute(stmt)
    updated = res.scalar_one_or_none()
    if updated is not None:
        await db.commit()
        return ExecutionRunOut.model_validate(updated)

    run = await db.scalar(select(ExecutionRun).where(ExecutionRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    if run.status in RUN_STATUS_FINAL:
        if (
            run.status == data.status
            and run.output_json == data.output_json
            and run.error_json == data.error_json
        ):
            return ExecutionRunOut.model_validate(run)
        raise HTTPException(status_code=409, detail="run already finalized with different payload")

    now = datetime.now(run.lease_expires_at.tzinfo) if run.lease_expires_at is not None else datetime.now()
    lease_at = run.lease_expires_at
    if lease_at is not None and lease_at.tzinfo is None:
        lease_at = lease_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
    elif lease_at is not None and lease_at.tzinfo is not None:
        now = datetime.now(lease_at.tzinfo)

    if (
        run.claimed_by is not None
        and lease_at is not None
        and lease_at > now
        and run.claimed_by != worker_id
    ):
        raise HTTPException(status_code=409, detail="run already claimed")

    raise HTTPException(status_code=409, detail="run status not finalizable")


@router.post("/runs/{run_id}/claim", response_model=ExecutionRunOut)
async def claim_execution_run(
    run_id: int,
    data: ExecutionClaimIn,
    db: AsyncSession = Depends(get_db),
):
    worker_id = data.worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")
    lease_seconds = 60 if data.lease_seconds is None else data.lease_seconds
    if not (1 <= lease_seconds <= 3600):
        raise HTTPException(status_code=400, detail="invalid lease_seconds")

    try:
        run = await claim_run(
            db,
            run_id=run_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail="run not found")
    except ClaimConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ExecutionRunOut.model_validate(run)


@router.post("/runs/{run_id}/lease", response_model=ExecutionRunOut)
async def extend_execution_run_lease(
    run_id: int,
    data: ExecutionLeaseIn,
    db: AsyncSession = Depends(get_db),
):
    worker_id = data.worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")
    lease_seconds = 60 if data.lease_seconds is None else data.lease_seconds
    if not (1 <= lease_seconds <= 3600):
        raise HTTPException(status_code=400, detail="invalid lease_seconds")

    try:
        run = await extend_lease(
            db,
            run_id=run_id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail="run not found")
    except ClaimConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ExecutionRunOut.model_validate(run)


@router.post("/runs/claim-next", response_model=ExecutionRunOut)
async def claim_next_execution_run(
    data: ExecutionClaimNextIn,
    db: AsyncSession = Depends(get_db),
):
    definition_key = data.definition_key.strip()
    if not (1 <= len(definition_key) <= 96):
        raise HTTPException(status_code=400, detail="invalid definition_key")

    worker_id = data.worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")
    lease_seconds = 60 if data.lease_seconds is None else data.lease_seconds
    if not (1 <= lease_seconds <= 3600):
        raise HTTPException(status_code=400, detail="invalid lease_seconds")

    definition = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == definition_key))
    if definition is None:
        raise HTTPException(status_code=404, detail="definition not found")

    try:
        run = await claim_next_run(
            db,
            definition_id=definition.id,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )
    except ClaimNotFoundError as exc:
        detail = str(exc)
        raise HTTPException(status_code=404, detail=detail)
    except ClaimConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ExecutionRunOut.model_validate(run)


@router.post("/runs/{run_id}/release", response_model=ExecutionRunOut)
async def release_execution_run(
    run_id: int,
    data: ExecutionReleaseIn,
    db: AsyncSession = Depends(get_db),
):
    worker_id = data.worker_id.strip()
    if not (1 <= len(worker_id) <= 96):
        raise HTTPException(status_code=400, detail="invalid worker_id")

    try:
        run = await release_claim(db, run_id=run_id, worker_id=worker_id)
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail="run not found")
    except ClaimConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return ExecutionRunOut.model_validate(run)


@router.get("/runs/{run_id}", response_model=ExecutionRunOut)
async def get_execution_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    run = await db.scalar(select(ExecutionRun).where(ExecutionRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return ExecutionRunOut.model_validate(run)
