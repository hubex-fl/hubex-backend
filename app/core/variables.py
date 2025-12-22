import json
import re
from datetime import datetime, timezone
from typing import Any
import time
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.error_utils import raise_api_error
from app.db.models.device import Device
from app.db.models.tasks import Task
from app.db.models.pairing import PairingSession
from app.db.models.variables import (
    VariableDefinition,
    VariableValue,
    VariableAudit,
    VariableSnapshot,
    VariableSnapshotItem,
    VariableAppliedAck,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


_effective_cache: dict[tuple[int, str, bool], tuple[float, dict[str, Any]]] = {}
_effective_cache_ttl = 2.0


def _cache_key(user_id: int, device_uid: str, include_secrets: bool) -> tuple[int, str, bool]:
    return (int(user_id), device_uid, include_secrets)


def _cache_get(user_id: int, device_uid: str, include_secrets: bool) -> dict[str, Any] | None:
    key = _cache_key(user_id, device_uid, include_secrets)
    entry = _effective_cache.get(key)
    if not entry:
        return None
    ts, payload = entry
    if time.monotonic() - ts > _effective_cache_ttl:
        _effective_cache.pop(key, None)
        return None
    return payload


def _cache_set(user_id: int, device_uid: str, include_secrets: bool, payload: dict[str, Any]) -> None:
    _effective_cache[_cache_key(user_id, device_uid, include_secrets)] = (time.monotonic(), payload)


def invalidate_effective_cache() -> None:
    _effective_cache.clear()


def validate_and_coerce(value: Any, value_type: str) -> Any:
    if value is None:
        return None
    if value_type == "string":
        return str(value)
    if value_type == "int":
        if isinstance(value, bool):
            raise_api_error(422, "VAR_INVALID_TYPE", "invalid int value")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                raise_api_error(422, "VAR_INVALID_TYPE", "invalid int value")
        raise_api_error(422, "VAR_INVALID_TYPE", "invalid int value")
    if value_type == "float":
        if isinstance(value, bool):
            raise_api_error(422, "VAR_INVALID_TYPE", "invalid float value")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise_api_error(422, "VAR_INVALID_TYPE", "invalid float value")
        raise_api_error(422, "VAR_INVALID_TYPE", "invalid float value")
    if value_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "1", "yes", "y"):
                return True
            if lowered in ("false", "0", "no", "n"):
                return False
        raise_api_error(422, "VAR_INVALID_TYPE", "invalid bool value")
    if value_type == "json":
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            raise_api_error(422, "VAR_INVALID_TYPE", "invalid json value")
        return value
    raise_api_error(422, "VAR_INVALID_TYPE", "unsupported value type")


def _constraints(definition: VariableDefinition) -> dict[str, Any] | None:
    constraints: dict[str, Any] = {}
    if definition.min_value is not None:
        constraints["min"] = definition.min_value
    if definition.max_value is not None:
        constraints["max"] = definition.max_value
    if definition.enum_values:
        constraints["enum"] = definition.enum_values
    if definition.regex:
        constraints["regex"] = definition.regex
    if definition.unit:
        constraints["unit"] = definition.unit
    return constraints or None


def validate_and_coerce_value(definition: VariableDefinition, value: Any) -> Any:
    coerced = validate_and_coerce(value, definition.value_type)
    constraints = _constraints(definition)
    if not constraints:
        return coerced

    if isinstance(coerced, (int, float)):
        min_value = constraints.get("min")
        max_value = constraints.get("max")
        if min_value is not None and coerced < min_value:
            raise_api_error(
                422,
                "VAR_CONSTRAINT_VIOLATION",
                "value below minimum",
                meta={"min": min_value},
            )
        if max_value is not None and coerced > max_value:
            raise_api_error(
                422,
                "VAR_CONSTRAINT_VIOLATION",
                "value above maximum",
                meta={"max": max_value},
            )

    if isinstance(coerced, str):
        enum_values = constraints.get("enum")
        if enum_values and coerced not in enum_values:
            raise_api_error(
                422,
                "VAR_CONSTRAINT_VIOLATION",
                "value not in enum",
                meta={"enum": enum_values},
            )
        regex = constraints.get("regex")
        if regex and not re.fullmatch(regex, coerced):
            raise_api_error(
                422,
                "VAR_CONSTRAINT_VIOLATION",
                "value does not match regex",
                meta={"regex": regex},
            )

    return coerced


def get_effective_value(definition: VariableDefinition, stored_value: Any | None) -> Any:
    return stored_value if stored_value is not None else definition.default_value


def mask_if_secret(definition: VariableDefinition, value: Any | None) -> Any | None:
    if definition.is_secret and value is not None:
        return "***"
    return value


