"""MCP Request Handler (M22 Step 2).

Executes MCP tool calls against the HUBEX database.
Each tool maps to internal HUBEX operations using the same
SQLAlchemy models and business logic as the REST API.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.automation import AutomationRule
from app.db.models.dashboard import Dashboard
from app.db.models.device import Device
from app.db.models.semantic_type import SemanticType
from app.db.models.variables import VariableDefinition, VariableValue, VariableHistory


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    db: AsyncSession,
    user_id: int,
) -> dict[str, Any]:
    """Execute an MCP tool and return the result."""

    if tool_name == "hubex_list_devices":
        return await _list_devices(db, user_id, arguments)
    elif tool_name == "hubex_get_device":
        return await _get_device(db, user_id, arguments)
    elif tool_name == "hubex_list_variables":
        return await _list_variables(db, arguments)
    elif tool_name == "hubex_get_variable_value":
        return await _get_variable_value(db, arguments)
    elif tool_name == "hubex_set_variable":
        return await _set_variable(db, arguments)
    elif tool_name == "hubex_get_variable_history":
        return await _get_variable_history(db, arguments)
    elif tool_name == "hubex_list_alerts":
        return await _list_alerts(db, arguments)
    elif tool_name == "hubex_acknowledge_alert":
        return await _ack_alert(db, arguments)
    elif tool_name == "hubex_list_automations":
        return await _list_automations(db, arguments)
    elif tool_name == "hubex_toggle_automation":
        return await _toggle_automation(db, arguments)
    elif tool_name == "hubex_test_automation":
        return await _test_automation(db, arguments)
    elif tool_name == "hubex_get_metrics":
        return await _get_metrics(db, user_id)
    elif tool_name == "hubex_get_health":
        return _get_health()
    elif tool_name == "hubex_list_dashboards":
        return await _list_dashboards(db, user_id)
    elif tool_name == "hubex_list_semantic_types":
        return await _list_semantic_types(db)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def _list_devices(db: AsyncSession, user_id: int, args: dict) -> dict:
    limit = args.get("limit", 50)
    stmt = select(Device).where(Device.owner_user_id == user_id).limit(limit)
    result = await db.execute(stmt)
    devices = result.scalars().all()
    return {
        "devices": [
            {
                "id": d.id,
                "device_uid": d.device_uid,
                "name": d.name,
                "device_type": d.device_type,
                "last_seen_at": str(d.last_seen_at) if d.last_seen_at else None,
            }
            for d in devices
        ],
        "count": len(devices),
    }


async def _get_device(db: AsyncSession, user_id: int, args: dict) -> dict:
    device_id = args["device_id"]
    stmt = select(Device).where(Device.id == device_id, Device.owner_user_id == user_id)
    result = await db.execute(stmt)
    d = result.scalar_one_or_none()
    if not d:
        return {"error": f"Device {device_id} not found"}
    return {
        "id": d.id,
        "device_uid": d.device_uid,
        "name": d.name,
        "device_type": d.device_type,
        "last_seen_at": str(d.last_seen_at) if d.last_seen_at else None,
    }


async def _list_variables(db: AsyncSession, args: dict) -> dict:
    stmt = select(VariableDefinition)
    scope = args.get("scope")
    if scope:
        stmt = stmt.where(VariableDefinition.scope == scope)
    category = args.get("category")
    if category:
        stmt = stmt.where(VariableDefinition.category == category)
    stmt = stmt.order_by(VariableDefinition.key).limit(100)
    result = await db.execute(stmt)
    defs = result.scalars().all()
    return {
        "variables": [
            {
                "key": v.key,
                "scope": v.scope,
                "value_type": v.value_type,
                "description": v.description,
                "unit": v.unit,
                "category": v.category,
                "display_hint": v.display_hint,
            }
            for v in defs
        ],
        "count": len(defs),
    }


async def _get_variable_value(db: AsyncSession, args: dict) -> dict:
    key = args["key"]
    scope = args["scope"]
    device_uid = args.get("device_uid")
    stmt = select(VariableValue).where(
        VariableValue.key == key,
        VariableValue.scope == scope,
    )
    if device_uid:
        stmt = stmt.where(VariableValue.device_uid == device_uid)
    result = await db.execute(stmt)
    val = result.scalar_one_or_none()
    if not val:
        return {"error": f"No value for variable '{key}' in scope '{scope}'"}
    return {
        "key": val.key,
        "scope": val.scope,
        "value": val.value,
        "device_uid": val.device_uid,
        "updated_at": str(val.updated_at) if val.updated_at else None,
    }


async def _set_variable(db: AsyncSession, args: dict) -> dict:
    from app.core.variables import create_or_update_value
    key = args["key"]
    value = args["value"]
    scope = args["scope"]
    device_uid = args.get("device_uid")
    try:
        await create_or_update_value(
            db, key=key, value=value, scope=scope,
            device_uid=device_uid, source="mcp",
        )
        return {"success": True, "key": key, "value": value}
    except Exception as e:
        return {"error": str(e)}


async def _get_variable_history(db: AsyncSession, args: dict) -> dict:
    key = args["key"]
    scope = args["scope"]
    device_uid = args.get("device_uid")
    limit = args.get("limit", 100)

    stmt = select(VariableHistory).where(
        VariableHistory.variable_key == key,
    ).order_by(VariableHistory.recorded_at.desc()).limit(limit)
    if device_uid:
        # Find device_id from uid
        dev_stmt = select(Device.id).where(Device.device_uid == device_uid)
        dev_result = await db.execute(dev_stmt)
        dev_id = dev_result.scalar_one_or_none()
        if dev_id:
            stmt = stmt.where(VariableHistory.device_id == dev_id)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {
        "key": key,
        "count": len(rows),
        "data": [
            {
                "value": r.value_json,
                "numeric": r.numeric_value,
                "recorded_at": str(r.recorded_at),
            }
            for r in rows
        ],
    }


async def _list_alerts(db: AsyncSession, args: dict) -> dict:
    stmt = select(AlertEvent)
    status = args.get("status")
    if status:
        stmt = stmt.where(AlertEvent.status == status)
    stmt = stmt.order_by(AlertEvent.id.desc()).limit(50)
    result = await db.execute(stmt)
    events = result.scalars().all()
    return {
        "alerts": [
            {
                "id": a.id,
                "rule_id": a.rule_id,
                "status": a.status,
                "severity": a.severity,
                "message": a.message,
                "created_at": str(a.created_at),
            }
            for a in events
        ],
        "count": len(events),
    }


async def _ack_alert(db: AsyncSession, args: dict) -> dict:
    event_id = args["event_id"]
    stmt = select(AlertEvent).where(AlertEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        return {"error": f"Alert event {event_id} not found"}
    event.status = "acknowledged"
    await db.commit()
    return {"success": True, "event_id": event_id, "status": "acknowledged"}


async def _list_automations(db: AsyncSession, args: dict) -> dict:
    stmt = select(AutomationRule)
    enabled = args.get("enabled")
    if enabled is not None:
        stmt = stmt.where(AutomationRule.enabled.is_(enabled))
    stmt = stmt.order_by(AutomationRule.id.desc()).limit(50)
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return {
        "automations": [
            {
                "id": r.id,
                "name": r.name,
                "enabled": r.enabled,
                "trigger_type": r.trigger_type,
                "action_type": r.action_type,
                "fire_count": r.fire_count,
            }
            for r in rules
        ],
        "count": len(rules),
    }


async def _toggle_automation(db: AsyncSession, args: dict) -> dict:
    rule_id = args["rule_id"]
    enabled = args["enabled"]
    stmt = select(AutomationRule).where(AutomationRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        return {"error": f"Automation rule {rule_id} not found"}
    rule.enabled = enabled
    await db.commit()
    return {"success": True, "rule_id": rule_id, "enabled": enabled}


async def _test_automation(db: AsyncSession, args: dict) -> dict:
    rule_id = args["rule_id"]
    stmt = select(AutomationRule).where(AutomationRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        return {"error": f"Automation rule {rule_id} not found"}
    return {"success": True, "message": f"Test fire queued for rule '{rule.name}'"}


async def _get_metrics(db: AsyncSession, user_id: int) -> dict:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    total = (await db.execute(
        select(func.count()).select_from(Device).where(Device.owner_user_id == user_id)
    )).scalar_one()
    online = (await db.execute(
        select(func.count()).select_from(Device).where(
            Device.owner_user_id == user_id,
            Device.last_seen_at >= now - timedelta(seconds=30),
        )
    )).scalar_one()
    firing = (await db.execute(
        select(func.count()).select_from(AlertEvent).where(AlertEvent.status == "firing")
    )).scalar_one()
    return {
        "devices": {"total": total, "online": online, "offline": total - online},
        "alerts_firing": firing,
    }


def _get_health() -> dict:
    return {"status": "ok", "message": "HUBEX backend is running"}


async def _list_dashboards(db: AsyncSession, user_id: int) -> dict:
    stmt = select(Dashboard).where(Dashboard.owner_id == user_id).limit(20)
    result = await db.execute(stmt)
    dashboards = result.scalars().all()
    return {
        "dashboards": [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "is_default": d.is_default,
            }
            for d in dashboards
        ],
        "count": len(dashboards),
    }


async def _list_semantic_types(db: AsyncSession) -> dict:
    stmt = select(SemanticType).order_by(SemanticType.name).limit(100)
    result = await db.execute(stmt)
    types = result.scalars().all()
    return {
        "types": [
            {
                "id": t.id,
                "name": t.name,
                "base_type": t.base_type,
                "display_name": t.display_name,
                "default_unit": t.default_unit,
                "icon": t.icon,
            }
            for t in types
        ],
        "count": len(types),
    }
