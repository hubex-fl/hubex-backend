from datetime import datetime
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.db.models.device import Device
from app.db.models.telemetry import DeviceTelemetry

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryIn(BaseModel):
    event_type: Optional[str] = Field(default=None, max_length=64)
    payload: Dict[str, Any]
    device_timestamp: Optional[datetime] = None


class TelemetryOut(BaseModel):
    telemetry_id: int
    received_at: datetime


class TelemetryRecentOut(BaseModel):
    id: int
    received_at: datetime
    event_type: Optional[str]
    payload: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=TelemetryOut)
async def ingest_telemetry(
    data: TelemetryIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    telemetry = DeviceTelemetry(
        device_id=device.id,
        event_type=data.event_type,
        payload=data.payload,
    )
    db.add(telemetry)
    await db.commit()
    await db.refresh(telemetry)
    return TelemetryOut(telemetry_id=telemetry.id, received_at=telemetry.received_at)


@router.get("/recent", response_model=List[TelemetryRecentOut])
async def recent_telemetry(
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    limit = max(1, min(200, limit))
    res = await db.execute(
        select(DeviceTelemetry)
        .where(DeviceTelemetry.device_id == device.id)
        .order_by(desc(DeviceTelemetry.received_at))
        .limit(limit)
    )
    return list(res.scalars().all())
