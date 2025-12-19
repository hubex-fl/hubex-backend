from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device, get_current_user
from app.db.models.device import Device  # NUR das echte Model importieren
from app.db.models.user import User
from app.api.v1.validators import validate_json_object
from app.db.models.telemetry import DeviceTelemetry
from app.db.models.tasks import ExecutionContext, Task

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceHelloIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=128)
    firmware_version: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None


class DeviceHelloOut(BaseModel):
    device_id: int
    claimed: bool


class DeviceOut(BaseModel):
    id: int
    device_uid: str
    name: Optional[str]
    firmware_version: Optional[str]
    capabilities: Optional[Dict[str, Any]]
    last_seen_at: Optional[datetime]
    owner_user_id: Optional[int]
    is_claimed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserTelemetryOut(BaseModel):
    id: int
    created_at: datetime
    event_type: Optional[str]
    payload: Optional[Dict[str, Any]]


class UserTaskCreateIn(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    payload: Dict[str, Any]
    priority: Optional[int] = 0
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    execution_context_key: Optional[str] = Field(default=None, max_length=128)


class UserTaskCreateOut(BaseModel):
    id: int
    status: str
    created_at: datetime


class UserTaskOut(BaseModel):
    id: int
    type: str
    status: str
    priority: int
    created_at: datetime
    completed_at: Optional[datetime]
    execution_context_id: Optional[int]
    idempotency_key: Optional[str]

    model_config = ConfigDict(from_attributes=True)


@router.post("/hello", response_model=DeviceHelloOut)
async def hello(data: DeviceHelloIn, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Device).where(Device.device_uid == data.device_uid))
    device = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if device is None:
        device = Device(
            device_uid=data.device_uid,
            firmware_version=data.firmware_version,
            capabilities=data.capabilities,
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.firmware_version = data.firmware_version
        device.capabilities = data.capabilities
        device.last_seen_at = now
    device.is_claimed = device.owner_user_id is not None

    await db.commit()
    await db.refresh(device)

    claimed = device.owner_user_id is not None
    return DeviceHelloOut(device_id=device.id, claimed=claimed)


@router.get("/whoami")
async def whoami(device: Device = Depends(get_current_device)):
    return {
        "id": device.id,
        "device_uid": device.device_uid,
        "owner_user_id": device.owner_user_id,
    }


@router.get("", response_model=list[DeviceOut])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Device).where(Device.owner_user_id == user.id).order_by(Device.id)
    )
    return list(res.scalars().all())


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Device).where(Device.id == device_id, Device.owner_user_id == user.id)
    )
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    return device


async def _get_owned_device(
    device_id: int, db: AsyncSession, user: User
) -> Device:
    res = await db.execute(
        select(Device).where(Device.id == device_id, Device.owner_user_id == user.id)
    )
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")
    return device




@router.get("/{device_id}/telemetry/recent", response_model=list[UserTelemetryOut])
async def get_device_telemetry_recent(
    device_id: int,
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    limit = max(1, min(200, limit))
    res = await db.execute(
        select(DeviceTelemetry)
        .where(DeviceTelemetry.device_id == device_id)
        .order_by(desc(DeviceTelemetry.received_at))
        .limit(limit)
    )
    rows = res.scalars().all()
    return [
        UserTelemetryOut(
            id=row.id,
            created_at=row.received_at,
            event_type=row.event_type,
            payload=row.payload,
        )
        for row in rows
    ]


@router.get("/{device_id}/telemetry", response_model=list[UserTelemetryOut])
async def get_device_telemetry(
    device_id: int,
    before: Optional[datetime] = Query(default=None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    limit = max(1, min(200, limit))
    stmt = select(DeviceTelemetry).where(DeviceTelemetry.device_id == device_id)
    if before is not None:
        stmt = stmt.where(DeviceTelemetry.received_at < before)
    res = await db.execute(stmt.order_by(desc(DeviceTelemetry.received_at)).limit(limit))
    rows = res.scalars().all()
    return [
        UserTelemetryOut(
            id=row.id,
            created_at=row.received_at,
            event_type=row.event_type,
            payload=row.payload,
        )
        for row in rows
    ]


@router.post("/{device_id}/tasks", response_model=UserTaskCreateOut)
async def create_task_for_device(
    device_id: int,
    data: UserTaskCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    validate_json_object(data.payload, "payload")
    context_id = None
    if data.execution_context_key:
        res = await db.execute(
            select(ExecutionContext.id).where(
                ExecutionContext.client_id == device_id,
                ExecutionContext.context_key == data.execution_context_key,
            )
        )
        context_id = res.scalar_one_or_none()
        if context_id is None:
            raise HTTPException(status_code=409, detail="execution context not found")
    if data.idempotency_key:
        res = await db.execute(
            select(Task).where(
                Task.client_id == device_id,
                Task.idempotency_key == data.idempotency_key,
            )
        )
        existing = res.scalar_one_or_none()
        if existing is not None:
            return UserTaskCreateOut(
                id=existing.id,
                status=existing.status,
                created_at=existing.created_at,
            )
    task = Task(
        client_id=device_id,
        execution_context_id=context_id,
        type=data.type,
        payload=data.payload,
        status="queued",
        priority=data.priority or 0,
        idempotency_key=data.idempotency_key,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return UserTaskCreateOut(id=task.id, status=task.status, created_at=task.created_at)


@router.get("/{device_id}/tasks", response_model=list[UserTaskOut])
async def list_device_tasks(
    device_id: int,
    status: Optional[str] = Query(default=None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    limit = max(1, min(200, limit))
    stmt = select(Task).where(Task.client_id == device_id)
    if status:
        stmt = stmt.where(Task.status == status)
    res = await db.execute(stmt.order_by(desc(Task.created_at)).limit(limit))
    return list(res.scalars().all())
