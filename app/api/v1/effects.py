from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.effects import EffectV1

router = APIRouter(prefix="/effects", tags=["effects"])


class EffectOut(BaseModel):
    id: int
    created_at: datetime
    effect_id: str
    source_event_id: int | None
    kind: str
    status: str
    payload_json: dict
    error_json: dict | None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[EffectOut])
async def list_effects(
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(100, ge=1, le=500),
    kind: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(EffectV1)
    if after_id is not None:
        stmt = stmt.where(EffectV1.id > after_id)
    if kind:
        stmt = stmt.where(EffectV1.kind == kind)
    res = await db.execute(stmt.order_by(EffectV1.id.asc()).limit(limit))
    return list(res.scalars().all())


@router.get("/{effect_id}", response_model=EffectOut)
async def get_effect(
    effect_id: str,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(EffectV1).where(EffectV1.effect_id == effect_id))
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="effect not found")
    return row
