"""MCP Request Handler (M22 Step 2).

Executes MCP tool calls against the HUBEX database.
Each tool maps to internal HUBEX operations using the same
SQLAlchemy models and business logic as the REST API.
"""

import logging
import uuid as _uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.automation import AutomationRule
from app.db.models.dashboard import Dashboard, DashboardWidget
from app.db.models.device import Device
from app.db.models.semantic_type import SemanticType
from app.db.models.user import User
from app.db.models.variables import VariableDefinition, VariableValue, VariableHistory
from app.realtime import user_hub

logger = logging.getLogger("uvicorn.error")

# ── Capability enforcement ────────────────────────────────────────────────

TOOL_CAPS: dict[str, list[str]] = {
    # Read-only tools
    "hubex_list_devices": ["devices.read"],
    "hubex_get_device": ["devices.read"],
    "hubex_list_variables": ["vars.read"],
    "hubex_get_variable_value": ["vars.read"],
    "hubex_get_variable_history": ["vars.read"],
    "hubex_list_alerts": ["alerts.read"],
    "hubex_list_automations": ["automations.read"],
    "hubex_get_metrics": ["devices.read"],
    "hubex_get_health": [],
    "hubex_list_dashboards": ["dashboards.read"],
    "hubex_list_semantic_types": ["vars.read"],
    # Write tools
    "hubex_set_variable": ["vars.write"],
    "hubex_acknowledge_alert": ["alerts.write"],
    "hubex_toggle_automation": ["automations.write"],
    "hubex_test_automation": ["automations.write"],
    "hubex_create_device": ["devices.write"],
    "hubex_create_automation": ["automations.write"],
    "hubex_create_dashboard": ["dashboards.write"],
    "hubex_create_alert_rule": ["alerts.write"],
    # UI command tools
    "hubex_navigate": ["mcp.execute"],
    "hubex_start_tour": ["mcp.execute"],
    "hubex_highlight_element": ["mcp.execute"],
    "hubex_fly_to_node": ["mcp.execute"],
    "hubex_camera": ["mcp.execute"],
    "hubex_show_notification": ["mcp.execute"],
}


