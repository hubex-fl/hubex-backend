from datetime import datetime, timezone
import os

from fastapi import APIRouter, Depends, Query, Body, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import (
    get_current_user,
    get_current_device,
    bearer,
    device_token_header,
)
from app.api.v1.error_utils import raise_api_error
from app.core import variables as vars_core
from app.schemas.variables import (
    VariableDefinitionIn,
    VariableDefinitionOut,
    VariableValueIn,
    VariableSetIn,
    VariableValueOut,
    DeviceVariablesOut,
    EffectiveVariableOut,
    EffectiveVariablesOut,
    VariableAppliedIn,
    VariableAuditOut,
)
from app.db.models.device import Device

router = APIRouter(prefix="/variables", tags=["variables"])


def _dev_tools_enabled() -> bool:
    return os.getenv("HUBEX_DEV_TOOLS", "0") == "1"


async def _resolve_actor(
    db: AsyncSession,
    user_creds: HTTPAuthorizationCredentials | None,
    device_token: str | None,
):
    user = None
    device = None
    if user_creds and user_creds.credentials:
        user = await get_current_user(creds=user_creds, db=db)
    if device_token:
        device = await get_current_device(device_token=device_token, db=db)
    if user:
        return user, None
    if device:
        return None, device
    raise_api_error(401, "AUTH_REQUIRED", "authentication required")


