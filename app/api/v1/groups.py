"""Group shortcuts — Groups are Entities with type="group"."""
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.entities import (
    EntityOut,
    EntityDeviceBindingOut,
    EntityCreateIn,
    _get_entity_or_404,
)
from app.core.system_events import emit_system_event
from app.db.models.entities import Entity, EntityDeviceBinding

router = APIRouter(prefix="/groups", tags=["groups"])

GROUP_TYPE = "group"


class GroupCreateIn(BaseModel):
    entity_id: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    tags: list | dict | None = None

    model_config = ConfigDict(extra="ignore")


@router.get("", response_model=list[EntityOut])
async def list_groups(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Entity).where(Entity.type == GROUP_TYPE).order_by(Entity.entity_id)
    )
    return list(res.scalars().all())


@router.post("", response_model=EntityOut)
async def create_group(
    data: GroupCreateIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Entity).where(Entity.entity_id == data.entity_id))
    existing = res.scalar_one_or_none()
    if existing is not None:
        response.status_code = 200
        return existing

    entity = Entity(
        entity_id=data.entity_id,
        type=GROUP_TYPE,
        name=data.name,
        tags=data.tags,
    )
    db.add(entity)
    await emit_system_event(db, "entity.created", {
        "entity_id": data.entity_id,
        "type": GROUP_TYPE,
    })
    await db.commit()
    await db.refresh(entity)
    response.status_code = 201
    return entity


@router.get("/{group_id}/devices", response_model=list[EntityDeviceBindingOut])
async def list_group_devices(
    group_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(group_id, db)
    res = await db.execute(
        select(EntityDeviceBinding).where(EntityDeviceBinding.entity_id == group_id)
    )
    return list(res.scalars().all())
