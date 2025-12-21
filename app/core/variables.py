import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.error_utils import raise_api_error
from app.db.models.device import Device
from app.db.models.variables import VariableDefinition, VariableValue, VariableAudit


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


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


async def create_definition(
    db: AsyncSession,
    *,
    key: str,
    scope: str,
    value_type: str,
    default_value: Any | None,
    description: str | None,
    is_secret: bool,
    is_readonly: bool,
) -> VariableDefinition:
    existing = await get_definition(db, key)
    if existing is not None:
        raise_api_error(409, "VAR_DEF_EXISTS", "variable definition already exists")
    if default_value is not None:
        default_value = validate_and_coerce(default_value, value_type)
    definition = VariableDefinition(
        key=key,
        scope=scope,
        value_type=value_type,
        default_value=default_value,
        description=description,
        is_secret=is_secret,
        is_readonly=is_readonly,
    )
    db.add(definition)
    await db.flush()
    return definition


async def get_value(
    db: AsyncSession,
    *,
    key: str,
    scope: str,
    device_uid: str | None,
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
    elif device_uid:
        raise_api_error(409, "VAR_SCOPE_MISMATCH", "device_uid not allowed for global scope")

    res = await db.execute(
        select(VariableValue).where(
            VariableValue.variable_key == definition.key,
            VariableValue.scope == scope,
            VariableValue.device_id == device_id,
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

    coerced = validate_and_coerce(value, definition.value_type)
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
    return definition, current, device


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
    db: AsyncSession, device_id: int
) -> tuple[list[VariableDefinition], dict[str, VariableValue], dict[str, VariableValue]]:
    res = await db.execute(select(VariableDefinition))
    definitions = list(res.scalars().all())

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
            VariableValue.device_id == device_id,
        )
    )
    device_values = {v.variable_key: v for v in res.scalars().all()}
    return definitions, globals_values, device_values


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
