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
from app.core.system_events import emit_system_event
from app.core.variable_effects import run_effects_once
from app.schemas.variables import (
    VariableDefinitionIn,
    VariableDefinitionPatchIn,
    VariableDefinitionOut,
    VariableValueIn,
    VariableSetIn,
    VariableValueOut,
    DeviceVariablesOut,
    EffectiveVariableOut,
    EffectiveVariablesOut,
    VariableSnapshotV3Out,
    VariableAckIn,
    VariableAckOut,
    VariableAppliedIn,
    VariableAppliedAckOut,
    VariableAuditOut,
    VariableEffectOut,
    VariableEffectRunIn,
    VariableEffectRunOut,
    VariableHistoryOut,
    VariableHistoryPointOut,
    BulkSetItem,
    BulkSetIn,
    BulkSetResult,
)
from app.db.models.device import Device
from app.db.models.variables import (
    VariableSnapshot,
    VariableSnapshotItem,
    VariableEffect,
    VariableDefinition,
    VariableValue,
    VariableHistory,
)

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
    try:
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
            display_hint=data.display_hint,
            category=data.category,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return definition


@router.post("/defs", response_model=VariableDefinitionOut)
async def create_definition_v2(
    data: VariableDefinitionIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _dev_tools_enabled():
        raise_api_error(403, "DEV_TOOLS_DISABLED", "dev tools disabled")
    try:
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
            display_hint=data.display_hint,
            category=data.category,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return definition


@router.patch("/definitions/{key}", response_model=VariableDefinitionOut)
async def patch_definition(
    key: str,
    data: VariableDefinitionPatchIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update mutable fields of a variable definition."""
    res = await db.execute(
        select(VariableDefinition).where(VariableDefinition.key == key)
    )
    defn = res.scalar_one_or_none()
    if defn is None:
        raise_api_error(404, "VAR_DEF_NOT_FOUND", "Variable definition not found")

    patch = data.model_dump(exclude_unset=True)
    for field, value in patch.items():
        setattr(defn, field, value)
    await db.commit()
    await db.refresh(defn)
    return defn


@router.delete("/definitions/{key}")
async def delete_definition(
    key: str,
    confirm: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a variable definition and all associated values/history."""
    res = await db.execute(
        select(VariableDefinition).where(VariableDefinition.key == key)
    )
    defn = res.scalar_one_or_none()
    if defn is None:
        raise_api_error(404, "VAR_DEF_NOT_FOUND", "Variable definition not found")
    if not confirm:
        raise_api_error(400, "DELETE_REQUIRES_CONFIRM", "Pass ?confirm=true to delete")

    from sqlalchemy import delete
    from app.db.models.variables import VariableAudit, VariableAppliedAck

    # Cascade delete related rows
    await db.execute(delete(VariableHistory).where(VariableHistory.variable_key == key))
    await db.execute(delete(VariableAppliedAck).where(VariableAppliedAck.variable_key == key))
    await db.execute(delete(VariableAudit).where(VariableAudit.variable_key == key))
    await db.execute(delete(VariableSnapshotItem).where(VariableSnapshotItem.variable_key == key))
    await db.execute(delete(VariableValue).where(VariableValue.variable_key == key))
    await db.execute(delete(VariableDefinition).where(VariableDefinition.key == key))
    await db.commit()
    return {"ok": True, "deleted_key": key}


@router.get("/history", response_model=VariableHistoryOut)
async def get_variable_history(
    key: str = Query(...),
    device_uid: str | None = Query(default=None, alias="deviceUid"),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=500, ge=1, le=2000),
    downsample: int | None = Query(default=None, ge=10, le=86400),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get time-series history for a variable. Optionally downsample."""
    from sqlalchemy import func as sa_func, cast, Float

    now = datetime.now(timezone.utc)
    if from_time is None:
        from_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if to_time is None:
        to_time = now

    # Resolve device_id from uid
    device_id = None
    if device_uid:
        res = await db.execute(select(Device.id).where(Device.device_uid == device_uid))
        device_id = res.scalar_one_or_none()

    stmt = (
        select(VariableHistory)
        .where(
            VariableHistory.variable_key == key,
            VariableHistory.recorded_at >= from_time,
            VariableHistory.recorded_at <= to_time,
        )
    )
    if device_id is not None:
        stmt = stmt.where(VariableHistory.device_id == device_id)

    if downsample and downsample > 0:
        # SQL-level downsampling: bucket by seconds, return avg/min/max
        from sqlalchemy import literal_column
        epoch = sa_func.extract("epoch", VariableHistory.recorded_at)
        bucket = sa_func.floor(epoch / downsample) * downsample

        bucket_stmt = (
            select(
                sa_func.to_timestamp(bucket).label("bucket_time"),
                sa_func.avg(VariableHistory.numeric_value).label("avg_val"),
                sa_func.min(VariableHistory.numeric_value).label("min_val"),
                sa_func.max(VariableHistory.numeric_value).label("max_val"),
                sa_func.count().label("cnt"),
            )
            .where(
                VariableHistory.variable_key == key,
                VariableHistory.recorded_at >= from_time,
                VariableHistory.recorded_at <= to_time,
                VariableHistory.numeric_value.is_not(None),
            )
        )
        if device_id is not None:
            bucket_stmt = bucket_stmt.where(VariableHistory.device_id == device_id)

        bucket_stmt = (
            bucket_stmt
            .group_by(bucket)
            .order_by(bucket)
            .limit(limit)
        )
        res = await db.execute(bucket_stmt)
        rows = res.all()
        points = [
            VariableHistoryPointOut(
                recorded_at=row.bucket_time,
                value={"avg": round(row.avg_val, 4) if row.avg_val is not None else None,
                       "min": round(row.min_val, 4) if row.min_val is not None else None,
                       "max": round(row.max_val, 4) if row.max_val is not None else None,
                       "count": row.cnt},
                numeric_value=round(row.avg_val, 4) if row.avg_val is not None else None,
                source="aggregated",
            )
            for row in rows
        ]
        return VariableHistoryOut(key=key, device_uid=device_uid, points=points, downsampled=True)

    # Raw points
    stmt = stmt.order_by(VariableHistory.recorded_at.desc()).limit(limit)
    res = await db.execute(stmt)
    rows = res.scalars().all()
    points = [
        VariableHistoryPointOut(
            recorded_at=row.recorded_at,
            value=row.value_json,
            numeric_value=row.numeric_value,
            source=row.source,
        )
        for row in reversed(rows)  # oldest first
    ]
    return VariableHistoryOut(key=key, device_uid=device_uid, points=points, downsampled=False)


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
    try:
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
        await emit_system_event(db, "variable.changed", {
            "key": data.key,
            "scope": data.scope,
            "device_uid": data.device_uid,
            "version": value.version,
        })
        await db.commit()
    except Exception:
        await db.rollback()
        raise
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
    try:
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
        await db.commit()
    except Exception:
        await db.rollback()
        raise
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


@router.post("/bulk-set", response_model=BulkSetResult)
async def bulk_set_values(
    data: BulkSetIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Set multiple variable values in a single request.

    If allow_partial=True (default), failures are collected and the successful
    items are committed. If allow_partial=False, any single failure rolls back
    all changes.
    """
    succeeded: list[str] = []
    failed: list[dict] = []

    if data.allow_partial:
        # Process items individually; collect failures without rolling back successes
        for item in data.items:
            try:
                await vars_core.create_or_update_value(
                    db,
                    key=item.key,
                    scope=item.scope,
                    device_uid=item.device_uid,
                    value=item.value,
                    expected_version=None,
                    actor_user_id=current_user.id,
                    actor_device_id=None,
                )
                succeeded.append(item.key)
            except Exception as exc:
                await db.rollback()
                failed.append({"key": item.key, "error": str(exc)})
        if succeeded:
            try:
                await db.commit()
            except Exception as exc:
                await db.rollback()
                # Move all previously-succeeded items to failed
                for key in succeeded:
                    failed.append({"key": key, "error": str(exc)})
                succeeded = []
    else:
        # All-or-nothing: any failure rolls back everything
        try:
            for item in data.items:
                await vars_core.create_or_update_value(
                    db,
                    key=item.key,
                    scope=item.scope,
                    device_uid=item.device_uid,
                    value=item.value,
                    expected_version=None,
                    actor_user_id=current_user.id,
                    actor_device_id=None,
                )
                succeeded.append(item.key)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            failed_key = data.items[len(succeeded)].key if len(succeeded) < len(data.items) else "unknown"
            failed.append({"key": failed_key, "error": str(exc)})
            succeeded = []

    return BulkSetResult(
        succeeded=succeeded,
        failed=failed,
        total=len(data.items),
        success_count=len(succeeded),
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

    try:
        snapshot_id, resolved_at, effective_version, effective_rev, items_raw = (
            await vars_core.resolve_effective_snapshot(
                db,
                device_id=device.id,
                device_uid=device_uid,
                user_id=current_user.id,
                include_secrets=include_secrets,
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    items: list[EffectiveVariableOut] = []
    for item in items_raw:
        items.append(
            EffectiveVariableOut(
                key=item["key"],
                value=item["value"],
                scope=item["scope"],
                device_uid=item["device_uid"],
                version=item["version"],
                updated_at=item["updated_at"],
                is_secret=item["is_secret"],
                masked=item["masked"],
                source=item["source"],
                precedence=item["precedence"],
                resolved_type=item["resolved_type"],
                constraints=item["constraints"],
            )
        )

    return EffectiveVariablesOut(
        device_uid=device_uid,
        computed_at=resolved_at,
        resolved_at=resolved_at,
        snapshot_id=snapshot_id,
        effective_version=effective_version,
        effective_rev=effective_rev,
        scope="device",
        items=items,
    )


@router.get("/snapshot", response_model=VariableSnapshotV3Out)
async def get_snapshot_v3(
    device_uid: str | None = Query(default=None, alias="deviceUid"),
    db: AsyncSession = Depends(get_db),
    user_creds: HTTPAuthorizationCredentials | None = Security(bearer),
    device_token: str | None = Security(device_token_header),
):
    current_user, current_device = await _resolve_actor(db, user_creds, device_token)
    device = None
    if current_device:
        device = current_device
        device_uid = device.device_uid
        user_id = device.owner_user_id or 0
    else:
        if not device_uid:
            raise_api_error(422, "VAR_DEVICE_UID_REQUIRED", "device_uid required")
        res = await db.execute(select(Device).where(Device.device_uid == device_uid))
        device = res.scalar_one_or_none()
        if device is None:
            raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
        if device.owner_user_id != current_user.id:
            raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")
        user_id = current_user.id

    try:
        snapshot = await vars_core.resolve_snapshot_v3(
            db,
            device_id=device.id,
            device_uid=device.device_uid,
            user_id=user_id,
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return VariableSnapshotV3Out(**snapshot)


@router.post("/applied")
async def applied(
    data: VariableAppliedIn = Body(...),
    db: AsyncSession = Depends(get_db),
    user_creds: HTTPAuthorizationCredentials | None = Security(bearer),
    device_token: str | None = Security(device_token_header),
):
    current_user, current_device = await _resolve_actor(db, user_creds, device_token)

    device = None
    if current_device:
        device = current_device
        if data.device_uid and data.device_uid != device.device_uid:
            raise_api_error(409, "VAR_NOT_ALLOWED", "device uid mismatch")
    else:
        if not data.device_uid:
            raise_api_error(422, "VAR_DEVICE_UID_REQUIRED", "device_uid required")
        res = await db.execute(select(Device).where(Device.device_uid == data.device_uid))
        device = res.scalar_one_or_none()
        if device is None:
            raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
        if device.owner_user_id != current_user.id:
            raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")

    res = await db.execute(select(VariableSnapshot).where(VariableSnapshot.id == data.snapshot_id))
    snapshot = res.scalar_one_or_none()
    if snapshot is None:
        raise_api_error(404, "VAR_SNAPSHOT_NOT_FOUND", "snapshot not found")
    if snapshot.device_id != device.id:
        raise_api_error(409, "VAR_NOT_ALLOWED", "snapshot device mismatch")

    res = await db.execute(
        select(VariableSnapshotItem.variable_key, VariableSnapshotItem.version).where(
            VariableSnapshotItem.snapshot_id == data.snapshot_id
        )
    )
    snapshot_versions = {row[0]: row[1] for row in res.all()}

    for item in data.applied + data.failed:
        if item.key not in snapshot_versions:
            raise_api_error(409, "VAR_APPLIED_MISMATCH", "key not in snapshot")
        expected = snapshot_versions[item.key]
        if item.version is not None and expected is not None and item.version != expected:
            raise_api_error(
                409,
                "VAR_APPLIED_MISMATCH",
                "version mismatch",
                meta={"expected": expected, "got": item.version},
            )

    try:
        applied_count = 0
        failed_count = 0
        for item in data.applied:
            if await vars_core.record_applied_ack(
                db,
                snapshot_id=data.snapshot_id,
                device_id=device.id,
                key=item.key,
                version=item.version,
                status="applied",
                reason=None,
            ):
                applied_count += 1
        for item in data.failed:
            if await vars_core.record_applied_ack(
                db,
                snapshot_id=data.snapshot_id,
                device_id=device.id,
                key=item.key,
                version=item.version,
                status="failed",
                reason=item.reason,
            ):
                failed_count += 1
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {"ok": True, "applied": applied_count, "failed": failed_count}


@router.post("/ack", response_model=VariableAckOut)
async def ack_v3(
    data: VariableAckIn = Body(...),
    db: AsyncSession = Depends(get_db),
    user_creds: HTTPAuthorizationCredentials | None = Security(bearer),
    device_token: str | None = Security(device_token_header),
):
    current_user, current_device = await _resolve_actor(db, user_creds, device_token)

    device = None
    if current_device:
        device = current_device
        if data.device_uid and data.device_uid != device.device_uid:
            raise_api_error(409, "VAR_NOT_ALLOWED", "device uid mismatch")
    else:
        if not data.device_uid:
            raise_api_error(422, "VAR_DEVICE_UID_REQUIRED", "device_uid required")
        res = await db.execute(select(Device).where(Device.device_uid == data.device_uid))
        device = res.scalar_one_or_none()
        if device is None:
            raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
        if device.owner_user_id != current_user.id:
            raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")

    try:
        result = await vars_core.apply_effective_ack_v3(
            db,
            device=device,
            effective_rev=data.effective_rev,
            results=[{"key": item.key, "status": item.status, "detail": item.detail} for item in data.results],
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return VariableAckOut(**result)


@router.get("/applied", response_model=list[VariableAppliedAckOut])
async def list_applied(
    device_uid: str = Query(..., alias="deviceUid"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await db.execute(select(Device).where(Device.device_uid == device_uid))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
    if device.owner_user_id != current_user.id:
        raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")

    items = await vars_core.list_applied_acks(db, device_uid=device_uid, limit=limit)
    return [
        VariableAppliedAckOut(
            snapshot_id=item.snapshot_id,
            device_uid=device_uid,
            key=item.variable_key,
            version=item.version,
            status=item.status,
            reason=item.reason,
            created_at=item.created_at,
        )
        for item in items
    ]


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


@router.get("/effects", response_model=list[VariableEffectOut])
async def list_effects(
    device_uid: str | None = Query(default=None, alias="deviceUid"),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    device_id = None
    if device_uid:
        res = await db.execute(select(Device).where(Device.device_uid == device_uid))
        device = res.scalar_one_or_none()
        if device is None:
            raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
        if device.owner_user_id != current_user.id:
            raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")
        device_id = device.id

    stmt = select(VariableEffect)
    if device_id is not None:
        stmt = stmt.where(VariableEffect.device_id == device_id)
    if status:
        stmt = stmt.where(VariableEffect.status == status)
    stmt = stmt.order_by(VariableEffect.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    items = list(res.scalars().all())
    return [
        VariableEffectOut(
            id=item.id,
            status=item.status,
            kind=item.kind,
            scope=item.scope,
            device_uid=item.device_uid,
            trigger_audit_id=item.trigger_audit_id,
            payload=item.payload,
            error=item.error,
            attempts=item.attempts,
            next_attempt_at=item.next_attempt_at,
            locked_until=item.locked_until,
            locked_by=item.locked_by,
            correlation_id=item.correlation_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.get("/effects/{effect_id}", response_model=VariableEffectOut)
async def get_effect(
    effect_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await db.execute(select(VariableEffect).where(VariableEffect.id == effect_id))
    item = res.scalar_one_or_none()
    if item is None:
        raise_api_error(404, "VAR_EFFECT_NOT_FOUND", "effect not found")
    if item.device_id is not None:
        res = await db.execute(select(Device).where(Device.id == item.device_id))
        device = res.scalar_one_or_none()
        if device is None or device.owner_user_id != current_user.id:
            raise_api_error(404, "DEVICE_NOT_OWNED", "Device not owned")
    return VariableEffectOut(
        id=item.id,
        status=item.status,
        kind=item.kind,
        scope=item.scope,
        device_uid=item.device_uid,
        trigger_audit_id=item.trigger_audit_id,
        payload=item.payload,
        error=item.error,
        attempts=item.attempts,
        next_attempt_at=item.next_attempt_at,
        locked_until=item.locked_until,
        locked_by=item.locked_by,
        correlation_id=item.correlation_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/effects/run-once", response_model=VariableEffectRunOut)
async def run_effects(
    data: VariableEffectRunIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not _dev_tools_enabled():
        raise_api_error(403, "DEV_TOOLS_DISABLED", "dev tools disabled")
    try:
        result = await run_effects_once(
            db,
            limit=data.limit,
            locked_by=f"user:{current_user.id}",
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return VariableEffectRunOut(**result)
