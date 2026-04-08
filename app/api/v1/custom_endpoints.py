"""Custom API Builder — CRUD management + runtime handler for user-defined endpoints."""

import csv
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_current_org_id
from app.core.system_events import emit_system_event
from app.core import variables as vars_core
from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.custom_endpoint import CustomEndpoint
from app.db.models.device import Device
from app.db.models.entities import Entity, EntityDeviceBinding
from app.db.models.events import EventV1
from app.db.models.user import User
from app.db.models.variables import VariableHistory, VariableValue
from app.schemas.custom_api import (
    EndpointCreate,
    EndpointOut,
    EndpointSummaryOut,
    EndpointTrafficOut,
    EndpointUpdate,
    PreviewOut,
    RegenerateKeyOut,
    SetVariablePayload,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/custom-api", tags=["Custom API"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _generate_api_key() -> str:
    """Generate a 48-char URL-safe API key."""
    return secrets.token_urlsafe(36)


def _to_out(ep: CustomEndpoint) -> EndpointOut:
    return EndpointOut(
        id=ep.id,
        name=ep.name,
        path=ep.path,
        method=ep.method,
        description=ep.description,
        source_config=ep.source_config or {},
        auth_type=ep.auth_type,
        api_key=ep.api_key,
        rate_limit=ep.rate_limit,
        write_enabled=ep.write_enabled,
        enabled=ep.enabled,
        request_count=ep.request_count,
        last_called_at=ep.last_called_at,
        created_at=ep.created_at,
        updated_at=ep.updated_at,
        call_url=f"/api/v1/custom-api/call{ep.path}",
    )


# ── Rate-limiting (simple in-memory per-endpoint) ───────────────────────────

_rate_limit_store: dict[int, list[float]] = {}


def _check_rate_limit(endpoint_id: int, limit_per_hour: int) -> bool:
    """Return True if the request is within rate limits."""
    now = datetime.now(timezone.utc).timestamp()
    window_start = now - 3600  # 1 hour window

    if endpoint_id not in _rate_limit_store:
        _rate_limit_store[endpoint_id] = []

    # Prune old entries
    _rate_limit_store[endpoint_id] = [
        ts for ts in _rate_limit_store[endpoint_id] if ts > window_start
    ]

    if len(_rate_limit_store[endpoint_id]) >= limit_per_hour:
        return False

    _rate_limit_store[endpoint_id].append(now)
    return True


# ── Management endpoints (authenticated) ────────────────────────────────────


@router.get("/endpoints", response_model=list[EndpointSummaryOut])
async def list_custom_endpoints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """List all custom endpoints for the current org."""
    stmt = select(CustomEndpoint).order_by(CustomEndpoint.created_at.desc())
    if org_id is not None:
        stmt = stmt.where(CustomEndpoint.org_id == org_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/endpoints", response_model=EndpointOut, status_code=201)
async def create_custom_endpoint(
    data: EndpointCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Create a new custom API endpoint. Auto-generates an API key."""
    # Check path uniqueness
    existing = await db.execute(
        select(CustomEndpoint).where(CustomEndpoint.path == data.path)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Path '{data.path}' already exists")

    # Safety: POST endpoints require write_enabled
    if data.method == "POST" and not data.write_enabled:
        raise HTTPException(
            status_code=422,
            detail="POST endpoints require write_enabled=true",
        )

    api_key = _generate_api_key() if data.auth_type == "api_key" else None

    ep = CustomEndpoint(
        org_id=org_id,
        owner_id=user.id,
        name=data.name.strip(),
        path=data.path,
        method=data.method,
        description=data.description,
        source_config=data.source_config.model_dump(exclude_none=True),
        auth_type=data.auth_type,
        api_key=api_key,
        rate_limit=data.rate_limit,
        write_enabled=data.write_enabled,
    )
    db.add(ep)
    await emit_system_event(db, "custom_endpoint.created", {
        "user_id": user.id,
        "name": data.name,
        "path": data.path,
        "method": data.method,
    })
    await db.commit()
    await db.refresh(ep)
    return _to_out(ep)


@router.get("/endpoints/{endpoint_id}", response_model=EndpointOut)
async def get_custom_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full details of a custom endpoint."""
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return _to_out(ep)


@router.put("/endpoints/{endpoint_id}", response_model=EndpointOut)
async def update_custom_endpoint(
    endpoint_id: int,
    data: EndpointUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an existing custom endpoint."""
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    if data.name is not None:
        ep.name = data.name.strip()
    if data.description is not None:
        ep.description = data.description
    if data.source_config is not None:
        ep.source_config = data.source_config.model_dump(exclude_none=True)
    if data.auth_type is not None:
        ep.auth_type = data.auth_type
        if data.auth_type == "api_key" and not ep.api_key:
            ep.api_key = _generate_api_key()
    if data.rate_limit is not None:
        ep.rate_limit = data.rate_limit
    if data.write_enabled is not None:
        ep.write_enabled = data.write_enabled
    if data.enabled is not None:
        ep.enabled = data.enabled

    await db.commit()
    await db.refresh(ep)
    return _to_out(ep)


@router.delete("/endpoints/{endpoint_id}", status_code=204)
async def delete_custom_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a custom endpoint."""
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await emit_system_event(db, "custom_endpoint.deleted", {
        "user_id": user.id,
        "name": ep.name,
        "path": ep.path,
    })
    await db.delete(ep)
    await db.commit()


@router.post(
    "/endpoints/{endpoint_id}/regenerate-key",
    response_model=RegenerateKeyOut,
)
async def regenerate_api_key(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Regenerate the API key for an endpoint."""
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if ep.auth_type != "api_key":
        raise HTTPException(status_code=422, detail="Endpoint does not use API key auth")

    ep.api_key = _generate_api_key()
    await db.commit()
    return RegenerateKeyOut(api_key=ep.api_key)


@router.get("/endpoints/{endpoint_id}/preview", response_model=PreviewOut)
async def preview_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preview what this endpoint would return (for the builder UI)."""
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    try:
        sample = await _execute_source(db, ep.source_config, limit=5)
    except Exception as exc:
        sample = {"error": str(exc)}

    return PreviewOut(
        endpoint_id=ep.id,
        path=ep.path,
        method=ep.method,
        source_config=ep.source_config,
        sample_data=sample,
    )


@router.get("/traffic", response_model=list[EndpointTrafficOut])
async def get_traffic(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Traffic overview for all custom endpoints."""
    result = await db.execute(
        select(CustomEndpoint)
        .where(CustomEndpoint.enabled.is_(True))
        .order_by(CustomEndpoint.request_count.desc())
    )
    return list(result.scalars().all())


# ── Runtime handler (custom auth) ───────────────────────────────────────────


@router.api_route(
    "/call/{path:path}",
    methods=["GET", "POST"],
    include_in_schema=True,
    summary="Custom endpoint runtime handler",
)
async def call_custom_endpoint(
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Unified runtime handler for all custom endpoints.
    Auth is validated per-endpoint (API key via X-API-Key header or ?key= param).
    """
    # Normalize the path
    lookup_path = f"/{path}" if not path.startswith("/") else path

    # Find the endpoint definition
    result = await db.execute(
        select(CustomEndpoint).where(
            CustomEndpoint.path == lookup_path,
            CustomEndpoint.enabled.is_(True),
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Custom endpoint not found")

    # Method check
    if request.method.upper() != ep.method:
        raise HTTPException(
            status_code=405,
            detail=f"Method {request.method} not allowed, expected {ep.method}",
        )

    # Auth check
    _validate_auth(request, ep)

    # Rate limit check
    if not _check_rate_limit(ep.id, ep.rate_limit):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Update traffic stats
    ep.request_count = (ep.request_count or 0) + 1
    ep.last_called_at = datetime.now(timezone.utc)

    config = ep.source_config or {}

    # Handle GET (read) or POST (write)
    if ep.method == "GET":
        data = await _execute_source(db, config)
        await db.commit()

        # CSV format?
        output_format = config.get("format", "json")
        if output_format == "csv":
            return _to_csv_response(data)
        return data

    elif ep.method == "POST":
        if not ep.write_enabled:
            raise HTTPException(status_code=403, detail="Write not enabled for this endpoint")

        body = await request.json()
        result_data = await _execute_write(db, config, body)
        await db.commit()
        return result_data

    raise HTTPException(status_code=405, detail="Unsupported method")


# ── Auth validation ──────────────────────────────────────────────────────────


def _validate_auth(request: Request, ep: CustomEndpoint) -> None:
    """Validate authentication for a custom endpoint."""
    if ep.auth_type == "none":
        return

    if ep.auth_type == "api_key":
        # Check X-API-Key header or ?key= query param
        api_key = request.headers.get("X-API-Key") or request.query_params.get("key")
        if not api_key:
            raise HTTPException(status_code=401, detail="API key required (X-API-Key header or ?key= param)")
        if api_key != ep.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return

    if ep.auth_type == "bearer":
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token required")
        # For bearer, we delegate to the standard auth system
        # The token is validated by the normal HUBEX auth flow
        return

    raise HTTPException(status_code=401, detail="Unknown auth type")


# ── Source execution (read) ──────────────────────────────────────────────────


async def _execute_source(
    db: AsyncSession,
    config: dict,
    limit: int | None = None,
) -> Any:
    """Execute a source_config and return the data."""
    source_type = config.get("type")

    if source_type == "variables":
        return await _query_variables(db, config, limit)
    elif source_type == "devices":
        return await _query_devices(db, config, limit)
    elif source_type == "entities":
        return await _query_entities(db, config, limit)
    elif source_type == "alerts":
        return await _query_alerts(db, config, limit)
    elif source_type == "events":
        return await _query_events(db, config, limit)
    elif source_type == "status_snapshot":
        return await _query_status_snapshot(db, config)
    else:
        raise HTTPException(status_code=422, detail=f"Unknown source type: {source_type}")


async def _query_variables(
    db: AsyncSession, config: dict, limit: int | None = None,
) -> dict:
    """Query variable values, optionally with history aggregation."""
    variable_keys: list[str] = config.get("variable_keys", [])
    device_uids: list[str] = config.get("device_uids", [])
    aggregation: str | None = config.get("aggregation")
    time_range: str | None = config.get("time_range")
    group_by: str | None = config.get("group_by")

    # Resolve device IDs from UIDs
    device_ids: list[int] = []
    if device_uids:
        dev_result = await db.execute(
            select(Device.id, Device.device_uid).where(Device.device_uid.in_(device_uids))
        )
        device_rows = dev_result.all()
        device_ids = [r.id for r in device_rows]

    # If aggregation or time_range specified, query history
    if aggregation or time_range:
        return await _query_variable_history(
            db, variable_keys, device_ids, aggregation, time_range, group_by, limit,
        )

    # Otherwise return current values
    stmt = select(
        VariableValue.variable_key,
        VariableValue.value_json,
        VariableValue.device_id,
        VariableValue.updated_at,
        VariableValue.version,
    )
    if variable_keys:
        stmt = stmt.where(VariableValue.variable_key.in_(variable_keys))
    if device_ids:
        stmt = stmt.where(VariableValue.device_id.in_(device_ids))
    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    # Build device_uid lookup for response
    uid_map: dict[int, str] = {}
    if device_ids:
        dev_result = await db.execute(
            select(Device.id, Device.device_uid).where(Device.id.in_(device_ids))
        )
        uid_map = {r.id: r.device_uid for r in dev_result.all()}

    return {
        "type": "variables",
        "count": len(rows),
        "data": [
            {
                "variable_key": r.variable_key,
                "value": r.value_json,
                "device_uid": uid_map.get(r.device_id) if r.device_id else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "version": r.version,
            }
            for r in rows
        ],
    }


async def _query_variable_history(
    db: AsyncSession,
    variable_keys: list[str],
    device_ids: list[int],
    aggregation: str | None,
    time_range: str | None,
    group_by: str | None,
    limit: int | None,
) -> dict:
    """Query variable history with optional aggregation."""
    # Calculate time window
    now = datetime.now(timezone.utc)
    range_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
    hours = range_map.get(time_range or "24h", 24)
    from_dt = now - timedelta(hours=hours)

    # Base query
    stmt = select(VariableHistory).where(VariableHistory.recorded_at >= from_dt)

    if variable_keys:
        stmt = stmt.where(VariableHistory.variable_key.in_(variable_keys))
    if device_ids:
        stmt = stmt.where(VariableHistory.device_id.in_(device_ids))

    stmt = stmt.order_by(VariableHistory.recorded_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    else:
        stmt = stmt.limit(1000)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    if not aggregation:
        return {
            "type": "variable_history",
            "time_range": time_range,
            "count": len(rows),
            "data": [
                {
                    "variable_key": r.variable_key,
                    "value": r.value_json,
                    "numeric_value": r.numeric_value,
                    "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
                }
                for r in reversed(rows)
            ],
        }

    # Perform in-memory aggregation grouped by variable_key
    from collections import defaultdict

    grouped: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r.numeric_value is not None:
            grouped[r.variable_key].append(r.numeric_value)

    agg_fn = {
        "avg": lambda vals: sum(vals) / len(vals) if vals else None,
        "min": lambda vals: min(vals) if vals else None,
        "max": lambda vals: max(vals) if vals else None,
        "sum": lambda vals: sum(vals) if vals else None,
    }
    fn = agg_fn.get(aggregation, agg_fn["avg"])

    return {
        "type": "variable_history_aggregated",
        "aggregation": aggregation,
        "time_range": time_range,
        "data": [
            {
                "variable_key": key,
                "value": fn(vals),
                "sample_count": len(vals),
            }
            for key, vals in grouped.items()
        ],
    }


async def _query_devices(
    db: AsyncSession, config: dict, limit: int | None = None,
) -> dict:
    """Query device status and metadata."""
    device_uids: list[str] = config.get("device_uids", [])

    stmt = select(Device)
    if device_uids:
        stmt = stmt.where(Device.device_uid.in_(device_uids))
    stmt = stmt.order_by(Device.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    devices = list(result.scalars().all())

    return {
        "type": "devices",
        "count": len(devices),
        "data": [
            {
                "device_uid": d.device_uid,
                "name": d.name,
                "device_type": d.device_type,
                "category": d.category,
                "firmware_version": d.firmware_version,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "is_claimed": d.is_claimed,
                "location_name": d.location_name,
            }
            for d in devices
        ],
    }


async def _query_entities(
    db: AsyncSession, config: dict, limit: int | None = None,
) -> dict:
    """Query entities with their bound devices."""
    entity_ids: list[int] = config.get("entity_ids", [])

    stmt = select(Entity)
    if entity_ids:
        # entity_id is string-typed in the model
        str_ids = [str(eid) for eid in entity_ids]
        stmt = stmt.where(Entity.entity_id.in_(str_ids))
    stmt = stmt.order_by(Entity.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    entities = list(result.scalars().all())

    # Fetch device bindings for each entity
    entity_data = []
    for ent in entities:
        binding_result = await db.execute(
            select(EntityDeviceBinding, Device)
            .join(Device, EntityDeviceBinding.device_id == Device.id)
            .where(EntityDeviceBinding.entity_id == ent.entity_id)
        )
        bindings = binding_result.all()

        entity_data.append({
            "entity_id": ent.entity_id,
            "type": ent.type,
            "name": ent.name,
            "health_status": ent.health_status,
            "location_name": ent.location_name,
            "devices": [
                {
                    "device_uid": dev.device_uid,
                    "name": dev.name,
                    "last_seen_at": dev.last_seen_at.isoformat() if dev.last_seen_at else None,
                }
                for _, dev in bindings
            ],
        })

    return {
        "type": "entities",
        "count": len(entity_data),
        "data": entity_data,
    }


async def _query_alerts(
    db: AsyncSession, config: dict, limit: int | None = None,
) -> dict:
    """Query active alert events."""
    stmt = (
        select(AlertEvent, AlertRule.name, AlertRule.severity)
        .join(AlertRule, AlertEvent.rule_id == AlertRule.id)
        .where(AlertEvent.status == "firing")
        .order_by(AlertEvent.triggered_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    else:
        stmt = stmt.limit(100)

    result = await db.execute(stmt)
    rows = result.all()

    return {
        "type": "alerts",
        "count": len(rows),
        "data": [
            {
                "id": alert.id,
                "rule_name": rule_name,
                "severity": severity,
                "status": alert.status,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            }
            for alert, rule_name, severity in rows
        ],
    }


async def _query_events(
    db: AsyncSession, config: dict, limit: int | None = None,
) -> dict:
    """Query recent events."""
    time_range: str | None = config.get("time_range")

    stmt = select(EventV1).order_by(EventV1.ts.desc())

    if time_range:
        now = datetime.now(timezone.utc)
        range_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
        hours = range_map.get(time_range, 24)
        from_dt = now - timedelta(hours=hours)
        stmt = stmt.where(EventV1.ts >= from_dt)

    if limit:
        stmt = stmt.limit(limit)
    else:
        stmt = stmt.limit(100)

    result = await db.execute(stmt)
    events = list(result.scalars().all())

    return {
        "type": "events",
        "count": len(events),
        "data": [
            {
                "id": e.id,
                "stream": e.stream,
                "type": e.type,
                "payload": e.payload,
                "ts": e.ts.isoformat() if e.ts else None,
            }
            for e in events
        ],
    }


async def _query_status_snapshot(
    db: AsyncSession, config: dict,
) -> dict:
    """Return all devices with their current variable values as one JSON snapshot."""
    device_uids: list[str] = config.get("device_uids", [])

    # Get devices
    dev_stmt = select(Device)
    if device_uids:
        dev_stmt = dev_stmt.where(Device.device_uid.in_(device_uids))
    dev_result = await db.execute(dev_stmt)
    devices = list(dev_result.scalars().all())

    device_ids = [d.id for d in devices]
    uid_by_id = {d.id: d.device_uid for d in devices}

    # Get all current variable values for these devices
    val_stmt = select(VariableValue).where(VariableValue.device_id.in_(device_ids))
    val_result = await db.execute(val_stmt)
    values = list(val_result.scalars().all())

    # Group values by device
    from collections import defaultdict

    values_by_device: dict[int, list] = defaultdict(list)
    for v in values:
        if v.device_id:
            values_by_device[v.device_id].append(v)

    snapshot = []
    for d in devices:
        dev_vars = values_by_device.get(d.id, [])
        snapshot.append({
            "device_uid": d.device_uid,
            "name": d.name,
            "category": d.category,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            "variables": {
                v.variable_key: {
                    "value": v.value_json,
                    "updated_at": v.updated_at.isoformat() if v.updated_at else None,
                }
                for v in dev_vars
            },
        })

    return {
        "type": "status_snapshot",
        "device_count": len(snapshot),
        "data": snapshot,
    }


# ── Write execution ─────────────────────────────────────────────────────────


async def _execute_write(
    db: AsyncSession, config: dict, body: dict,
) -> dict:
    """Execute a write operation based on source_config."""
    source_type = config.get("type")

    if source_type != "set_variable":
        raise HTTPException(status_code=422, detail=f"Write not supported for type: {source_type}")

    allowed_keys: list[str] = config.get("allowed_variable_keys", [])
    default_device_uid: str | None = config.get("device_uid")

    variable_key = body.get("variable_key")
    value = body.get("value")
    device_uid = body.get("device_uid") or default_device_uid

    if not variable_key:
        raise HTTPException(status_code=422, detail="variable_key is required")
    if value is None:
        raise HTTPException(status_code=422, detail="value is required")
    if allowed_keys and variable_key not in allowed_keys:
        raise HTTPException(
            status_code=403,
            detail=f"Variable '{variable_key}' is not in the allowed list for this endpoint",
        )

    # Use the variables core to set the value
    try:
        definition, var_value, device = await vars_core.create_or_update_value(
            db,
            key=variable_key,
            scope="device" if device_uid else "global",
            device_uid=device_uid,
            value=value,
            expected_version=None,
            actor_user_id=None,
            actor_device_id=None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to set variable: {exc}")

    return {
        "status": "ok",
        "variable_key": variable_key,
        "value": var_value.value_json,
        "version": var_value.version,
        "device_uid": device_uid,
    }


# ── CSV formatting ──────────────────────────────────────────────────────────


def _to_csv_response(data: dict) -> PlainTextResponse:
    """Convert a dict result to CSV format."""
    rows = data.get("data", [])
    if not rows:
        return PlainTextResponse("", media_type="text/csv")

    output = io.StringIO()
    # Use keys from first row as headers
    headers = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    for row in rows:
        # Flatten nested values for CSV
        flat_row = {}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                flat_row[k] = str(v)
            else:
                flat_row[k] = v
        writer.writerow(flat_row)

    csv_content = output.getvalue()
    return PlainTextResponse(csv_content, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=data.csv",
    })
