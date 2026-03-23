"""Edge API — config sync and heartbeat for devices.

GET  /edge/config      — returns effective variables + pending tasks
POST /edge/heartbeat   — updates last_seen_at and optionally firmware_version
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.db.models.device import Device
from app.db.models.tasks import Task
from app.db.models.variables import VariableValue

router = APIRouter(prefix="/edge")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EdgeConfigOut(BaseModel):
    device_id: int
    variables: dict[str, Any]
    tasks: list[dict[str, Any]]


class HeartbeatIn(BaseModel):
    firmware_version: str | None = None
    metadata: dict[str, Any] | None = None


class HeartbeatOut(BaseModel):
    device_id: int
    last_seen_at: datetime


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/config", response_model=EdgeConfigOut)
async def edge_config(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    """Return effective variable values and pending tasks for this device."""
    # Variables: device-scoped values for this device
    res = await db.execute(
        select(VariableValue).where(VariableValue.device_id == device.id)
    )
    variables: dict[str, Any] = {
        vv.variable_key: vv.value_json for vv in res.scalars().all()
    }

    # Tasks: pending (not yet claimed/completed)
    res = await db.execute(
        select(Task).where(
            Task.client_id == device.id,
            Task.status == "pending",
        ).order_by(Task.priority.desc(), Task.created_at.asc())
    )
    tasks = [
        {
            "id": t.id,
            "type": t.type,
            "payload": t.payload,
            "priority": t.priority,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in res.scalars().all()
    ]

    return EdgeConfigOut(device_id=device.id, variables=variables, tasks=tasks)


@router.post("/heartbeat", response_model=HeartbeatOut)
async def edge_heartbeat(
    body: HeartbeatIn,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    """Update device last_seen_at and optional firmware_version."""
    now = datetime.now(timezone.utc)
    device.last_seen_at = now
    if body.firmware_version is not None:
        device.firmware_version = body.firmware_version
    await db.commit()
    return HeartbeatOut(device_id=device.id, last_seen_at=now)
