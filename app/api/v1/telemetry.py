from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
import asyncio
import json
import time
import logging
from collections import deque

from fastapi import APIRouter, Depends, Query, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.core.security import decode_access_token
from app.core.system_events import emit_system_event
from app.realtime import hub
from app.db.models.device import Device
from app.db.models.telemetry import DeviceTelemetry
from app.db.models.user import User
from app.db.models.variables import VariableDefinition
from app.db.session import AsyncSessionLocal
from app.core.variables import record_history
from sqlalchemy import select as sa_select

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
ws_router = APIRouter(prefix="/telemetry", tags=["telemetry"])
logger = logging.getLogger("uvicorn.error")

MAX_PAYLOAD_BYTES = 16 * 1024
MAX_PAYLOAD_KEY_LENGTH = 64
RATE_LIMIT_PER_MINUTE = 60
MAX_WS_CONNECTIONS = 200
_rate_lock = asyncio.Lock()
_rate_window = 60.0
_rate_hits: dict[int, deque[float]] = {}


def _serialize_telemetry(row: DeviceTelemetry) -> dict:
    return {
        "id": row.id,
        "received_at": row.received_at.isoformat(),
        "event_type": row.event_type,
        "payload": row.payload,
    }


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
async def _bridge_telemetry_to_variables(
    device_id: int,
    device_uid: str,
    event_type: Optional[str],
    payload: Dict[str, Any],
) -> None:
    """Background task: match telemetry payload keys against device_writable variable definitions."""
    try:
        async with AsyncSessionLocal() as db:
            # Build lookup keys: "event_type.key" and "key"
            candidate_keys: list[str] = []
            for pk in payload.keys():
                if event_type:
                    candidate_keys.append(f"{event_type}.{pk}")
                candidate_keys.append(pk)

            if not candidate_keys:
                return

            # Load matching device_writable definitions
            res = await db.execute(
                sa_select(VariableDefinition).where(
                    VariableDefinition.key.in_(candidate_keys),
                    VariableDefinition.device_writable == True,  # noqa: E712
                )
            )
            defs = res.scalars().all()
            if not defs:
                return

            from app.db.models.variables import VariableValue
            for defn in defs:
                # Determine raw payload value
                if event_type and defn.key == f"{event_type}.{defn.key.split('.')[-1]}":
                    raw_key = defn.key.split(".", 1)[-1]
                    raw_value = payload.get(raw_key)
                else:
                    raw_value = payload.get(defn.key)

                if raw_value is None:
                    continue

                # Coerce to definition type
                try:
                    if defn.value_type == "int":
                        coerced = int(raw_value)
                    elif defn.value_type == "float":
                        coerced = float(raw_value)
                    elif defn.value_type == "bool":
                        coerced = bool(raw_value)
                    elif defn.value_type == "json":
                        coerced = raw_value if isinstance(raw_value, (dict, list)) else raw_value
                    else:
                        coerced = str(raw_value)
                except (TypeError, ValueError):
                    continue

                # Upsert VariableValue
                scope = defn.scope
                duid = device_uid if scope == "device" else None
                did = device_id if scope == "device" else None

                existing_res = await db.execute(
                    sa_select(VariableValue).where(
                        VariableValue.variable_key == defn.key,
                        VariableValue.scope == scope,
                        VariableValue.device_id == did,
                    )
                )
                existing = existing_res.scalar_one_or_none()
                if existing:
                    existing.value = coerced
                    existing.version = (existing.version or 0) + 1
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    db.add(VariableValue(
                        variable_key=defn.key,
                        scope=scope,
                        device_id=did,
                        value=coerced,
                        version=1,
                    ))

                await record_history(
                    db, definition=defn, value=coerced,
                    device_id=did, source="telemetry"
                )

            await db.commit()
    except Exception as exc:
        logger.warning("telemetry→variable bridge error: %s", exc)


@router.post("", response_model=TelemetryOut)
async def ingest_telemetry(
    data: TelemetryIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    await _check_rate_limit(device.id)
    _validate_payload(data.payload)
    device.last_seen_at = datetime.now(timezone.utc)
    # Allow device to self-report its reporting interval
    ri = data.payload.get("reporting_interval_seconds")
    if isinstance(ri, (int, float)) and 1 <= ri <= 86400:
        device.reporting_interval_seconds = int(ri)
    telemetry = DeviceTelemetry(
        device_id=device.id,
        event_type=data.event_type,
        payload=data.payload,
    )
    db.add(telemetry)
    await emit_system_event(db, "telemetry.received", {
        "device_uid": device.device_uid,
        "device_id": device.id,
        "event_type": data.event_type,
    })
    await emit_system_event(db, "device.online", {
        "device_uid": device.device_uid,
        "device_id": device.id,
    })
    await db.commit()
    await db.refresh(telemetry)
    await hub.broadcast(device.id, _serialize_telemetry(telemetry))

    # Bridge telemetry → variables (fire-and-forget, non-blocking)
    asyncio.create_task(
        _bridge_telemetry_to_variables(
            device.id, device.device_uid, data.event_type, data.payload
        )
    )

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


@ws_router.websocket("/devices/{device_id}/telemetry/ws")
async def telemetry_ws(
    websocket: WebSocket,
    device_id: int,
    token: str = Query(...),
):
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        await websocket.close(code=1008)
        return

    rows: list[DeviceTelemetry] = []
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            await websocket.close(code=1008)
            return

        res = await session.execute(
            select(Device).where(Device.id == device_id, Device.owner_user_id == user.id)
        )
        device = res.scalar_one_or_none()
        if not device:
            await websocket.close(code=1008)
            return

        res = await session.execute(
            select(DeviceTelemetry)
            .where(DeviceTelemetry.device_id == device_id)
            .order_by(desc(DeviceTelemetry.received_at))
            .limit(5)
        )
        rows = list(res.scalars().all())

    active_ws = sum(len(s) for s in hub.clients.values())
    if active_ws >= MAX_WS_CONNECTIONS:
        await websocket.close(code=1013)
        return

    await websocket.accept()
    await hub.add(device_id, websocket)
    logger.info("telemetry_ws connect device_id=%s active=%s", device_id, active_ws + 1)
    try:
        rows.reverse()
        await websocket.send_json([_serialize_telemetry(row) for row in rows])
        while True:
            await asyncio.sleep(3600)
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(device_id, websocket)
