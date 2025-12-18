from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.db.models.device import Device  # NUR das echte Model importieren

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceHelloIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=128)
    firmware_version: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None


class DeviceHelloOut(BaseModel):
    device_id: int
    claimed: bool


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
