from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.system_events import emit_system_event
from app.db.models.device import Device
from app.db.models.entities import Entity, EntityDeviceBinding

router = APIRouter(prefix="/entities", tags=["entities"])

ONLINE_WINDOW_SECONDS = 30
STALE_WINDOW_SECONDS = 120


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EntityOut(BaseModel):
    entity_id: str
    type: str
    name: str | None
    tags: list | dict | None
    health_last_seen_at: datetime | None
    health_status: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityDeviceBindingOut(BaseModel):
    device_id: int
    enabled: bool
    priority: int

    model_config = ConfigDict(from_attributes=True)


class EntityCreateIn(BaseModel):
    entity_id: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    tags: list | dict | None = None

    model_config = ConfigDict(extra="ignore")


class EntityUpdateIn(BaseModel):
    type: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=128)
    tags: list | dict | None = None

    model_config = ConfigDict(extra="ignore")


class DeviceBindIn(BaseModel):
    device_ids: list[int] = Field(min_length=1)
    priority: int = 0
    enabled: bool = True

    model_config = ConfigDict(extra="ignore")


class DeviceBindingUpdateIn(BaseModel):
    priority: int | None = None
    enabled: bool | None = None

    model_config = ConfigDict(extra="ignore")


class BulkBindIn(BaseModel):
    device_ids: list[int] = Field(min_length=1)
    priority: int = 0
    enabled: bool = True

    model_config = ConfigDict(extra="ignore")


class BulkUnbindIn(BaseModel):
    device_ids: list[int] = Field(min_length=1)

    model_config = ConfigDict(extra="ignore")


class BulkOpResult(BaseModel):
    device_id: int
    ok: bool
    error: str | None = None


class BulkOpOut(BaseModel):
    results: list[BulkOpResult]


class EntityHealthOut(BaseModel):
    entity_id: str
    device_count: int
    online: int
    stale: int
    offline: int
    worst_health: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_entity_or_404(entity_id: str, db: AsyncSession) -> Entity:
    res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    entity = res.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return entity


async def _get_device_or_404(device_id: int, db: AsyncSession) -> Device:
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail=f"device {device_id} not found")
    return device


async def _get_binding(entity_id: str, device_id: int, db: AsyncSession) -> EntityDeviceBinding | None:
    res = await db.execute(
        select(EntityDeviceBinding).where(
            EntityDeviceBinding.entity_id == entity_id,
            EntityDeviceBinding.device_id == device_id,
        )
    )
    return res.scalar_one_or_none()


def _device_health_status(last_seen_at: datetime | None, now: datetime) -> str:
    if last_seen_at is None:
        return "offline"
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    age = (now - last_seen_at).total_seconds()
    if age <= ONLINE_WINDOW_SECONDS:
        return "ok"
    if age <= STALE_WINDOW_SECONDS:
        return "stale"
    return "offline"


_HEALTH_RANK = {"offline": 0, "stale": 1, "ok": 2}


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

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


