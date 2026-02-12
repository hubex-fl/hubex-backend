from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.signals import DEFAULT_LIMIT, MAX_LIMIT, read_signals


router = APIRouter(prefix="/signals", tags=["signals"])


class SignalOut(BaseModel):
    id: int
    stream: str
    signal_type: str
    payload: dict
    provider_instance_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignalReadOut(BaseModel):
    items: list[SignalOut]
    next_cursor: int | None


@router.get("", response_model=SignalReadOut)
async def list_signals(
    stream: str = Query(..., min_length=1, max_length=128),
    cursor: int | None = Query(default=None, ge=0),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    eff_limit = DEFAULT_LIMIT if limit is None else min(max(limit, 1), MAX_LIMIT)
    items, next_cursor = await read_signals(db, stream=stream, cursor=cursor, limit=eff_limit)
    return SignalReadOut(items=items, next_cursor=next_cursor)

