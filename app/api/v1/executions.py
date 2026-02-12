from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.executions import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    create_definition,
    create_run_idempotent,
    read_runs,
)
from app.db.models.executions import ExecutionDefinition, ExecutionRun


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


class ExecutionRunIn(BaseModel):
    definition_key: str
    idempotency_key: str
    requested_by: str | None = None
    input_json: dict


@router.get("/runs", response_model=ExecutionRunReadOut)
async def list_execution_runs(
    definition_key: str = Query(..., min_length=1, max_length=96),
    cursor: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    definition = await db.scalar(select(ExecutionDefinition).where(ExecutionDefinition.key == definition_key))
    if definition is None:
        raise HTTPException(status_code=404, detail="definition not found")

    eff_limit = DEFAULT_LIMIT if limit is None else min(max(limit, 1), MAX_LIMIT)
    items, next_cursor = await read_runs(db, definition_id=definition.id, cursor=cursor, limit=eff_limit)
    return ExecutionRunReadOut(items=items, next_cursor=next_cursor)


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
