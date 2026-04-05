from datetime import datetime, timezone, timedelta
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, desc, update, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device, get_current_user
from app.api.deps_org import get_current_org_id
from app.core.security import hash_device_token
from app.core.system_events import emit_system_event
from app.db.models.device import Device
from app.db.models.user import User
from app.api.v1.validators import validate_json_object
from app.api.v1.error_utils import raise_api_error
from app.core.device_type import detect_device_type, VALID_DEVICE_TYPES
from app.db.models.telemetry import DeviceTelemetry
from app.db.models.tasks import ExecutionContext, Task
from app.db.models.pairing import PairingSession
from app.db.models.pairing import DeviceToken
from app.db.models.audit import AuditV1Entry
from app.db.models.device_runtime import DeviceRuntimeSetting
from app.db.models.entities import EntityDeviceBinding
from app.db.models.variables import (
    VariableAppliedAck,
    VariableAudit,
    VariableEffect,
    VariableSnapshot,
    VariableSnapshotItem,
    VariableValue,
)
from app.schemas.device import DeviceListItem, DeviceDetailItem
from app.api.v1.device_state import (
    derive_state,
    fetch_busy_device_ids,
    fetch_pairing_active_uids,
)
from app.schemas.taskcam import CurrentTaskOut, TaskHistoryItemOut

router = APIRouter(prefix="/devices", tags=["devices"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DeviceHelloIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=128)
    firmware_version: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None


class DeviceHelloOut(BaseModel):
    device_id: int
    claimed: bool


class DeviceLookupOut(BaseModel):
    device_uid: str
    device_id: int
    claimed: bool
    state: str
    last_seen_at: Optional[datetime]


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


class DeviceTokenReissueIn(BaseModel):
    reason: str = Field(min_length=3, max_length=256)


class DeviceTokenReissueOut(BaseModel):
    device_id: int
    device_uid: str
    device_token: str
    revoked_count: int


class DeviceUnclaimOut(BaseModel):
    device_id: int
    device_uid: str
    revoked_count: int
    unclaimed: bool


class DevicePurgeIn(BaseModel):
    reason: str | None = Field(default=None, max_length=256)


class DevicePurgeOut(BaseModel):
    device_id: int
    device_uid: str
    deleted_counts: Dict[str, int]


class DevicePurgeBulkIn(BaseModel):
    device_ids: list[int] = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=256)


class DevicePurgeBulkResult(BaseModel):
    id: int
    ok: bool
    deleted_counts: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class DevicePurgeBulkOut(BaseModel):
    results: list[DevicePurgeBulkResult]


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


class UserTaskCancelOut(BaseModel):
    id: int
    status: str
    completed_at: datetime


@router.post("/hello", response_model=DeviceHelloOut)
async def hello(
    data: DeviceHelloIn,
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    res = await db.execute(select(Device).where(Device.device_uid == data.device_uid))
    device = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if device is None:
        # Enforce device plan limit when org context is available
        if org_id is not None:
            from app.db.models.orgs import Organization
            from app.api.v1.orgs import check_device_limit
            org = await db.get(Organization, org_id)
            if org is not None:
                await check_device_limit(db, org)
        device = Device(
            device_uid=data.device_uid,
            firmware_version=data.firmware_version,
            capabilities=data.capabilities,
            last_seen_at=now,
            org_id=org_id,
            device_type=detect_device_type(data.firmware_version),
        )
        db.add(device)
    else:
        device.firmware_version = data.firmware_version
        device.capabilities = data.capabilities
        device.last_seen_at = now
        if not device.device_type or device.device_type == "unknown":
            device.device_type = detect_device_type(data.firmware_version)
    device.is_claimed = device.owner_user_id is not None

    await db.commit()
    await db.refresh(device)

    claimed = device.owner_user_id is not None
    return DeviceHelloOut(device_id=device.id, claimed=claimed)


@router.get("/whoami")
async def whoami(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "id": device.id,
        "device_uid": device.device_uid,
        "owner_user_id": device.owner_user_id,
    }


@router.get("/lookup/{device_uid}", response_model=DeviceLookupOut)
async def lookup_device(
    device_uid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Device).where(Device.device_uid == device_uid))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
    now = datetime.now(timezone.utc)
    active_pairing_uids = await fetch_pairing_active_uids(
        db, [device.device_uid], now
    )
    busy_ids = await fetch_busy_device_ids(db, [device.id], now)
    pairing_active = device.device_uid in active_pairing_uids
    busy = device.id in busy_ids
    state, claimed = derive_state(device, pairing_active, busy)
    return DeviceLookupOut(
        device_uid=device.device_uid,
        device_id=device.id,
        claimed=claimed,
        state=state,
        last_seen_at=device.last_seen_at,
    )


