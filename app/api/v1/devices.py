from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device, get_current_user
from app.db.models.device import Device  # NUR das echte Model importieren
from app.db.models.user import User

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
