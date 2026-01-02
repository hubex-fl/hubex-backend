from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.entities import Entity, EntityDeviceBinding

router = APIRouter(prefix="/entities", tags=["entities"])


class EntityOut(BaseModel):
    entity_id: str
    type: str
    name: str | None
    tags: list | dict | None
    health_last_seen_at: datetime | None
    health_status: str | None

    model_config = ConfigDict(from_attributes=True)


class EntityDeviceBindingOut(BaseModel):
    device_id: int
    enabled: bool
    priority: int

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[EntityOut])
async def list_entities(
    type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Entity)
    if type:
        stmt = stmt.where(Entity.type == type)
    res = await db.execute(stmt.order_by(Entity.entity_id))
    return list(res.scalars().all())


@router.get("/{entity_id}", response_model=EntityOut)
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    entity = res.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return entity


@router.get("/{entity_id}/devices", response_model=list[EntityDeviceBindingOut])
async def list_entity_devices(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(EntityDeviceBinding).where(EntityDeviceBinding.entity_id == entity_id)
    )
    return list(res.scalars().all())
