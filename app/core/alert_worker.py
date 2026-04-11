"""Alert evaluation background worker.

Each enabled AlertRule is evaluated every cycle (30 s). When a condition fires
a new AlertEvent (status=firing) is created (subject to cooldown). When the
condition clears, open events are auto-resolved.

Supported condition_types and their condition_config keys
---------------------------------------------------------
device_offline:
    threshold_seconds (int, default 120)
    device_ids        (list[int] | None) — scope to specific devices; if None,
                      fires when *any* claimed device is offline

entity_health:
    entity_id         (str)
    min_online        (int, default 1) — alert if online count < min_online

effect_failure_rate:
    kind              (str) — EffectV1.kind to filter
    failure_rate_threshold (float, default 0.5)
    window_seconds    (int, default 300)

event_lag:
    stream            (str)
    max_lag_seconds   (int, default 300) — alert if no event in stream for this long
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_events import emit_system_event
from app.core.notification_service import create_notification_all_users
from app.core.notifications import notify_alert_fired, notify_device_offline
from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.device import Device
from app.db.models.effects import EffectV1
from app.db.models.entities import Entity, EntityDeviceBinding
from app.db.models.events import EventV1
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

EVAL_INTERVAL = 30  # seconds between evaluation cycles
ONLINE_WINDOW_SECONDS = 30
STALE_WINDOW_SECONDS = 120


# ---------------------------------------------------------------------------
# Condition evaluators — return (should_fire: bool, message: str)
# ---------------------------------------------------------------------------

async def _eval_device_offline(config: dict, db: AsyncSession, now: datetime) -> tuple[bool, str]:
    threshold = config.get("threshold_seconds", STALE_WINDOW_SECONDS)
    device_ids: list[int] | None = config.get("device_ids")
    cutoff = now - timedelta(seconds=threshold)

    stmt = select(func.count()).select_from(Device).where(
        Device.is_claimed.is_(True),
        (Device.last_seen_at.is_(None)) | (Device.last_seen_at < cutoff),
    )
    if device_ids:
        stmt = stmt.where(Device.id.in_(device_ids))

    res = await db.execute(stmt)
    count = res.scalar_one()
    if count > 0:
        return True, f"{count} device(s) offline for more than {threshold}s"
    return False, ""


async def _eval_entity_health(config: dict, db: AsyncSession, now: datetime) -> tuple[bool, str]:
    entity_id: str | None = config.get("entity_id")
    min_online: int = config.get("min_online", 1)

    if not entity_id:
        return False, ""

    cutoff_online = now - timedelta(seconds=ONLINE_WINDOW_SECONDS)
    res = await db.execute(
        select(func.count())
        .select_from(Device)
        .join(EntityDeviceBinding, EntityDeviceBinding.device_id == Device.id)
        .where(
            EntityDeviceBinding.entity_id == entity_id,
            EntityDeviceBinding.enabled.is_(True),
            Device.last_seen_at.is_not(None),
            Device.last_seen_at >= cutoff_online,
        )
    )
    online_count = res.scalar_one()
    if online_count < min_online:
        return True, f"entity {entity_id} has {online_count} online device(s), min required {min_online}"
    return False, ""


async def _eval_effect_failure_rate(config: dict, db: AsyncSession, now: datetime) -> tuple[bool, str]:
    kind: str | None = config.get("kind")
    threshold: float = config.get("failure_rate_threshold", 0.5)
    window: int = config.get("window_seconds", 300)

    if not kind:
        return False, ""

    cutoff = now - timedelta(seconds=window)
    stmt_total = select(func.count()).select_from(EffectV1).where(
        EffectV1.kind == kind,
        EffectV1.created_at >= cutoff,
    )
    stmt_failed = select(func.count()).select_from(EffectV1).where(
        EffectV1.kind == kind,
        EffectV1.status == "failed",
        EffectV1.created_at >= cutoff,
    )
    total = (await db.execute(stmt_total)).scalar_one()
    failed = (await db.execute(stmt_failed)).scalar_one()

    if total == 0:
        return False, ""
    rate = failed / total
    if rate >= threshold:
        return True, f"effect '{kind}' failure rate {rate:.0%} >= threshold {threshold:.0%} over {window}s"
    return False, ""


async def _eval_event_lag(config: dict, db: AsyncSession, now: datetime) -> tuple[bool, str]:
    stream: str | None = config.get("stream")
    max_lag: int = config.get("max_lag_seconds", 300)

    if not stream:
        return False, ""

    res = await db.execute(
        select(func.max(EventV1.ts)).where(EventV1.stream == stream)
    )
    last_ts: datetime | None = res.scalar_one_or_none()
    if last_ts is None:
        return True, f"stream '{stream}' has no events at all"
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    lag = (now - last_ts).total_seconds()
    if lag > max_lag:
        return True, f"stream '{stream}' last event {lag:.0f}s ago (max {max_lag}s)"
    return False, ""


async def _eval_variable_threshold(config: dict, db: AsyncSession, now: datetime) -> tuple[bool, str]:
    """
    config keys:
      variable_key (str, required)
      threshold_operator (str): "gt", "gte", "lt", "lte", "eq", "ne"
      threshold_value (float, required)
      device_uid (str | None) - if None, checks global scope
    """
    key: str | None = config.get("variable_key")
    operator: str = config.get("threshold_operator", "gt")
    threshold: float | None = config.get("threshold_value")
    device_uid: str | None = config.get("device_uid")

    if not key or threshold is None:
        return False, ""

    from app.db.models.variables import VariableValue

    # Build query — VariableValue uses device_id (int FK), not device_uid directly
    stmt = select(VariableValue).where(VariableValue.variable_key == key)
    if device_uid:
        # Resolve device_uid → device_id via a subquery
        sub = select(Device.id).where(Device.device_uid == device_uid).scalar_subquery()
        stmt = stmt.where(VariableValue.device_id == sub)
    else:
        stmt = stmt.where(VariableValue.scope == "global")
    res = await db.execute(stmt)
    val_obj = res.scalar_one_or_none()
    if val_obj is None:
        return False, ""

    raw = val_obj.value_json
    try:
        numeric = float(raw)
    except (TypeError, ValueError):
        return False, ""

    ops = {
        "gt": numeric > threshold,
        "gte": numeric >= threshold,
        "lt": numeric < threshold,
        "lte": numeric <= threshold,
        "eq": numeric == threshold,
        "ne": numeric != threshold,
    }
    fired = ops.get(operator, False)
    if fired:
        # Sprint 3.6 bugfix: use math symbols instead of english op words.
        # Old message "variable 'temperature' value 20.3 gt 20" is locale-
        # agnostic-ish, but "gt/gte/lt/lte/eq/ne" are english codes. The
        # symbols ">", "<", "=" etc. are universal and render identically
        # in every locale. Frontend Alerts + Dashboard widgets display
        # this string directly, so this makes them readable without any
        # frontend translation pass.
        symbols = {"gt": ">", "gte": "\u2265", "lt": "<", "lte": "\u2264", "eq": "=", "ne": "\u2260"}
        sym = symbols.get(operator, operator)
        return True, f"{key} = {numeric} {sym} {threshold}"
    return False, ""


_EVALUATORS = {
    "device_offline": _eval_device_offline,
    "entity_health": _eval_entity_health,
    "effect_failure_rate": _eval_effect_failure_rate,
    "event_lag": _eval_event_lag,
    "variable_threshold": _eval_variable_threshold,
}


# ---------------------------------------------------------------------------
# Core evaluation logic (testable — accepts a db session and now)
# ---------------------------------------------------------------------------

async def run_alert_cycle(db: AsyncSession, now: datetime) -> None:
    """Evaluate all enabled alert rules and update alert events accordingly."""
    res = await db.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
    rules: list[AlertRule] = list(res.scalars().all())

    for rule in rules:
        evaluator = _EVALUATORS.get(rule.condition_type)
        if evaluator is None:
            logger.warning("alert_worker: unknown condition_type=%s rule_id=%d", rule.condition_type, rule.id)
            continue

        try:
            should_fire, message = await evaluator(rule.condition_config or {}, db, now)
        except Exception:
            logger.exception("alert_worker: evaluator error rule_id=%d", rule.id)
            continue

        # Find any open (firing/acknowledged) event for this rule
        res_open = await db.execute(
            select(AlertEvent).where(
                AlertEvent.rule_id == rule.id,
                AlertEvent.status.in_(["firing", "acknowledged"]),
            )
        )
        open_events: list[AlertEvent] = list(res_open.scalars().all())

        if should_fire:
            if open_events:
                # Already firing — cooldown / no-op
                continue

            # Check cooldown: was there a recent resolved/fired event?
            cutoff = now - timedelta(seconds=rule.cooldown_seconds)
            res_recent = await db.execute(
                select(AlertEvent).where(
                    AlertEvent.rule_id == rule.id,
                    AlertEvent.triggered_at >= cutoff,
                ).order_by(AlertEvent.triggered_at.desc()).limit(1)
            )
            recent = res_recent.scalar_one_or_none()
            if recent is not None:
                continue  # within cooldown

            # Fire!
            event = AlertEvent(
                rule_id=rule.id,
                entity_id=rule.entity_id,
                status="firing",
                message=message,
                triggered_at=now,
            )
            db.add(event)
            await db.flush()
            await emit_system_event(db, "alert.fired", {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "severity": rule.severity,
                "message": message,
                "alert_event_id": event.id,
            })
            # Push notification to all users
            try:
                await create_notification_all_users(
                    db,
                    type="alert_fired",
                    title=f"Alert: {rule.name}",
                    message=message,
                    severity=rule.severity if rule.severity in ("info", "warning", "error", "critical") else "warning",
                    entity_ref=f"alert_rule:{rule.id}",
                )
            except Exception:
                logger.exception("alert_worker: failed to create notification rule_id=%d", rule.id)

            # Send email notification (checks per-user preferences)
            try:
                variable_key = (rule.condition_config or {}).get("variable_key") if rule.condition_type == "variable_threshold" else None
                device_name = None
                if rule.condition_type == "device_offline":
                    device_ids = (rule.condition_config or {}).get("device_ids")
                    if device_ids and len(device_ids) == 1:
                        dev_res = await db.execute(select(Device).where(Device.id == device_ids[0]))
                        dev = dev_res.scalar_one_or_none()
                        if dev:
                            device_name = dev.name or dev.uid

                await notify_alert_fired(
                    db,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=message,
                    rule_id=rule.id,
                    alert_event_id=event.id,
                    org_id=rule.org_id,
                    variable_key=variable_key,
                    device_name=device_name,
                )
            except Exception:
                logger.exception("alert_worker: failed to send email notification rule_id=%d", rule.id)
        else:
            # Condition cleared — auto-resolve open events
            for ev in open_events:
                ev.status = "resolved"
                ev.resolved_at = now
                await emit_system_event(db, "alert.resolved", {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "alert_event_id": ev.id,
                })

    await db.commit()


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------

async def alert_worker_loop() -> None:
    """Background loop: evaluates alert rules every EVAL_INTERVAL seconds."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_alert_cycle(db, datetime.now(timezone.utc))
        except Exception:
            logger.exception("alert_worker: unhandled error in evaluation cycle")
        await asyncio.sleep(EVAL_INTERVAL)
