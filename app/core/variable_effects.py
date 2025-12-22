from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.error_utils import raise_api_error
from app.db.models.device import Device
from app.db.models.device_runtime import DeviceRuntimeSetting
from app.db.models.variables import VariableAudit, VariableDefinition, VariableEffect


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _backoff_seconds(attempts: int) -> int:
    return min(300, 2 ** min(attempts, 6))


def derive_effects_from_change(
    definition: VariableDefinition,
    *,
    device: Device | None,
    old_value: Any | None,
    new_value: Any | None,
    audit: VariableAudit,
) -> list[dict[str, Any]]:
    if definition.scope != "device" or device is None:
        return []

    effects: list[dict[str, Any]] = []
    if definition.key == "device.telemetry_interval_ms":
        if new_value is not None:
            effects.append(
                {
                    "kind": "telemetry.reschedule",
                    "scope": "device",
                    "device_uid": device.device_uid,
                    "payload": {"interval_ms": int(new_value)},
                }
            )
    if definition.key == "device.label":
        effects.append(
            {
                "kind": "device.label.sync",
                "scope": "device",
                "device_uid": device.device_uid,
                "payload": {"label": "" if new_value is None else str(new_value)},
            }
        )
    return effects


async def enqueue_effects(
    db: AsyncSession,
    *,
    effects: list[dict[str, Any]],
    audit: VariableAudit,
    device: Device | None,
) -> list[VariableEffect]:
    if not effects:
        return []
    now = _now_utc()
    created: list[VariableEffect] = []
    for spec in effects:
        effect = VariableEffect(
            id=str(uuid4()),
            status="pending",
            kind=spec["kind"],
            scope=spec["scope"],
            device_id=device.id if device else None,
            device_uid=spec.get("device_uid"),
            trigger_audit_id=audit.id,
            payload=spec.get("payload"),
            attempts=0,
            next_attempt_at=now,
            correlation_id=f"audit:{audit.id}",
        )
        db.add(effect)
        created.append(effect)
    await db.flush()
    return created


async def _apply_telemetry_reschedule(
    db: AsyncSession,
    *,
    device_id: int,
    payload: dict[str, Any] | None,
) -> None:
    interval_ms = None if payload is None else payload.get("interval_ms")
    if interval_ms is None:
        raise_api_error(422, "EFFECT_INVALID_PAYLOAD", "interval_ms missing")
    res = await db.execute(
        select(DeviceRuntimeSetting).where(DeviceRuntimeSetting.device_id == device_id)
    )
    setting = res.scalar_one_or_none()
    if setting is None:
        setting = DeviceRuntimeSetting(device_id=device_id, telemetry_interval_ms=int(interval_ms))
        db.add(setting)
    else:
        setting.telemetry_interval_ms = int(interval_ms)


async def _apply_label_sync(
    db: AsyncSession,
    *,
    device_id: int,
    payload: dict[str, Any] | None,
) -> None:
    label = "" if payload is None else (payload.get("label") or "")
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_NOT_FOUND", "device not found")
    device.name = str(label)


async def run_effects_once(
    db: AsyncSession,
    *,
    limit: int,
    locked_by: str,
) -> dict[str, int]:
    now = _now_utc()
    res = await db.execute(
        select(VariableEffect)
        .where(
            VariableEffect.status.in_(["pending", "failed"]),
            (VariableEffect.next_attempt_at.is_(None) | (VariableEffect.next_attempt_at <= now)),
            (VariableEffect.locked_until.is_(None) | (VariableEffect.locked_until <= now)),
        )
        .order_by(VariableEffect.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(limit)
    )
    effects = list(res.scalars().all())
    for effect in effects:
        effect.status = "in_flight"
        effect.locked_by = locked_by
        effect.locked_until = now + timedelta(seconds=30)
        effect.attempts = (effect.attempts or 0) + 1
    await db.flush()

    processed = 0
    done = 0
    failed = 0
    for effect in effects:
        processed += 1
        try:
            if effect.kind == "telemetry.reschedule":
                await _apply_telemetry_reschedule(
                    db, device_id=effect.device_id, payload=effect.payload
                )
            elif effect.kind == "device.label.sync":
                await _apply_label_sync(
                    db, device_id=effect.device_id, payload=effect.payload
                )
            else:
                raise_api_error(422, "EFFECT_UNKNOWN_KIND", "unknown effect kind")
            effect.status = "done"
            effect.error = None
            effect.locked_until = None
            done += 1
        except Exception as exc:
            effect.status = "failed"
            effect.error = {"message": str(exc)}
            effect.locked_until = None
            backoff = _backoff_seconds(effect.attempts or 1)
            effect.next_attempt_at = now + timedelta(seconds=backoff)
            failed += 1
            if effect.attempts and effect.attempts >= 5:
                effect.status = "dead"
    await db.flush()
    return {"processed": processed, "done": done, "failed": failed}
