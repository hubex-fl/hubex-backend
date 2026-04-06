"""Automation Engine — background loop that evaluates AutomationRule entries.

Polling pattern mirrors alert_worker.py. Every 5 seconds, we pull new system
events from events_v1 (stream="system") and evaluate matching rules.

Trigger types:
  variable_threshold  — fires when config: {variable_key, operator, value}
  variable_geofence   — fires when GPS variable exits/enters zone
  device_offline      — fires on device.offline event
  telemetry_received  — fires on telemetry.received event

Action types:
  set_variable        — update a variable value
  call_webhook        — HTTP call via httpx (async, fire-and-forget)
  create_alert_event  — write an AlertEvent row
  emit_system_event   — write a system event
"""
from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.models.automation import AutomationFireLog, AutomationRule
from app.db.models.events import EventV1
from app.core.system_events import emit_system_event

logger = logging.getLogger("uvicorn.error")

ENGINE_INTERVAL = 5  # seconds between event-poll cycles


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in metres between two WGS-84 coordinates."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_in_polygon(lat: float, lng: float, polygon: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon. polygon = [[lat, lng], ...]."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][1], polygon[i][0]  # x=lng, y=lat
        xj, yj = polygon[j][1], polygon[j][0]
        if ((yi > lng) != (yj > lng)) and (lat < (xj - xi) * (lng - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------------
# Trigger evaluators — return True if rule should fire
# ---------------------------------------------------------------------------

async def _check_variable_threshold(rule: AutomationRule, event_payload: dict[str, Any]) -> bool:
    cfg = rule.trigger_config
    key = cfg.get("variable_key")
    operator = cfg.get("operator", "gt")
    threshold = cfg.get("value")
    device_uid = cfg.get("device_uid")

    if not key or threshold is None:
        return False

    # Only process events for the relevant variable
    if event_payload.get("variable_key") != key:
        return False
    if device_uid and event_payload.get("device_uid") != device_uid:
        return False

    raw = event_payload.get("value")
    try:
        numeric = float(raw)
    except (TypeError, ValueError):
        return False

    threshold_f = float(threshold)
    ops: dict[str, bool] = {
        "gt": numeric > threshold_f,
        "gte": numeric >= threshold_f,
        "lt": numeric < threshold_f,
        "lte": numeric <= threshold_f,
        "eq": numeric == threshold_f,
        "ne": numeric != threshold_f,
    }
    return ops.get(operator, False)


async def _check_variable_geofence(rule: AutomationRule, event_payload: dict[str, Any]) -> bool:
    cfg = rule.trigger_config
    key = cfg.get("variable_key")
    device_uid = cfg.get("device_uid")
    geofence_type = cfg.get("geofence_type", "circle")
    exit_or_enter = cfg.get("exit_or_enter", "exit")

    if not key:
        return False
    if event_payload.get("variable_key") != key:
        return False
    if device_uid and event_payload.get("device_uid") != device_uid:
        return False

    raw = event_payload.get("value")
    if not isinstance(raw, dict):
        return False

    try:
        lat = float(raw.get("lat", raw.get("latitude", 0)))
        lng = float(raw.get("lng", raw.get("longitude", 0)))
    except (TypeError, ValueError):
        return False

    if geofence_type == "circle":
        center = cfg.get("center", {})
        try:
            clat = float(center.get("lat", 0))
            clng = float(center.get("lng", 0))
            radius = float(cfg.get("radius_m", 500))
        except (TypeError, ValueError):
            return False
        dist = _haversine_distance(lat, lng, clat, clng)
        inside = dist <= radius
    elif geofence_type == "polygon":
        polygon = cfg.get("polygon", [])
        if len(polygon) < 3:
            return False
        inside = _point_in_polygon(lat, lng, polygon)
    else:
        return False

    if exit_or_enter == "enter":
        return inside
    else:  # exit
        return not inside


def _check_device_offline(rule: AutomationRule, event_payload: dict[str, Any]) -> bool:
    cfg = rule.trigger_config
    device_uid = cfg.get("device_uid")
    if device_uid:
        return event_payload.get("device_uid") == device_uid
    return True  # any device


def _check_telemetry_received(rule: AutomationRule, event_payload: dict[str, Any]) -> bool:
    cfg = rule.trigger_config
    device_uid = cfg.get("device_uid")
    event_type = cfg.get("event_type")
    if device_uid and event_payload.get("device_uid") != device_uid:
        return False
    if event_type and event_payload.get("event_type") != event_type:
        return False
    return True


# ---------------------------------------------------------------------------
# Action executors
# ---------------------------------------------------------------------------

async def execute_action(db: AsyncSession, rule: AutomationRule, context: dict[str, Any]) -> None:
    """Execute the configured action for a rule. Called by engine + test endpoint."""
    action_type = rule.action_type
    cfg = rule.action_config

    if action_type == "set_variable":
        await _action_set_variable(db, cfg, context)
    elif action_type == "call_webhook":
        await _action_call_webhook(cfg, context)
    elif action_type == "create_alert_event":
        await _action_create_alert(db, rule, cfg, context)
    elif action_type == "emit_system_event":
        await _action_emit_system_event(db, cfg, context)
    elif action_type == "send_notification":
        await _action_send_notification(db, rule, cfg, context)
    elif action_type == "log_to_audit":
        await _action_log_to_audit(db, rule, cfg, context)
    else:
        logger.warning("automation_engine: unknown action_type=%s rule_id=%d", action_type, rule.id)


async def _action_set_variable(db: AsyncSession, cfg: dict[str, Any], context: dict[str, Any]) -> None:
    from app.core.variables import create_or_update_value_v2

    key = cfg.get("variable_key")
    value = cfg.get("value")
    scope = cfg.get("scope", "global")
    device_uid = cfg.get("device_uid")

    if not key:
        raise ValueError("set_variable action requires variable_key")

    await create_or_update_value_v2(
        db,
        key=key,
        scope=scope,
        device_uid=device_uid,
        value=value,
        expected_version=None,
        actor_user_id=None,
        actor_device_id=None,
        force=True,
        dev_tools=True,
    )


async def _action_call_webhook(cfg: dict[str, Any], context: dict[str, Any]) -> None:
    import httpx

    url = cfg.get("url")
    method = cfg.get("method", "POST").upper()
    headers = cfg.get("headers") or {}
    payload = cfg.get("payload_template") or {}

    if not url:
        raise ValueError("call_webhook action requires url")

    async def _fire() -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.request(method, url, headers=headers, json={**payload, **context})
        except Exception as exc:
            logger.warning("automation_engine: webhook call failed url=%s err=%s", url, exc)

    asyncio.create_task(_fire())


async def _action_create_alert(
    db: AsyncSession, rule: AutomationRule, cfg: dict[str, Any], context: dict[str, Any]
) -> None:
    from app.db.models.alerts import AlertEvent, AlertRule
    from sqlalchemy import select

    severity = cfg.get("severity", "warning")
    message_tpl = cfg.get("message", f"Automation rule '{rule.name}' fired")

    # Simple template substitution with context values
    try:
        message = message_tpl.format(**context)
    except (KeyError, ValueError):
        message = message_tpl

    # Find or create a synthetic alert rule
    stmt = select(AlertRule).where(
        AlertRule.name == f"__auto__{rule.id}",
        AlertRule.org_id == rule.org_id,
    )
    res = await db.execute(stmt)
    alert_rule = res.scalar_one_or_none()
    if alert_rule is None:
        alert_rule = AlertRule(
            name=f"__auto__{rule.id}",
            condition_type="device_offline",
            condition_config={},
            org_id=rule.org_id,
            severity=severity,
            enabled=True,
            cooldown_seconds=0,
        )
        db.add(alert_rule)
        await db.flush()

    event = AlertEvent(
        rule_id=alert_rule.id,
        status="firing",
        message=message,
        triggered_at=datetime.now(timezone.utc),
    )
    db.add(event)


async def _action_emit_system_event(
    db: AsyncSession, cfg: dict[str, Any], context: dict[str, Any]
) -> None:
    event_type = cfg.get("event_type", "automation.fired")
    payload_extra = cfg.get("payload_extra") or {}
    await emit_system_event(db, event_type, {**payload_extra, **context})


async def _action_send_notification(
    db: AsyncSession, rule: AutomationRule, cfg: dict[str, Any], context: dict[str, Any]
) -> None:
    """Create a notification for the device owner."""
    from app.db.models.notifications import Notification
    title = cfg.get("title", f"Automation: {rule.name}")
    message = cfg.get("message", "Automation rule fired")
    try:
        message = message.format(**context)
    except (KeyError, IndexError):
        pass
    severity = cfg.get("severity", "info")
    notif = Notification(
        user_id=rule.org_id,  # Will need proper user resolution
        type="automation",
        severity=severity,
        title=title,
        message=message,
        entity_ref=f"automation:{rule.id}",
    )
    db.add(notif)


async def _action_log_to_audit(
    db: AsyncSession, rule: AutomationRule, cfg: dict[str, Any], context: dict[str, Any]
) -> None:
    """Write an audit log entry."""
    from app.db.models.audit import AuditEntry
    action = cfg.get("action", "automation.action")
    resource = cfg.get("resource", f"rule:{rule.id}")
    db.add(AuditEntry(
        actor_type="automation",
        actor_id=str(rule.id),
        action=action,
        resource=resource,
        metadata_json=context,
    ))


# ---------------------------------------------------------------------------
# Main evaluation cycle
# ---------------------------------------------------------------------------

async def _process_new_events(db: AsyncSession, last_event_id: int) -> int:
    """Fetch events newer than last_event_id and evaluate automation rules. Return new max id."""
    stmt = (
        select(EventV1)
        .where(
            EventV1.stream == "system",
            EventV1.id > last_event_id,
        )
        .order_by(EventV1.id.asc())
        .limit(200)
    )
    result = await db.execute(stmt)
    events: list[EventV1] = list(result.scalars().all())

    if not events:
        return last_event_id

    new_max_id = last_event_id

    for event in events:
        new_max_id = max(new_max_id, event.id)
        event_type: str = event.type or ""
        payload: dict[str, Any] = event.payload or {}

        # Map event type → trigger types to evaluate
        if event_type.startswith("variable."):
            trigger_types = ["variable_threshold", "variable_geofence"]
        elif event_type == "device.offline":
            trigger_types = ["device_offline"]
        elif event_type.startswith("telemetry."):
            trigger_types = ["telemetry_received"]
        else:
            continue

        # Load matching enabled rules
        stmt_rules = select(AutomationRule).where(
            AutomationRule.enabled.is_(True),
            AutomationRule.trigger_type.in_(trigger_types),
        )
        rules_result = await db.execute(stmt_rules)
        rules: list[AutomationRule] = list(rules_result.scalars().all())

        now = datetime.now(timezone.utc)

        for rule in rules:
            try:
                # Evaluate trigger condition
                if rule.trigger_type == "variable_threshold":
                    fired = await _check_variable_threshold(rule, payload)
                elif rule.trigger_type == "variable_geofence":
                    fired = await _check_variable_geofence(rule, payload)
                elif rule.trigger_type == "device_offline":
                    fired = _check_device_offline(rule, payload)
                elif rule.trigger_type == "telemetry_received":
                    fired = _check_telemetry_received(rule, payload)
                elif rule.trigger_type == "variable_change":
                    # Fires on any variable change event
                    fired = event_type.startswith("variable.") if event_type else False
                    if fired:
                        cfg_key = rule.trigger_config.get("variable_key")
                        if cfg_key and payload.get("variable_key") != cfg_key:
                            fired = False
                elif rule.trigger_type == "device_online":
                    fired = event_type == "device.online" if event_type else False
                    cfg_uid = rule.trigger_config.get("device_uid")
                    if fired and cfg_uid and payload.get("device_uid") != cfg_uid:
                        fired = False
                elif rule.trigger_type == "schedule":
                    # Schedule triggers are handled externally (cron), not by event matching
                    fired = False
                else:
                    fired = False

                if not fired:
                    continue

                # Cooldown check
                if rule.last_fired_at is not None:
                    last = rule.last_fired_at
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    if (now - last).total_seconds() < rule.cooldown_seconds:
                        continue

                # Execute action
                success = True
                error_msg: str | None = None
                try:
                    await execute_action(db, rule, context={"event_type": event_type, **payload})
                except Exception as exc:
                    success = False
                    error_msg = str(exc)
                    logger.error("automation_engine: action error rule_id=%d: %s", rule.id, exc)

                # Update rule stats
                rule.last_fired_at = now
                rule.fire_count = (rule.fire_count or 0) + 1

                # Write log entry
                log_entry = AutomationFireLog(
                    rule_id=rule.id,
                    fired_at=now,
                    success=success,
                    error_message=error_msg,
                    context_json={"event_type": event_type, **{k: v for k, v in payload.items() if isinstance(v, (str, int, float, bool, type(None)))}},
                )
                db.add(log_entry)

            except Exception as exc:
                logger.exception("automation_engine: rule evaluation error rule_id=%d: %s", rule.id, exc)

    await db.commit()
    return new_max_id


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------

async def automation_engine_loop() -> None:
    """Background loop: process system events for automation rules every ENGINE_INTERVAL seconds."""
    last_event_id = 0

    # Initialise last_event_id to current max so we don't replay old events on startup
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import func as sqlfunc
            res = await db.execute(
                select(sqlfunc.max(EventV1.id)).where(EventV1.stream == "system")
            )
            current_max = res.scalar_one_or_none()
            if current_max is not None:
                last_event_id = current_max
    except Exception:
        pass

    while True:
        try:
            async with AsyncSessionLocal() as db:
                last_event_id = await _process_new_events(db, last_event_id)
        except Exception:
            logger.exception("automation_engine: unhandled error in evaluation cycle")
        await asyncio.sleep(ENGINE_INTERVAL)
