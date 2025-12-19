from datetime import datetime
from typing import Any, Dict, Optional, List
import asyncio
import json
import time
from collections import deque

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.db.models.device import Device
from app.db.models.telemetry import DeviceTelemetry

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

MAX_PAYLOAD_BYTES = 16 * 1024
MAX_PAYLOAD_KEY_LENGTH = 64
RATE_LIMIT_PER_MINUTE = 60
_rate_lock = asyncio.Lock()
_rate_window = 60.0
_rate_hits: dict[int, deque[float]] = {}


def _validate_payload(payload: Dict[str, Any]) -> None:
    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if not isinstance(key, str):
                    raise HTTPException(status_code=422, detail="payload keys must be strings")
                if len(key) > MAX_PAYLOAD_KEY_LENGTH:
                    raise HTTPException(status_code=422, detail="payload key too long")
                _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(payload)
    payload_bytes = len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    if payload_bytes > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")


async def _check_rate_limit(device_id: int) -> None:
    now = time.monotonic()
    async with _rate_lock:
        hits = _rate_hits.get(device_id)
        if hits is None:
            hits = deque()
            _rate_hits[device_id] = hits
        while hits and now - hits[0] > _rate_window:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        hits.append(now)


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
    await _check_rate_limit(device.id)
    _validate_payload(data.payload)
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