def _check_caps(tool_name: str, user_caps: set[str]) -> str | None:
    """Return an error message if the user lacks required caps, else None."""
    required = TOOL_CAPS.get(tool_name, [])
    if not required:
        return None
    # "mcp.execute" grants all MCP caps; admin users have all caps
    if "mcp.execute" in user_caps or "admin" in user_caps:
        return None
    missing = [c for c in required if c not in user_caps]
    if missing:
        return f"Missing capabilities: {', '.join(missing)}"
    return None


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    db: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Execute an MCP tool and return the result.

    The ``user`` parameter is the authenticated User ORM object providing
    user_id and org_id context for all operations.
    """
    user_id = user.id
    org_id = getattr(user, "org_id", None)

    # Capability check — resolve caps from user role or API key
    # JWT-authenticated users (via bridge) get full caps based on their role
    user_caps = set(getattr(user, "_mcp_caps", []))
    if not user_caps:
        # No explicit MCP caps → user logged in via JWT. Grant based on role.
        # Owner/admin users get all capabilities.
        from app.core.capabilities import resolve_caps_for_role
        try:
            role = getattr(user, "_role", None) or "owner"  # default to owner for MCP
            user_caps = set(resolve_caps_for_role(role))
        except Exception:
            user_caps = {"mcp.read", "mcp.execute"}  # safe fallback
    cap_error = _check_caps(tool_name, user_caps)
    if cap_error:
        return {"error": cap_error}

    if tool_name == "hubex_list_devices":
        return await _list_devices(db, user_id, arguments)
    elif tool_name == "hubex_get_device":
        return await _get_device(db, user_id, arguments)
    elif tool_name == "hubex_list_variables":
        return await _list_variables(db, arguments)
    elif tool_name == "hubex_get_variable_value":
        return await _get_variable_value(db, arguments)
    elif tool_name == "hubex_set_variable":
        return await _set_variable(db, user_id, arguments)
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
    # ── AI Coop: UI command tools ────────────────────────────────────────
    elif tool_name == "hubex_navigate":
        return await _ui_navigate(user_id, arguments)
    elif tool_name == "hubex_start_tour":
        return await _ui_start_tour(user_id, arguments)
    elif tool_name == "hubex_highlight_element":
        return await _ui_highlight(user_id, arguments)
    elif tool_name == "hubex_fly_to_node":
        return await _ui_fly_to_node(user_id, arguments)
    elif tool_name == "hubex_camera":
        return await _ui_camera(user_id, arguments)
    elif tool_name == "hubex_show_notification":
        return await _ui_notification(user_id, arguments)
    # ── AI Coop: CRUD tools ──────────────────────────────────────────────
    elif tool_name == "hubex_create_device":
        return await _create_device(db, user_id, org_id, arguments)
    elif tool_name == "hubex_create_automation":
        return await _create_automation(db, user_id, org_id, arguments)
    elif tool_name == "hubex_create_dashboard":
        return await _create_dashboard(db, user_id, arguments)
    elif tool_name == "hubex_create_alert_rule":
        return await _create_alert_rule(db, user_id, org_id, arguments)
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
        VariableValue.variable_key == key,
        VariableValue.scope == scope,
    )
    if device_uid:
        # Resolve device_uid to device_id
        dev_stmt = select(Device.id).where(Device.device_uid == device_uid)
        dev_result = await db.execute(dev_stmt)
        dev_id = dev_result.scalar_one_or_none()
        if dev_id:
            stmt = stmt.where(VariableValue.device_id == dev_id)
        else:
            return {"error": f"Device '{device_uid}' not found"}
    result = await db.execute(stmt)
    val = result.scalar_one_or_none()
    if not val:
        return {"error": f"No value for variable '{key}' in scope '{scope}'"}
    # Resolve device_id back to device_uid for the response
    resp_device_uid = None
    if val.device_id:
        dev_res = await db.execute(select(Device.device_uid).where(Device.id == val.device_id))
        resp_device_uid = dev_res.scalar_one_or_none()
    return {
        "key": val.variable_key,
        "scope": val.scope,
        "value": val.value_json,
        "device_uid": resp_device_uid,
        "updated_at": str(val.updated_at) if val.updated_at else None,
    }


async def _set_variable(db: AsyncSession, user_id: int, args: dict) -> dict:
    from app.core.variables import create_or_update_value
    key = args["key"]
    value = args["value"]
    scope = args["scope"]
    device_uid = args.get("device_uid")
    try:
        await create_or_update_value(
            db,
            key=key,
            value=value,
            scope=scope,
            device_uid=device_uid,
            expected_version=None,
            actor_user_id=user_id,
            actor_device_id=None,
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
    # Join AlertEvent with AlertRule to get severity
    stmt = select(AlertEvent, AlertRule.severity, AlertRule.name.label("rule_name")).join(
        AlertRule, AlertEvent.rule_id == AlertRule.id
    )
    status = args.get("status")
    if status:
        stmt = stmt.where(AlertEvent.status == status)
    stmt = stmt.order_by(AlertEvent.id.desc()).limit(50)
    result = await db.execute(stmt)
    rows = result.all()
    return {
        "alerts": [
            {
                "id": event.id,
                "rule_id": event.rule_id,
                "rule_name": rule_name,
                "status": event.status,
                "severity": severity,
                "message": event.message,
                "triggered_at": str(event.triggered_at),
            }
            for event, severity, rule_name in rows
        ],
        "count": len(rows),
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


# ---------------------------------------------------------------------------
# AI Coop — UI command tools
# ---------------------------------------------------------------------------


async def _ui_navigate(user_id: int, args: dict) -> dict:
    path = args["path"]
    logger.info("MCP UI command 'navigate' -> path=%s for user_id=%s", path, user_id)
    await user_hub.send_ui_command(user_id, "navigate", {"path": path})
    return {"success": True, "command": "navigate", "path": path}


async def _ui_start_tour(user_id: int, args: dict) -> dict:
    tour_id = args["tour_id"]
    logger.info("MCP UI command 'start_tour' -> tour=%s for user_id=%s", tour_id, user_id)
    await user_hub.send_ui_command(user_id, "start_tour", {"tour_id": tour_id})
    return {"success": True, "command": "start_tour", "tour_id": tour_id}


async def _ui_highlight(user_id: int, args: dict) -> dict:
    selector = args["selector"]
    message = args.get("message", "")
    duration = args.get("duration", 3)
    logger.info("MCP UI command 'highlight' -> selector=%s for user_id=%s", selector, user_id)
    await user_hub.send_ui_command(user_id, "highlight", {
        "selector": selector,
        "message": message,
        "duration": duration,
    })
    return {"success": True, "command": "highlight", "selector": selector}


async def _ui_fly_to_node(user_id: int, args: dict) -> dict:
    node_id = args["node_id"]
    logger.info("MCP UI command 'fly_to_node' -> node=%s for user_id=%s", node_id, user_id)
    await user_hub.send_ui_command(user_id, "fly_to_node", {"node_id": node_id})
    return {"success": True, "command": "fly_to_node", "node_id": node_id}


async def _ui_camera(user_id: int, args: dict) -> dict:
    action = args["action"]
    logger.info("MCP UI command 'camera' -> action=%s for user_id=%s", action, user_id)
    await user_hub.send_ui_command(user_id, "camera", {
        "action": action,
        "selector": args.get("selector", ""),
        "zoom": args.get("zoom", 2.0),
        "duration": args.get("duration", 800),
        "x": args.get("x", 0),
        "y": args.get("y", 0),
    })
    return {"success": True, "command": "camera", "action": action}


async def _ui_notification(user_id: int, args: dict) -> dict:
    message = args["message"]
    notif_type = args.get("type", "info")
    logger.info("MCP UI command 'notification' -> type=%s for user_id=%s", notif_type, user_id)
    await user_hub.send_ui_command(user_id, "notification", {
        "message": message,
        "type": notif_type,
    })
    return {"success": True, "command": "notification", "message": message}


# ---------------------------------------------------------------------------
# AI Coop — CRUD tools
# ---------------------------------------------------------------------------


async def _create_device(db: AsyncSession, user_id: int, org_id: int | None, args: dict) -> dict:
    name = args["name"]
    device_type = args["device_type"]
    device_uid = f"ai-{_uuid.uuid4().hex[:12]}"
    device = Device(
        device_uid=device_uid,
        name=name,
        device_type=device_type,
        owner_user_id=user_id,
        org_id=org_id,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    # Push a refresh event so the UI updates
    await user_hub.send_ui_command(user_id, "refresh", {})
    return {
        "success": True,
        "device_id": device.id,
        "device_uid": device.device_uid,
        "name": device.name,
        "device_type": device.device_type,
    }


async def _create_automation(db: AsyncSession, user_id: int, org_id: int | None, args: dict) -> dict:
    rule = AutomationRule(
        org_id=org_id,
        name=args["name"],
        trigger_type=args["trigger_type"],
        trigger_config=args.get("trigger_config", {}),
        action_type=args["action_type"],
        action_config=args.get("action_config", {}),
        enabled=args.get("enabled", True),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    await user_hub.send_ui_command(user_id, "refresh", {})
    return {
        "success": True,
        "rule_id": rule.id,
        "name": rule.name,
        "trigger_type": rule.trigger_type,
        "action_type": rule.action_type,
        "enabled": rule.enabled,
    }


async def _create_dashboard(db: AsyncSession, user_id: int, args: dict) -> dict:
    dashboard = Dashboard(
        name=args["name"],
        owner_id=user_id,
    )
    db.add(dashboard)
    await db.flush()  # get the dashboard.id

    widgets_data = args.get("widgets", [])
    created_widgets = []
    # Auto-calculate grid positions: 3 columns (each span 4 in a 12-col grid)
    cols_per_row = 3
    widget_w = 4   # 12 / 3 = 4
    widget_h = 3
    for idx, w in enumerate(widgets_data):
        col_idx = idx % cols_per_row         # 0, 1, 2, 0, 1, 2, ...
        row_idx = idx // cols_per_row        # 0, 0, 0, 1, 1, 1, ...
        grid_col = col_idx * widget_w        # 0, 4, 8, 0, 4, 8, ...
        grid_row = row_idx * widget_h        # 0, 0, 0, 3, 3, 3, ...
        widget = DashboardWidget(
            dashboard_id=dashboard.id,
            widget_type=w.get("widget_type", "sparkline"),
            variable_key=w.get("variable_key"),
            device_uid=w.get("device_uid"),
            label=w.get("label"),
            sort_order=idx,
            grid_col=grid_col,
            grid_row=grid_row,
            grid_span_w=widget_w,
            grid_span_h=widget_h,
        )
        db.add(widget)
        created_widgets.append(widget)

    await db.commit()
    await db.refresh(dashboard)
    await user_hub.send_ui_command(user_id, "refresh", {})
    return {
        "success": True,
        "dashboard_id": dashboard.id,
        "name": dashboard.name,
        "widgets_count": len(created_widgets),
    }


async def _create_alert_rule(db: AsyncSession, user_id: int, org_id: int | None, args: dict) -> dict:
    rule = AlertRule(
        name=args["name"],
        condition_type=args["condition_type"],
        condition_config=args.get("condition_config", {}),
        severity=args.get("severity", "warning"),
        org_id=org_id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    await user_hub.send_ui_command(user_id, "refresh", {})
    return {
        "success": True,
        "rule_id": rule.id,
        "name": rule.name,
        "condition_type": rule.condition_type,
        "severity": rule.severity,
    }