async def get_definition(db: AsyncSession, key: str) -> VariableDefinition | None:
    res = await db.execute(select(VariableDefinition).where(VariableDefinition.key == key))
    return res.scalar_one_or_none()


async def resolve_device(db: AsyncSession, device_uid: str) -> Device:
    res = await db.execute(select(Device).where(Device.device_uid == device_uid))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")
    if device.last_seen_at is None:
        raise_api_error(404, "DEVICE_NOT_PROVISIONED", "device not provisioned")
    return device


async def resolve_device_for_vars(db: AsyncSession, device_uid: str) -> Device:
    res = await db.execute(select(Device).where(Device.device_uid == device_uid))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")
    if device.last_seen_at is None:
        raise_api_error(409, "VAR_DEVICE_NOT_PROVISIONED", "device not provisioned")
    return device


async def create_definition(
    db: AsyncSession,
    *,
    key: str,
    scope: str,
    value_type: str,
    default_value: Any | None,
    description: str | None,
    unit: str | None,
    min_value: float | None,
    max_value: float | None,
    enum_values: list[str] | None,
    regex: str | None,
    is_secret: bool,
    is_readonly: bool,
    user_writable: bool,
    device_writable: bool,
    allow_device_override: bool,
) -> VariableDefinition:
    existing = await get_definition(db, key)
    if existing is not None:
        raise_api_error(409, "VAR_DEF_EXISTS", "variable definition already exists")
    if default_value is not None:
        dummy = VariableDefinition(
            key=key,
            scope=scope,
            value_type=value_type,
            default_value=None,
            description=description,
            unit=unit,
            min_value=min_value,
            max_value=max_value,
            enum_values=enum_values,
            regex=regex,
            is_secret=is_secret,
            is_readonly=is_readonly,
            user_writable=user_writable,
            device_writable=device_writable,
            allow_device_override=allow_device_override,
        )
        default_value = validate_and_coerce_value(dummy, default_value)
    definition = VariableDefinition(
        key=key,
        scope=scope,
        value_type=value_type,
        default_value=default_value,
        description=description,
        unit=unit,
        min_value=min_value,
        max_value=max_value,
        enum_values=enum_values,
        regex=regex,
        is_secret=is_secret,
        is_readonly=is_readonly,
        user_writable=user_writable,
        device_writable=device_writable,
        allow_device_override=allow_device_override,
    )
    db.add(definition)
    await db.flush()
    invalidate_effective_cache()
    return definition


async def get_value(
    db: AsyncSession,
    *,
    key: str,
    scope: str,
    device_uid: str | None,
    user_id: int | None,
) -> tuple[VariableDefinition, VariableValue | None, Device | None]:
    definition = await get_definition(db, key)
    if definition is None:
        raise_api_error(404, "VAR_DEF_NOT_FOUND", "variable definition not found")
    if definition.scope != scope:
        raise_api_error(409, "VAR_SCOPE_MISMATCH", "scope mismatch")

    device = None
    device_id = None
    if scope == "device":
        if not device_uid:
            raise_api_error(422, "VAR_DEVICE_UID_REQUIRED", "device_uid required")
        device = await resolve_device(db, device_uid)
        device_id = device.id
    elif scope == "user":
        if user_id is None:
            raise_api_error(403, "VAR_NOT_ALLOWED", "user scope requires user auth")
        user_id = int(user_id)
    elif device_uid:
        raise_api_error(409, "VAR_SCOPE_MISMATCH", "device_uid not allowed for global scope")

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.variable_key == definition.key,
            VariableValue.scope == scope,
            VariableValue.device_id == device_id,
            VariableValue.user_id == user_id,
        )
    )
    value = res.scalar_one_or_none()
    return definition, value, device


