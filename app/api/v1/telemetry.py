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


def _flatten_payload(payload: dict, prefix: str = "", _depth: int = 0) -> dict[str, Any]:
    """Recursively flatten nested dicts using dot notation (max 3 levels deep).

    Lists are not flattened — they are kept as-is under their parent key.

    Examples:
        {"sensors": {"temp": 23.5}} → {"sensors.temp": 23.5}
        {"a": {"b": {"c": 1}}}      → {"a.b.c": 1}
        {"a": {"b": {"c": {"d": 1}}}} → {"a.b.c": {"d": 1}}  (depth limit)
    """
    result: dict[str, Any] = {}
    for key, value in payload.items():
        flat_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and _depth < 3:
            nested = _flatten_payload(value, prefix=flat_key, _depth=_depth + 1)
            result.update(nested)
        else:
            result[flat_key] = value
    return result


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


async def _bridge_telemetry_to_variables(
    device_id: int,
    device_uid: str,
    event_type: Optional[str],
    payload: Dict[str, Any],
) -> None:
    """Background task: match telemetry payload keys against device_writable variable definitions.

    Supports nested payloads via dot notation through _flatten_payload, e.g.
    {"sensors": {"temperature": 23.5}} matches variable key "sensors.temperature"
    or "myevent.sensors.temperature" (when event_type="myevent").
    """
    try:
        async with AsyncSessionLocal() as db:
            # Flatten nested dicts to dot-notation keys (max 3 levels)
            flat = _flatten_payload(payload)

            # Build candidate lookup keys from all flattened keys
            candidate_keys: list[str] = []
            for flat_key in flat.keys():
                if event_type:
                    candidate_keys.append(f"{event_type}.{flat_key}")
                candidate_keys.append(flat_key)

            if not candidate_keys:
                return

            # Load ALL matching definitions (regardless of device_writable)
            res = await db.execute(
                sa_select(VariableDefinition).where(
                    VariableDefinition.key.in_(candidate_keys),
                )
            )
            defs = list(res.scalars().all())

            # Auto-Discovery: create VariableDefinitions for unknown keys
            known_keys = {d.key for d in defs}
            for flat_key in flat.keys():
                if flat_key not in known_keys and flat_key not in ("mqtt_topic",):
                    val = flat[flat_key]
                    vtype = "float" if isinstance(val, (int, float)) and not isinstance(val, bool) else \
                            "bool" if isinstance(val, bool) else \
                            "json" if isinstance(val, (dict, list)) else "string"
                    new_def = VariableDefinition(
                        key=flat_key,
                        scope="device",
                        value_type=vtype,
                        description=f"Auto-discovered from telemetry",
                        device_writable=True,
                    )
                    db.add(new_def)
                    defs.append(new_def)
                    known_keys.add(flat_key)

            if not defs:
                return

            from app.db.models.variables import VariableValue
            for defn in defs:
                # Look up raw value from flattened dict
                raw_value = flat.get(defn.key)
                if raw_value is None and event_type:
                    # Try stripping event_type prefix (e.g. "myevent.sensors.temp" → "sensors.temp")
                    prefix = f"{event_type}."
                    if defn.key.startswith(prefix):
                        raw_value = flat.get(defn.key[len(prefix):])

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
                    existing.value_json = coerced
                    existing.version = (existing.version or 0) + 1
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    db.add(VariableValue(
                        variable_key=defn.key,
                        scope=scope,
                        device_id=did,
                        value_json=coerced,
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

    # Bridge telemetry → variables
    # If Redis queue enabled, enqueue for async processing; else fire-and-forget
    from app.core.config import settings as _settings
    if _settings.telemetry_queue_enabled:
        from app.core.telemetry_worker import enqueue_telemetry
        queued = await enqueue_telemetry(
            device.id, device.device_uid, data.event_type, data.payload
        )
        if not queued:
            # Fallback to direct processing if Redis unavailable
            asyncio.create_task(
                _bridge_telemetry_to_variables(
                    device.id, device.device_uid, data.event_type, data.payload
                )
            )
    else:
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