@router.get("", response_model=list[DeviceListItem])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    include_unclaimed: bool = Query(False),
):
    now = datetime.now(timezone.utc)
    online_window = timedelta(seconds=300)  # must match health "ok" threshold
    if include_unclaimed:
        if not _is_admin(user):
            raise_api_error(403, "DEVICE_LIST_FORBIDDEN", "include_unclaimed requires admin")
        res = await db.execute(
            select(Device)
            .where(or_(Device.owner_user_id == user.id, Device.owner_user_id.is_(None)))
            .order_by(Device.id)
        )
    else:
        res = await db.execute(
            select(Device).where(Device.owner_user_id == user.id).order_by(Device.id)
        )
    devices = res.scalars().all()
    device_uids = [device.device_uid for device in devices]
    device_ids = [device.id for device in devices]
    active_pairing_uids = await fetch_pairing_active_uids(db, device_uids, now)
    busy_ids = await fetch_busy_device_ids(db, device_ids, now)
    out: list[DeviceListItem] = []
    for device in devices:
        last_seen = device.last_seen_at
        age_seconds: Optional[int] = None
        health = "dead"
        if last_seen:
            last_seen = _ensure_utc(last_seen)
            age_seconds = max(0, int((now - last_seen).total_seconds()))
            if age_seconds <= 300:
                health = "ok"
            elif age_seconds <= 900:
                health = "stale"
        online = bool(last_seen and (now - last_seen) <= online_window)
        pairing_active = device.device_uid in active_pairing_uids
        busy = device.id in busy_ids
        state, claimed = derive_state(device, pairing_active, busy)
        out.append(
            DeviceListItem(
                id=device.id,
                device_uid=device.device_uid,
                device_type=device.device_type or "unknown",
                claimed=claimed,
                last_seen=last_seen,
                online=online,
                health=health,
                last_seen_age_seconds=age_seconds,
                state=state,
                pairing_active=pairing_active,
                busy=busy,
                name=device.name,
                category=device.category or "hardware",
                icon=device.icon,
                location_name=device.location_name,
                auto_discovery=device.auto_discovery if device.auto_discovery is not None else True,
            )
        )
    return out


@router.get("/{device_id}", response_model=DeviceDetailItem)
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
    now = datetime.now(timezone.utc)
    last_seen = device.last_seen_at
    age_seconds: Optional[int] = None
    health = "dead"
    if last_seen:
        last_seen = _ensure_utc(last_seen)
        age_seconds = max(0, int((now - last_seen).total_seconds()))
        if age_seconds <= 300:
            health = "ok"
        elif age_seconds <= 900:
            health = "stale"
    active_pairing_uids = await fetch_pairing_active_uids(
        db, [device.device_uid], now
    )
    busy_ids = await fetch_busy_device_ids(db, [device.id], now)
    pairing_active = device.device_uid in active_pairing_uids
    busy = device.id in busy_ids
    state, claimed = derive_state(device, pairing_active, busy)
    return DeviceDetailItem(
        id=device.id,
        device_uid=device.device_uid,
        device_type=device.device_type or "unknown",
        name=device.name,
        firmware_version=device.firmware_version,
        capabilities=device.capabilities,
        last_seen_at=device.last_seen_at,
        owner_user_id=device.owner_user_id,
        is_claimed=device.is_claimed,
        created_at=device.created_at,
        health=health,
        last_seen_age_seconds=age_seconds,
        state=state,
        pairing_active=pairing_active,
        busy=busy,
        config=device.config,
    )


def _gen_device_token_plain() -> str:
    return secrets.token_urlsafe(32)


def _hash_token(token_plain: str) -> str:
    return hash_device_token(token_plain)


def _is_admin(user: User) -> bool:
    if not user.caps:
        return False
    return "cap.admin" in user.caps or "mic.admin" in user.caps