async def create_or_update_value(
    db: AsyncSession,
    *,
    key: str,
    scope: str,
    device_uid: str | None,
    value: Any,
    expected_version: int | None,
    actor_user_id: int | None,
    actor_device_id: int | None,
) -> tuple[VariableDefinition, VariableValue, Device | None]:
    definition = await get_definition(db, key)
    if definition is None:
        raise_api_error(404, "VAR_DEF_NOT_FOUND", "variable definition not found")
    if definition.scope != scope:
        raise_api_error(409, "VAR_SCOPE_MISMATCH", "scope mismatch")
    if definition.is_readonly:
        raise_api_error(409, "VAR_READONLY", "variable is read-only")

    device = None
    device_id = None
    if scope == "device":
        if not device_uid:
            raise_api_error(422, "VAR_DEVICE_UID_REQUIRED", "device_uid required")
        device = await resolve_device(db, device_uid)
        device_id = device.id
    elif device_uid:
        raise_api_error(409, "VAR_SCOPE_MISMATCH", "device_uid not allowed for global scope")

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.variable_key == definition.key,
            VariableValue.scope == scope,
            VariableValue.device_id == device_id,
            VariableValue.user_id.is_(None),
        )
    )
    current = res.scalar_one_or_none()

    current_version = current.version if current is not None else None
    if expected_version is not None and expected_version != current_version:
        raise_api_error(
            409,
            "VAR_VERSION_CONFLICT",
            "variable version conflict",
            meta={"current_version": current_version},
        )

    coerced = validate_and_coerce_value(definition, value)
    now = _now_utc()

    old_value = current.value_json if current is not None else None
    old_version = current.version if current is not None else None

    if current is None:
        current = VariableValue(
            variable_key=definition.key,
            scope=scope,
            device_id=device_id,
            value_json=coerced,
            version=1,
            updated_at=now,
            updated_by_user_id=actor_user_id,
            updated_by_device_id=actor_device_id,
        )
        db.add(current)
    else:
        current.value_json = coerced
        current.version = current.version + 1
        current.updated_at = now
        current.updated_by_user_id = actor_user_id
        current.updated_by_device_id = actor_device_id

    masked_old = mask_if_secret(definition, old_value)
    masked_new = mask_if_secret(definition, coerced)
    audit = VariableAudit(
        variable_key=definition.key,
        scope=scope,
        device_id=device_id,
        old_value_json=masked_old,
        new_value_json=masked_new,
        old_version=old_version,
        new_version=current.version,
        actor_type="user" if actor_user_id else "device",
        actor_user_id=actor_user_id,
        actor_device_id=actor_device_id,
        created_at=now,
    )
    db.add(audit)
    await db.flush()
    invalidate_effective_cache()
    return definition, current, device


async def _device_busy(db: AsyncSession, device_id: int) -> bool:
    now = _now_utc()
    res = await db.execute(
        select(Task.id).where(
            Task.client_id == device_id,
            Task.status == "in_flight",
            Task.lease_expires_at.is_not(None),
            Task.lease_expires_at > now,
            Task.lease_token.is_not(None),
        )
    )
    return res.scalar_one_or_none() is not None


async def _pairing_active(db: AsyncSession, device_uid: str) -> bool:
    now = _now_utc()
    res = await db.execute(
        select(PairingSession.id).where(
            PairingSession.device_uid == device_uid,
            PairingSession.is_used.is_(False),
            PairingSession.expires_at > now,
        )
    )
    return res.scalar_one_or_none() is not None


