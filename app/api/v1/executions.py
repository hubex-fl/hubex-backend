from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.executions import DEFAULT_LIMIT, MAX_LIMIT, read_runs
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