def _can_purge(user: User) -> bool:
    if not user.caps:
        return False
    return "devices.purge" in user.caps


def _ensure_purge_cap(user: User) -> None:
    if not _can_purge(user):
        raise_api_error(403, "DEVICE_PURGE_FORBIDDEN", "Missing capability: devices.purge")


@router.post("/{device_id}/token/reissue", response_model=DeviceTokenReissueOut)
async def reissue_device_token(
    device_id: int,
    data: DeviceTokenReissueIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reason = data.reason.strip()
    if not (3 <= len(reason) <= 256):
        raise_api_error(400, "INVALID_REASON", "reason is required")

    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")
    if device.owner_user_id is None:
        raise_api_error(409, "DEVICE_NOT_CLAIMED", "device not claimed")
    if device.owner_user_id != user.id and not _is_admin(user):
        raise_api_error(403, "DEVICE_NOT_OWNER", "not device owner")

    token_plain = _gen_device_token_plain()
    token_hash = _hash_token(token_plain)

    revoked = await db.execute(
        update(DeviceToken)
        .where(DeviceToken.device_id == device.id, DeviceToken.is_active.is_(True))
        .values(is_active=False)
    )
    revoked_count = int(revoked.rowcount or 0)

    db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))
    db.add(
        AuditV1Entry(
            actor_type="user",
            actor_id=str(user.id),
            action="device.token.reissue",
            resource=device.device_uid,
            audit_metadata={
                "device_uid": device.device_uid,
                "reason": reason,
                "revoked_count": revoked_count,
            },
            trace_id=None,
        )
    )
    await db.commit()

    return DeviceTokenReissueOut(
        device_id=device.id,
        device_uid=device.device_uid,
        device_token=token_plain,
        revoked_count=revoked_count,
    )


@router.post("/{device_id}/unclaim", response_model=DeviceUnclaimOut)
async def unclaim_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")
    if device.owner_user_id is None:
        raise_api_error(409, "DEVICE_NOT_CLAIMED", "device not claimed")
    if device.owner_user_id != user.id and not _is_admin(user):
        raise_api_error(403, "DEVICE_NOT_OWNER", "not device owner")

    revoked = await db.execute(
        update(DeviceToken)
        .where(DeviceToken.device_id == device.id, DeviceToken.is_active.is_(True))
        .values(is_active=False)
    )
    revoked_count = int(revoked.rowcount or 0)

    device.owner_user_id = None
    device.is_claimed = False

    db.add(
        AuditV1Entry(
            actor_type="user",
            actor_id=str(user.id),
            action="device.unclaim",
            resource=device.device_uid,
            audit_metadata={
                "device_id": device.id,
                "device_uid": device.device_uid,
                "revoked_count": revoked_count,
            },
            trace_id=None,
        )
    )
    await emit_system_event(db, "device.unclaimed", {
        "device_id": device.id,
        "device_uid": device.device_uid,
    })
    await db.commit()

    return DeviceUnclaimOut(
        device_id=device.id,
        device_uid=device.device_uid,
        revoked_count=revoked_count,
        unclaimed=True,
    )