async def create_or_update_value_v2(
    db: AsyncSession,
    *,
    key: str,
    scope: str,
    device_uid: str | None,
    value: Any,
    expected_version: int | None,
    actor_user_id: int | None,
    actor_device_id: int | None,
    force: bool,
    dev_tools: bool,
) -> tuple[VariableDefinition, VariableValue, Device | None]:
    definition = await get_definition(db, key)
    if definition is None:
        raise_api_error(404, "VAR_DEF_NOT_FOUND", "variable definition not found")
    if definition.scope != scope:
        raise_api_error(409, "VAR_SCOPE_MISMATCH", "scope mismatch")
    if definition.is_readonly:
        raise_api_error(409, "VAR_READ_ONLY", "variable is read-only")

    actor_is_user = actor_user_id is not None
    actor_is_device = actor_device_id is not None
    if scope == "user" and not actor_is_user:
        raise_api_error(403, "VAR_NOT_ALLOWED", "user scope requires user auth")
    if scope == "global" and not actor_is_user:
        raise_api_error(403, "VAR_NOT_ALLOWED", "global scope requires user auth")

    if actor_is_user and not definition.user_writable:
        raise_api_error(403, "VAR_NOT_ALLOWED", "variable not user writable")
    if actor_is_device and not definition.device_writable:
        raise_api_error(403, "VAR_NOT_ALLOWED", "variable not device writable")

    device = None
    device_id = None
    user_id = None
    if scope == "device":
        if not device_uid:
            raise_api_error(422, "VAR_DEVICE_UID_REQUIRED", "device_uid required")
        device = await resolve_device_for_vars(db, device_uid)
        device_id = device.id
        if not definition.allow_device_override:
            raise_api_error(409, "VAR_NOT_ALLOWED", "device override not allowed")
        if actor_is_device and device.id != actor_device_id:
            raise_api_error(403, "VAR_NOT_ALLOWED", "device token mismatch")
        if device.owner_user_id is None and not dev_tools:
            raise_api_error(403, "VAR_NOT_ALLOWED", "device not claimed")
        if device.owner_user_id is not None and actor_is_user and device.owner_user_id != actor_user_id:
            raise_api_error(404, "DEVICE_NOT_OWNED", "device not owned")
        if await _device_busy(db, device.id) and not force:
            raise_api_error(409, "VAR_DEVICE_BUSY", "device busy")
        if await _pairing_active(db, device.device_uid) and not force:
            raise_api_error(409, "VAR_DEVICE_PAIRING_ACTIVE", "pairing active")
    elif scope == "user":
        user_id = actor_user_id

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.variable_key == definition.key,
            VariableValue.scope == scope,
            VariableValue.device_id == device_id,
            VariableValue.user_id == user_id,
        )
    )
    current = res.scalar_one_or_none()
    current_version = current.version if current is not None else None

    if expected_version is not None and expected_version != current_version:
        raise_api_error(
            409,
            "VAR_VERSION_CONFLICT",
            "variable version conflict",
            meta={"expected": expected_version, "got": current_version},
        )

    coerced = validate_and_coerce_value(definition, value)
    now = _now_utc()

    old_value = current.value_json if current is not None else None
    old_version = current.version if current is not None else None

    if current is None:
        current = VariableValue(
            variable_key=definition.key,
            scope=scope,
            device_id=device_id,
            user_id=user_id,
            value_json=coerced,
            version=1,
            updated_at=now,
            updated_by_user_id=actor_user_id,
            updated_by_device_id=actor_device_id,
        )
        db.add(current)
    else:
        current.value_json = coerced
        current.version = current.version + 1
        current.updated_at = now
        current.updated_by_user_id = actor_user_id
        current.updated_by_device_id = actor_device_id

    masked_old = mask_if_secret(definition, old_value)
    masked_new = mask_if_secret(definition, coerced)
    audit = VariableAudit(
        variable_key=definition.key,
        scope=scope,
        device_id=device_id,
        old_value_json=masked_old,
        new_value_json=masked_new,
        old_version=old_version,
        new_version=current.version,
        actor_type="user" if actor_user_id else "device",
        actor_user_id=actor_user_id,
        actor_device_id=actor_device_id,
        created_at=now,
    )
    db.add(audit)
    await db.flush()
    invalidate_effective_cache()
    return definition, current, device


async def resolve_effective_snapshot(
    db: AsyncSession,
    *,
    device_id: int,
    device_uid: str,
    user_id: int,
    include_secrets: bool,
) -> tuple[str, datetime, str, list[dict[str, Any]]]:
    cached = _cache_get(user_id, device_uid, include_secrets)
    if cached:
        return (
            cached["snapshot_id"],
            cached["resolved_at"],
            cached["effective_version"],
            cached["items"],
        )

    definitions, globals_values, device_values, user_values = await list_effective_values(
        db, device_id=device_id, user_id=user_id
    )
    resolved_at = _now_utc()
    snapshot_id = uuid4().hex

    items: list[dict[str, Any]] = []
    timestamps: list[datetime] = []

    for definition in definitions:
        stored = None
        source = "default"
        precedence = 0
        if definition.scope == "global":
            stored = globals_values.get(definition.key)
            if stored:
                source = "global"
                precedence = 1
        elif definition.scope == "user":
            stored = user_values.get(definition.key)
            if stored:
                source = "user"
                precedence = 2
        elif definition.scope == "device":
            stored = device_values.get(definition.key)
            if stored:
                source = "device"
                precedence = 3

        effective = get_effective_value(
            definition, stored.value_json if stored else None
        )
        masked = definition.is_secret
        value_out = None if masked else effective

        items.append(
            {
                "key": definition.key,
                "value": value_out,
                "scope": definition.scope,
                "device_uid": device_uid if definition.scope == "device" else None,
                "version": stored.version if stored else None,
                "updated_at": stored.updated_at if stored else None,
                "is_secret": definition.is_secret,
                "masked": masked,
                "source": source,
                "precedence": precedence,
                "resolved_type": definition.value_type,
                "constraints": _constraints(definition),
                "value_json": None if masked else effective,
            }
        )

        if stored and stored.updated_at:
            timestamps.append(stored.updated_at)
        else:
            timestamps.append(definition.updated_at)

    effective_dt = max(timestamps) if timestamps else resolved_at
    effective_version = effective_dt.isoformat()

    snapshot = VariableSnapshot(
        id=snapshot_id,
        device_id=device_id,
        user_id=user_id,
        resolved_at=resolved_at,
        effective_version=effective_version,
    )
    db.add(snapshot)

    for item in items:
        db.add(
            VariableSnapshotItem(
                snapshot_id=snapshot_id,
                variable_key=item["key"],
                scope=item["scope"],
                device_id=device_id if item["scope"] == "device" else None,
                source=item["source"],
                value_json=item["value_json"],
                masked=item["masked"],
                is_secret=item["is_secret"],
                version=item["version"],
                updated_at=item["updated_at"],
                precedence=item["precedence"],
                resolved_type=item["resolved_type"],
                constraints=item["constraints"],
            )
        )

    await db.flush()
    _cache_set(
        user_id,
        device_uid,
        include_secrets,
        {
            "snapshot_id": snapshot_id,
            "resolved_at": resolved_at,
            "effective_version": effective_version,
            "items": items,
        },
    )
    return snapshot_id, resolved_at, effective_version, items


