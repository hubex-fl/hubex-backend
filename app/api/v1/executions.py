from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.executions import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ClaimConflictError,
    ClaimNotFoundError,
    claim_run,
    extend_lease,
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


class ExecutionRunIn(BaseModel):
    definition_key: str
    idempotency_key: str
    requested_by: str | None = None
    input_json: dict


class ExecutionFinalizeIn(BaseModel):
    status: str
    output_json: dict | None = None
    error_json: dict | None = None


class ExecutionClaimIn(BaseModel):
    worker_id: str
    lease_seconds: int | None = 60


class ExecutionLeaseIn(BaseModel):
    worker_id: str
    lease_seconds: int | None = 60


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

    stmt = (
        update(ExecutionRun)
        .where(ExecutionRun.id == run_id, ExecutionRun.status == RUN_STATUS_REQUESTED)
        .values(
            status=data.status,
            output_json=data.output_json,
            error_json=data.error_json,
            updated_at=func.now(),
        )
        .returning(ExecutionRun)
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


@router.get("/runs/{run_id}", response_model=ExecutionRunOut)
async def get_execution_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
):
    run = await db.scalar(select(ExecutionRun).where(ExecutionRun.id == run_id))
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return ExecutionRunOut.model_validate(run)