async def _purge_device_rows(db: AsyncSession, device: Device) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    def _count(res) -> int:
        return int(res.rowcount or 0)

    res = await db.execute(
        delete(VariableSnapshotItem).where(VariableSnapshotItem.device_id == device.id)
    )
    counts["variable_snapshot_items"] = _count(res)
    res = await db.execute(
        delete(VariableAppliedAck).where(VariableAppliedAck.device_id == device.id)
    )
    counts["variable_applied_acks"] = _count(res)
    res = await db.execute(
        delete(VariableAudit).where(
            or_(VariableAudit.device_id == device.id, VariableAudit.actor_device_id == device.id)
        )
    )
    counts["variable_audits"] = _count(res)
    res = await db.execute(
        delete(VariableValue).where(
            or_(VariableValue.device_id == device.id, VariableValue.updated_by_device_id == device.id)
        )
    )
    counts["variable_values"] = _count(res)
    res = await db.execute(
        delete(VariableSnapshot).where(VariableSnapshot.device_id == device.id)
    )
    counts["variable_snapshots"] = _count(res)
    res = await db.execute(
        delete(VariableEffect).where(
            or_(VariableEffect.device_id == device.id, VariableEffect.device_uid == device.device_uid)
        )
    )
    counts["variable_effects"] = _count(res)
    res = await db.execute(
        delete(DeviceTelemetry).where(DeviceTelemetry.device_id == device.id)
    )
    counts["device_telemetry"] = _count(res)
    res = await db.execute(delete(Task).where(Task.client_id == device.id))
    counts["tasks"] = _count(res)
    res = await db.execute(
        delete(ExecutionContext).where(ExecutionContext.client_id == device.id)
    )
    counts["execution_contexts"] = _count(res)
    res = await db.execute(
        delete(EntityDeviceBinding).where(EntityDeviceBinding.device_id == device.id)
    )
    counts["entity_device_bindings"] = _count(res)
    res = await db.execute(
        delete(DeviceRuntimeSetting).where(DeviceRuntimeSetting.device_id == device.id)
    )
    counts["device_runtime_settings"] = _count(res)
    res = await db.execute(
        delete(PairingSession).where(PairingSession.device_uid == device.device_uid)
    )
    counts["pairing_sessions"] = _count(res)
    res = await db.execute(delete(DeviceToken).where(DeviceToken.device_id == device.id))
    counts["device_tokens"] = _count(res)
    res = await db.execute(delete(Device).where(Device.id == device.id))
    counts["devices"] = _count(res)
    return counts