async def record_applied_ack(
    db: AsyncSession,
    *,
    snapshot_id: str,
    device_id: int,
    key: str,
    version: int | None,
    status: str,
    reason: str | None,
) -> bool:
    res = await db.execute(
        select(VariableAppliedAck.id).where(
            VariableAppliedAck.snapshot_id == snapshot_id,
            VariableAppliedAck.device_id == device_id,
            VariableAppliedAck.variable_key == key,
            VariableAppliedAck.version == version,
        )
    )
    if res.scalar_one_or_none() is not None:
        return False
    db.add(
        VariableAppliedAck(
            snapshot_id=snapshot_id,
            device_id=device_id,
            variable_key=key,
            version=version,
            status=status,
            reason=reason,
        )
    )
    await db.flush()
    return True


async def list_applied_acks(
    db: AsyncSession,
    *,
    device_uid: str,
    limit: int,
) -> list[VariableAppliedAck]:
    device = await resolve_device(db, device_uid)
    stmt = (
        select(VariableAppliedAck)
        .where(VariableAppliedAck.device_id == device.id)
        .order_by(VariableAppliedAck.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def list_definitions(db: AsyncSession, scope: str | None) -> list[VariableDefinition]:
    stmt = select(VariableDefinition)
    if scope:
        stmt = stmt.where(VariableDefinition.scope == scope)
    res = await db.execute(stmt.order_by(VariableDefinition.key))
    return list(res.scalars().all())


async def list_device_values(
    db: AsyncSession, device_uid: str
) -> tuple[Device, list[VariableDefinition], list[VariableDefinition], dict[str, VariableValue], dict[str, VariableValue]]:
    device = await resolve_device(db, device_uid)
    res = await db.execute(select(VariableDefinition))
    definitions = list(res.scalars().all())
    globals_defs = [d for d in definitions if d.scope == "global"]
    device_defs = [d for d in definitions if d.scope == "device"]

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.scope == "global",
            VariableValue.device_id.is_(None),
        )
    )
    globals_values = {v.variable_key: v for v in res.scalars().all()}

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.scope == "device",
            VariableValue.device_id == device.id,
        )
    )
    device_values = {v.variable_key: v for v in res.scalars().all()}
    return device, globals_defs, device_defs, globals_values, device_values


async def list_effective_values(
    db: AsyncSession, *, device_id: int, user_id: int
) -> tuple[
    list[VariableDefinition],
    dict[str, VariableValue],
    dict[str, VariableValue],
    dict[str, VariableValue],
]:
    res = await db.execute(select(VariableDefinition))
    definitions = list(res.scalars().all())

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.scope == "global",
            VariableValue.device_id.is_(None),
            VariableValue.user_id.is_(None),
        )
    )
    globals_values = {v.variable_key: v for v in res.scalars().all()}

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.scope == "device",
            VariableValue.device_id == device_id,
        )
    )
    device_values = {v.variable_key: v for v in res.scalars().all()}

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.scope == "user",
            VariableValue.user_id == user_id,
        )
    )
    user_values = {v.variable_key: v for v in res.scalars().all()}
    return definitions, globals_values, device_values, user_values


async def list_audit(
    db: AsyncSession,
    *,
    key: str,
    scope: str | None,
    device_uid: str | None,
    limit: int,
    offset: int,
) -> list[VariableAudit]:
    device_id = None
    if device_uid:
        res = await db.execute(select(Device.id).where(Device.device_uid == device_uid))
        row = res.scalar_one_or_none()
        if row is None:
            raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")
        device_id = row
    stmt = select(VariableAudit).where(VariableAudit.variable_key == key)
    if scope:
        stmt = stmt.where(VariableAudit.scope == scope)
    if device_id is not None:
        stmt = stmt.where(VariableAudit.device_id == device_id)
    stmt = stmt.order_by(VariableAudit.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all())