@router.get("/{entity_id}/health", response_model=EntityHealthOut)
async def get_entity_health(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(entity_id, db)

    res = await db.execute(
        select(Device.last_seen_at)
        .join(EntityDeviceBinding, EntityDeviceBinding.device_id == Device.id)
        .where(
            EntityDeviceBinding.entity_id == entity_id,
            EntityDeviceBinding.enabled.is_(True),
        )
    )
    last_seen_values = res.scalars().all()

    now = datetime.now(timezone.utc)
    counts = {"ok": 0, "stale": 0, "offline": 0}
    for lsa in last_seen_values:
        status = _device_health_status(lsa, now)
        counts[status] = counts.get(status, 0) + 1

    device_count = len(last_seen_values)
    if device_count == 0:
        worst = "unknown"
    else:
        worst = min(counts, key=lambda k: _HEALTH_RANK.get(k, 2) if counts[k] > 0 else 999)
        # worst = the status with the lowest rank that has at least one device
        worst = min(
            (k for k, v in counts.items() if v > 0),
            key=lambda k: _HEALTH_RANK.get(k, 2),
            default="unknown",
        )

    return EntityHealthOut(
        entity_id=entity_id,
        device_count=device_count,
        online=counts["ok"],
        stale=counts["stale"],
        offline=counts["offline"],
        worst_health=worst,
    )


@router.get("/{entity_id}/devices", response_model=list[EntityDeviceBindingOut])
async def list_entity_devices(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(EntityDeviceBinding).where(EntityDeviceBinding.entity_id == entity_id)
    )
    return list(res.scalars().all())


@router.get("/{entity_id}", response_model=EntityOut)
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await _get_entity_or_404(entity_id, db)


# ---------------------------------------------------------------------------
# Entity write endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=EntityOut)
async def create_entity(
    data: EntityCreateIn,
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
        type=data.type,
        name=data.name,
        tags=data.tags,
    )
    db.add(entity)
    await emit_system_event(db, "entity.created", {
        "entity_id": data.entity_id,
        "type": data.type,
    })
    await db.commit()
    await db.refresh(entity)
    response.status_code = 201
    return entity


@router.put("/{entity_id}", response_model=EntityOut)
async def update_entity(
    entity_id: str,
    data: EntityUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    entity = await _get_entity_or_404(entity_id, db)
    if data.type is not None:
        entity.type = data.type
    if data.name is not None:
        entity.name = data.name
    if data.tags is not None:
        entity.tags = data.tags
    await emit_system_event(db, "entity.updated", {"entity_id": entity_id})
    await db.commit()
    await db.refresh(entity)
    return entity


@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
):
    entity = await _get_entity_or_404(entity_id, db)
    await db.execute(
        delete(EntityDeviceBinding).where(EntityDeviceBinding.entity_id == entity_id)
    )
    await db.delete(entity)
    await emit_system_event(db, "entity.deleted", {"entity_id": entity_id})
    await db.commit()


# ---------------------------------------------------------------------------
# Device binding write endpoints
# (bulk-* routes must be defined before /{device_id} to avoid path conflicts)
# ---------------------------------------------------------------------------

@router.post("/{entity_id}/devices/bulk-bind", response_model=BulkOpOut)
async def bulk_bind_devices(
    entity_id: str,
    data: BulkBindIn,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(entity_id, db)
    results: list[BulkOpResult] = []

    for device_id in data.device_ids:
        try:
            async with db.begin_nested():
                device = await db.get(Device, device_id)
                if device is None:
                    results.append(BulkOpResult(device_id=device_id, ok=False, error="device_not_found"))
                    continue
                existing = await _get_binding(entity_id, device_id, db)
                if existing is not None:
                    results.append(BulkOpResult(device_id=device_id, ok=False, error="already_bound"))
                    continue
                db.add(EntityDeviceBinding(
                    entity_id=entity_id,
                    device_id=device_id,
                    priority=data.priority,
                    enabled=data.enabled,
                ))
                await emit_system_event(db, "entity.device.bound", {
                    "entity_id": entity_id,
                    "device_id": device_id,
                })
            results.append(BulkOpResult(device_id=device_id, ok=True))
        except Exception as exc:
            results.append(BulkOpResult(device_id=device_id, ok=False, error=str(exc)))

    await db.commit()
    return BulkOpOut(results=results)


@router.post("/{entity_id}/devices/bulk-unbind", response_model=BulkOpOut)
async def bulk_unbind_devices(
    entity_id: str,
    data: BulkUnbindIn,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(entity_id, db)
    results: list[BulkOpResult] = []

    for device_id in data.device_ids:
        try:
            async with db.begin_nested():
                binding = await _get_binding(entity_id, device_id, db)
                if binding is None:
                    results.append(BulkOpResult(device_id=device_id, ok=False, error="not_bound"))
                    continue
                await db.delete(binding)
                await emit_system_event(db, "entity.device.unbound", {
                    "entity_id": entity_id,
                    "device_id": device_id,
                })
            results.append(BulkOpResult(device_id=device_id, ok=True))
        except Exception as exc:
            results.append(BulkOpResult(device_id=device_id, ok=False, error=str(exc)))

    await db.commit()
    return BulkOpOut(results=results)


@router.post("/{entity_id}/devices", response_model=list[EntityDeviceBindingOut], status_code=201)
async def bind_devices(
    entity_id: str,
    data: DeviceBindIn,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(entity_id, db)
    created: list[EntityDeviceBinding] = []

    for device_id in data.device_ids:
        await _get_device_or_404(device_id, db)
        existing = await _get_binding(entity_id, device_id, db)
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"device {device_id} already bound")
        binding = EntityDeviceBinding(
            entity_id=entity_id,
            device_id=device_id,
            priority=data.priority,
            enabled=data.enabled,
        )
        db.add(binding)
        created.append(binding)

    for device_id in data.device_ids:
        await emit_system_event(db, "entity.device.bound", {
            "entity_id": entity_id,
            "device_id": device_id,
        })
    await db.commit()
    for b in created:
        await db.refresh(b)
    return [EntityDeviceBindingOut(device_id=b.device_id, enabled=b.enabled, priority=b.priority) for b in created]


@router.put("/{entity_id}/devices/{device_id}", response_model=EntityDeviceBindingOut)
async def update_binding(
    entity_id: str,
    device_id: int,
    data: DeviceBindingUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(entity_id, db)
    binding = await _get_binding(entity_id, device_id, db)
    if binding is None:
        raise HTTPException(status_code=404, detail="binding not found")
    if data.priority is not None:
        binding.priority = data.priority
    if data.enabled is not None:
        binding.enabled = data.enabled
    await db.commit()
    await db.refresh(binding)
    return binding


@router.delete("/{entity_id}/devices/{device_id}", status_code=204)
async def unbind_device(
    entity_id: str,
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    await _get_entity_or_404(entity_id, db)
    binding = await _get_binding(entity_id, device_id, db)
    if binding is None:
        raise HTTPException(status_code=404, detail="binding not found")
    await db.delete(binding)
    await emit_system_event(db, "entity.device.unbound", {
        "entity_id": entity_id,
        "device_id": device_id,
    })
    await db.commit()
