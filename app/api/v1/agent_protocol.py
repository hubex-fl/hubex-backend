"""Agent Protocol API (M23 Step 1).

Lightweight endpoints for agent devices to:
  - Register/handshake
  - Send heartbeat
  - Receive pending commands

These complement the telemetry endpoint for agent-specific operations.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.db.models.device import Device

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentHandshakeRequest(BaseModel):
    agent_version: str
    platform: str
    hostname: str
    capabilities: list[str] = []


class AgentHandshakeResponse(BaseModel):
    status: str
    device_id: int
    device_uid: str
    server_version: str = "0.1.0"
    heartbeat_interval: int = 30
    telemetry_interval: int = 60


class AgentHeartbeatRequest(BaseModel):
    uptime: float = 0
    status: str = "alive"


class AgentCommand(BaseModel):
    id: str
    type: str
    payload: dict = {}


class AgentHeartbeatResponse(BaseModel):
    ack: bool = True
    commands: list[AgentCommand] = []
    config: dict = {}


@router.post("/handshake", response_model=AgentHandshakeResponse)
async def agent_handshake(
    body: AgentHandshakeRequest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> AgentHandshakeResponse:
    """Agent registration handshake. Called once on startup."""
    # Update device metadata
    device.last_seen_at = datetime.now(timezone.utc)
    if not device.device_type or device.device_type == "unknown":
        device.device_type = "agent"
    await db.commit()

    return AgentHandshakeResponse(
        status="connected",
        device_id=device.id,
        device_uid=device.device_uid,
    )


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
async def agent_heartbeat(
    body: AgentHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> AgentHeartbeatResponse:
    """Agent heartbeat. Called periodically to keep device online."""
    device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()

    # Future: return pending commands from a queue
    return AgentHeartbeatResponse(
        ack=True,
        commands=[],
        config={},
    )