@router.get("/definitions", response_model=list[VariableDefinitionOut])
async def list_definitions(
    scope: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    definitions = await vars_core.list_definitions(db, scope)
    return definitions


@router.get("/defs", response_model=list[VariableDefinitionOut])
async def list_definitions_v2(
    scope: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    definitions = await vars_core.list_definitions(db, scope)
    return definitions


@router.post("/definitions", response_model=VariableDefinitionOut)
async def create_definition(
    data: VariableDefinitionIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    async with db.begin_nested():
        definition = await vars_core.create_definition(
            db,
            key=data.key,
            scope=data.scope,
            value_type=data.value_type,
            default_value=data.default_value,
            description=data.description,
            unit=data.unit,
            min_value=data.min_value,
            max_value=data.max_value,
            enum_values=data.enum_values,
            regex=data.regex,
            is_secret=data.is_secret,
            is_readonly=data.is_readonly,
            user_writable=data.user_writable,
            device_writable=data.device_writable,
            allow_device_override=data.allow_device_override,
        )
    return definition


@router.post("/defs", response_model=VariableDefinitionOut)
async def create_definition_v2(
    data: VariableDefinitionIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _dev_tools_enabled():
        raise_api_error(403, "DEV_TOOLS_DISABLED", "dev tools disabled")
    async with db.begin_nested():
        definition = await vars_core.create_definition(
            db,
            key=data.key,
            scope=data.scope,
            value_type=data.value_type,
            default_value=data.default_value,
            description=data.description,
            unit=data.unit,
            min_value=data.min_value,
            max_value=data.max_value,
            enum_values=data.enum_values,
            regex=data.regex,
            is_secret=data.is_secret,
            is_readonly=data.is_readonly,
            user_writable=data.user_writable,
            device_writable=data.device_writable,
            allow_device_override=data.allow_device_override,
        )
    return definition


@router.get("/value", response_model=VariableValueOut)
async def get_value(
    key: str = Query(...),
    scope: str = Query(...),
    device_uid: str | None = Query(default=None, alias="deviceUid"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    definition, value, device = await vars_core.get_value(
        db, key=key, scope=scope, device_uid=device_uid, user_id=current_user.id
    )
    effective = vars_core.get_effective_value(definition, value.value_json if value else None)
    masked = vars_core.mask_if_secret(definition, effective)
    return VariableValueOut(
        key=definition.key,
        scope=definition.scope,
        device_uid=device_uid,
        value=masked,
        version=value.version if value else None,
        updated_at=value.updated_at if value else None,
        is_secret=definition.is_secret,
    )


@router.put("/value", response_model=VariableValueOut)
async def put_value(
    data: VariableValueIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    async with db.begin_nested():
        definition, value, device = await vars_core.create_or_update_value(
            db,
            key=data.key,
            scope=data.scope,
            device_uid=data.device_uid,
            value=data.value,
            expected_version=data.expected_version,
            actor_user_id=current_user.id,
            actor_device_id=None,
        )
    masked = vars_core.mask_if_secret(definition, value.value_json)
    return VariableValueOut(
        key=definition.key,
        scope=definition.scope,
        device_uid=data.device_uid,
        value=masked,
        version=value.version,
        updated_at=value.updated_at,
        is_secret=definition.is_secret,
    )


@router.post("/set", response_model=VariableValueOut)
async def set_value(
    data: VariableSetIn = Body(...),
    db: AsyncSession = Depends(get_db),
    user_creds: HTTPAuthorizationCredentials | None = Security(bearer),
    device_token: str | None = Security(device_token_header),
):
    current_user, current_device = await _resolve_actor(db, user_creds, device_token)
    async with db.begin_nested():
        definition, value, device = await vars_core.create_or_update_value_v2(
            db,
            key=data.key,
            scope=data.scope,
            device_uid=data.device_uid,
            value=data.value,
            expected_version=data.expected_version,
            actor_user_id=current_user.id if current_user else None,
            actor_device_id=current_device.id if current_device else None,
            force=data.force,
            dev_tools=_dev_tools_enabled(),
        )
    masked = vars_core.mask_if_secret(definition, value.value_json)
    return VariableValueOut(
        key=definition.key,
        scope=definition.scope,
        device_uid=data.device_uid,
        value=masked,
        version=value.version,
        updated_at=value.updated_at,
        is_secret=definition.is_secret,
    )


@router.get("/device/{device_uid}", response_model=DeviceVariablesOut)
async def list_device_variables(
    device_uid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    device, globals_defs, device_defs, globals_values, device_values = await vars_core.list_device_values(
        db, device_uid
    )

    globals_out: list[VariableValueOut] = []
    for definition in globals_defs:
        stored = globals_values.get(definition.key)
        effective = vars_core.get_effective_value(definition, stored.value_json if stored else None)
        globals_out.append(
            VariableValueOut(
                key=definition.key,
                scope=definition.scope,
                device_uid=None,
                value=vars_core.mask_if_secret(definition, effective),
                version=stored.version if stored else None,
                updated_at=stored.updated_at if stored else None,
                is_secret=definition.is_secret,
            )
        )

    device_out: list[VariableValueOut] = []
    for definition in device_defs:
        stored = device_values.get(definition.key)
        effective = vars_core.get_effective_value(definition, stored.value_json if stored else None)
        device_out.append(
            VariableValueOut(
                key=definition.key,
                scope=definition.scope,
                device_uid=device_uid,
                value=vars_core.mask_if_secret(definition, effective),
                version=stored.version if stored else None,
                updated_at=stored.updated_at if stored else None,
                is_secret=definition.is_secret,
            )
        )

    return DeviceVariablesOut(device_uid=device_uid, globals=globals_out, device=device_out)


@router.get("/effective", response_model=EffectiveVariablesOut)
async def get_effective_variables(
    device_uid: str = Query(..., alias="deviceUid"),
    include_secrets: bool = Query(default=False, alias="includeSecrets"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await db.execute(select(Device).where(Device.device_uid == device_uid))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
    if device.owner_user_id != current_user.id:
        raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")

    definitions, globals_values, device_values, user_values = await vars_core.list_effective_values(
        db, device_id=device.id, user_id=current_user.id
    )
    computed_at = datetime.now(timezone.utc)

    items: list[EffectiveVariableOut] = []
    timestamps: list[datetime] = []
    for definition in definitions:
        stored = None
        source = "default"
        if definition.scope == "global":
            stored = globals_values.get(definition.key)
            source = "global" if stored else "default"
        elif definition.scope == "user":
            stored = user_values.get(definition.key)
            source = "user" if stored else "default"
        elif definition.scope == "device":
            stored = device_values.get(definition.key)
            source = "device" if stored else "default"

        effective = vars_core.get_effective_value(
            definition, stored.value_json if stored else None
        )

        value_out = effective
        if definition.is_secret and not include_secrets:
            value_out = None

        items.append(
            EffectiveVariableOut(
                key=definition.key,
                value=value_out,
                scope=definition.scope,
                version=stored.version if stored else None,
                updated_at=stored.updated_at if stored else None,
                is_secret=definition.is_secret,
                source=source,
                resolved_type=definition.value_type,
                constraints=vars_core._constraints(definition),
            )
        )
        if stored and stored.updated_at:
            timestamps.append(stored.updated_at)
        else:
            timestamps.append(definition.updated_at)

    effective_dt = max(timestamps) if timestamps else computed_at
    return EffectiveVariablesOut(
        device_uid=device_uid,
        computed_at=computed_at,
        effective_version=effective_dt.isoformat(),
        items=items,
    )


@router.post("/applied")
async def applied(
    data: VariableAppliedIn = Body(...),
    db: AsyncSession = Depends(get_db),
    device=Depends(get_current_device),
):
    if device.device_uid != data.device_uid:
        raise_api_error(409, "VAR_NOT_ALLOWED", "device uid mismatch")
    return {"ok": True, "count": len(data.applied)}


@router.get("/audit", response_model=list[VariableAuditOut])
async def list_audit(
    key: str = Query(...),
    scope: str | None = Query(default=None),
    device_uid: str | None = Query(default=None, alias="deviceUid"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await vars_core.list_audit(
        db,
        key=key,
        scope=scope,
        device_uid=device_uid,
        limit=limit,
        offset=offset,
    )
    device_ids = {item.device_id for item in items if item.device_id is not None}
    device_uid_map: dict[int, str] = {}
    if device_ids:
        res = await db.execute(select(Device.id, Device.device_uid).where(Device.id.in_(device_ids)))
        device_uid_map = {row[0]: row[1] for row in res.all()}
    out: list[VariableAuditOut] = []
    for item in items:
        out.append(
            VariableAuditOut(
                variable_key=item.variable_key,
                scope=item.scope,
                device_uid=device_uid_map.get(item.device_id),
                old_value=item.old_value_json,
                new_value=item.new_value_json,
                old_version=item.old_version,
                new_version=item.new_version,
                actor_type=item.actor_type,
                actor_user_id=item.actor_user_id,
                actor_device_id=item.actor_device_id,
                request_id=item.request_id,
                note=item.note,
                created_at=item.created_at,
            )
        )
    return out