@router.post("/{device_id}/purge", response_model=DevicePurgeOut)
async def purge_device(
    device_id: int,
    data: DevicePurgeIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_purge_cap(user)

    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")

    deleted_counts = await _purge_device_rows(db, device)
    db.add(
        AuditV1Entry(
            actor_type="user",
            actor_id=str(user.id),
            action="device.purge",
            resource=str(device.id),
            audit_metadata={
                "device_id": device.id,
                "device_uid": device.device_uid,
                "deleted_counts": deleted_counts,
                "reason": data.reason,
                "bulk": False,
                "requested_device_ids_count": 1,
                "deleted_device": deleted_counts.get("devices", 0) > 0,
            },
            trace_id=None,
        )
    )
    await db.commit()
    return DevicePurgeOut(
        device_id=device_id,
        device_uid=device.device_uid,
        deleted_counts=deleted_counts,
    )


@router.post("/purge", response_model=DevicePurgeBulkOut)
@router.post("/purge-bulk", response_model=DevicePurgeBulkOut)
async def purge_devices_bulk(
    data: DevicePurgeBulkIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_purge_cap(user)

    results: list[DevicePurgeBulkResult] = []
    requested_count = len(data.device_ids)
    for device_id in data.device_ids:
        try:
            async with db.begin_nested():
                res = await db.execute(select(Device).where(Device.id == device_id))
                device = res.scalar_one_or_none()
                if device is None:
                    results.append(
                        DevicePurgeBulkResult(id=device_id, ok=False, error="not_found")
                    )
                    continue
                deleted_counts = await _purge_device_rows(db, device)
                db.add(
                    AuditV1Entry(
                        actor_type="user",
                        actor_id=str(user.id),
                        action="device.purge",
                        resource=str(device.id),
                        audit_metadata={
                            "device_id": device.id,
                            "device_uid": device.device_uid,
                            "deleted_counts": deleted_counts,
                            "reason": data.reason,
                            "bulk": True,
                            "requested_device_ids_count": requested_count,
                            "deleted_device": deleted_counts.get("devices", 0) > 0,
                        },
                        trace_id=None,
                    )
                )
            results.append(
                DevicePurgeBulkResult(
                    id=device_id, ok=True, deleted_counts=deleted_counts
                )
            )
        except Exception as exc:
            results.append(
                DevicePurgeBulkResult(id=device_id, ok=False, error=str(exc))
            )
    await db.commit()
    return DevicePurgeBulkOut(results=results)


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


class DeviceTypeUpdateIn(BaseModel):
    device_type: str = Field(min_length=1, max_length=32)


class DeviceTypeUpdateOut(BaseModel):
    device_id: int
    device_type: str


@router.patch("/{device_id}/type", response_model=DeviceTypeUpdateOut)
async def update_device_type(
    device_id: int,
    data: DeviceTypeUpdateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_owned_device(device_id, db, user)
    dt = data.device_type.strip().lower()
    if dt not in VALID_DEVICE_TYPES:
        raise_api_error(
            400,
            "INVALID_DEVICE_TYPE",
            f"Invalid device type. Valid: {', '.join(sorted(VALID_DEVICE_TYPES))}",
        )
    device.device_type = dt
    await db.commit()
    return DeviceTypeUpdateOut(device_id=device.id, device_type=dt)


# M15: Update device identity fields
from app.schemas.device import DevicePatch

@router.patch("/{device_id}")
async def update_device_identity(
    device_id: int,
    payload: DevicePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await _get_owned_device(device_id, db, user)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    for k, v in updates.items():
        setattr(device, k, v)
    await db.commit()
    return {"device_id": device.id, "updated_fields": list(updates.keys())}


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
    limit = max(1, min(100, limit))
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
    await db.flush()
    await emit_system_event(db, "task.queued", {
        "task_id": task.id,
        "task_type": data.type,
        "device_id": device_id,
    })
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


@router.get("/{device_id}/current-task", response_model=CurrentTaskOut)
async def get_current_task(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(Task, ExecutionContext.context_key)
        .outerjoin(ExecutionContext, ExecutionContext.id == Task.execution_context_id)
        .where(
            Task.client_id == device_id,
            Task.lease_expires_at.is_not(None),
            Task.lease_expires_at > now,
            Task.lease_token.is_not(None),
            Task.status == "in_flight",
        )
        # If multiple leases exist (should not), pick the latest expiry.
        .order_by(desc(Task.lease_expires_at))
        .limit(1)
    )
    row = res.one_or_none()
    if row is None:
        return CurrentTaskOut(
            has_active_lease=False,
            device_id=device_id,
            task_id=None,
            task_name=None,
            task_type=None,
            task_status=None,
            claimed_at=None,
            lease_expires_at=None,
            lease_seconds_remaining=None,
            lease_token_hint=None,
            context_key=None,
        )

    task, context_key = row
    lease_seconds_remaining = max(
        0, int((task.lease_expires_at - now).total_seconds())
    )
    lease_token_hint = task.lease_token[:6] if task.lease_token else None
    # No separate name field exists; task.type is the canonical identifier.
    task_name = task.type
    task_type = task.type

    return CurrentTaskOut(
        has_active_lease=True,
        device_id=device_id,
        task_id=task.id,
        task_name=task_name,
        task_type=task_type,
        task_status=task.status,
        claimed_at=task.claimed_at,
        lease_expires_at=task.lease_expires_at,
        lease_seconds_remaining=lease_seconds_remaining,
        lease_token_hint=lease_token_hint,
        context_key=context_key,
    )


@router.get("/{device_id}/task-history", response_model=list[TaskHistoryItemOut])
async def get_task_history(
    device_id: int,
    limit: int = Query(5),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    limit = max(1, min(20, limit))
    res = await db.execute(
        select(Task)
        .where(Task.client_id == device_id)
        .order_by(desc(Task.completed_at), desc(Task.claimed_at), desc(Task.id))
        .limit(limit)
    )
    rows = res.scalars().all()
    out: list[TaskHistoryItemOut] = []
    for task in rows:
        out.append(
            TaskHistoryItemOut(
                task_id=task.id,
                task_name=task.type,
                task_type=task.type,
                task_status=task.status,
                claimed_at=task.claimed_at,
                finished_at=task.completed_at,
                last_seen_at=None,
            )
        )
    return out


@router.post("/{device_id}/tasks/{task_id}/cancel", response_model=UserTaskCancelOut)
async def cancel_task_for_device(
    device_id: int,
    task_id: int,
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_device(device_id, db, user)
    res = await db.execute(
        select(Task).where(Task.id == task_id, Task.client_id == device_id)
    )
    task = res.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status in {"done", "failed", "canceled"}:
        raise HTTPException(status_code=409, detail="task already completed")
    if task.status == "in_flight" and not force:
        raise HTTPException(status_code=409, detail="task in flight")

    was_in_flight = task.status == "in_flight"
    now = datetime.now(timezone.utc)
    task.status = "canceled"
    task.completed_at = now
    task.error = "canceled by owner (force)" if was_in_flight and force else "canceled by owner"
    await db.commit()
    return UserTaskCancelOut(id=task.id, status=task.status, completed_at=task.completed_at)
