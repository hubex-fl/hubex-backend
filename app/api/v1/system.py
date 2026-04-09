"""System endpoints — health, demo data, edition limits."""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Edition & Soft Limits
# ---------------------------------------------------------------------------

@router.get("/system/limits")
async def get_system_limits(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return current edition and soft limit status for all tracked resources."""
    from app.db.models.user import User
    from app.db.models.device import Device
    from app.db.models.api_key import ApiKey
    from app.db.models.dashboard import Dashboard
    from app.db.models.automation import AutomationRule
    from app.db.models.custom_endpoint import CustomEndpoint

    users_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    devices_count = (await db.execute(select(func.count(Device.id)))).scalar_one()
    api_keys_count = (await db.execute(select(func.count(ApiKey.id)))).scalar_one()
    dashboards_count = (await db.execute(select(func.count(Dashboard.id)))).scalar_one()
    automations_count = (await db.execute(select(func.count(AutomationRule.id)))).scalar_one()
    custom_endpoints_count = (await db.execute(select(func.count(CustomEndpoint.id)))).scalar_one()

    def _limit_entry(current: int, max_val: int) -> dict:
        # 0 means unlimited (enterprise)
        exceeded = max_val > 0 and current > max_val
        return {"current": current, "max": max_val, "exceeded": exceeded}

    return {
        "edition": settings.edition,
        "upgrade_url": settings.upgrade_url,
        "limits": {
            "users": _limit_entry(users_count, settings.max_users),
            "devices": _limit_entry(devices_count, settings.max_devices),
            "api_keys": _limit_entry(api_keys_count, settings.max_api_keys),
            "dashboards": _limit_entry(dashboards_count, settings.max_dashboards),
            "automations": _limit_entry(automations_count, settings.max_automations),
            "custom_endpoints": _limit_entry(custom_endpoints_count, settings.max_custom_endpoints),
        },
    }


# ---------------------------------------------------------------------------
# Demo data management
# ---------------------------------------------------------------------------

@router.post("/system/demo-data")
async def load_demo_data(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Load demo data (devices, variables, automations, dashboard)."""
    from app.scripts.seed_demo_data import seed
    result = await seed(db)
    return {"status": "ok", "created": result}


@router.delete("/system/demo-data")
async def delete_demo_data(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Remove all demo data."""
    from app.scripts.seed_demo_data import remove_demo
    result = await remove_demo(db)
    return {"status": "ok", "deleted": result}


# ---------------------------------------------------------------------------
# Full system reset (admin only) — clears ALL user-created data
# ---------------------------------------------------------------------------

@router.delete("/system/reset")
async def reset_all_data(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete ALL user data for a clean slate.

    Clears: devices, variables (definitions + values + history), automations,
    alerts, dashboards (+ widgets), entities, webhooks, custom endpoints,
    custom tours, simulator configs, device profiles, components, events,
    audit log, notifications, OTA firmware, and reports.

    Protected by cap.admin capability in the auth guard.
    """
    from sqlalchemy import delete as sa_delete

    summary: dict[str, int] = {}

    # Order matters — delete children before parents to respect FK constraints.
    delete_targets: list[tuple[str, type]] = []

    # Variable history & values first, then definitions
    from app.db.models.variables import VariableHistory, VariableValue, VariableDefinition
    delete_targets += [
        ("variable_history", VariableHistory),
        ("variable_values", VariableValue),
        ("variable_definitions", VariableDefinition),
    ]

    # Dashboard widgets, then dashboards
    from app.db.models.dashboard import DashboardWidget, Dashboard
    delete_targets += [
        ("dashboard_widgets", DashboardWidget),
        ("dashboards", Dashboard),
    ]

    # Automations
    from app.db.models.automation import AutomationRule
    delete_targets.append(("automations", AutomationRule))

    # Alerts
    from app.db.models.alerts import AlertEvent
    delete_targets.append(("alerts", AlertEvent))

    # Entities
    from app.db.models.entities import Entity
    delete_targets.append(("entities", Entity))

    # Webhook deliveries first (FK to subscriptions), then subscriptions
    from app.db.models.webhooks import WebhookDelivery, WebhookSubscription
    delete_targets += [
        ("webhook_deliveries", WebhookDelivery),
        ("webhook_subscriptions", WebhookSubscription),
    ]

    # Custom endpoints
    from app.db.models.custom_endpoint import CustomEndpoint
    delete_targets.append(("custom_endpoints", CustomEndpoint))

    # Custom tours
    from app.db.models.custom_tour import CustomTour
    delete_targets.append(("custom_tours", CustomTour))

    # Simulator configs
    from app.db.models.simulator import SimulatorConfig
    delete_targets.append(("simulator_configs", SimulatorConfig))

    # Device profiles
    from app.db.models.device_profile import DeviceProfile
    delete_targets.append(("device_profiles", DeviceProfile))

    # Hardware components
    from app.db.models.component import HardwareComponent
    delete_targets.append(("components", HardwareComponent))

    # Events
    from app.db.models.events import EventV1, EventV1Checkpoint
    delete_targets += [
        ("event_checkpoints", EventV1Checkpoint),
        ("events", EventV1),
    ]

    # Notifications
    from app.db.models.notifications import Notification
    delete_targets.append(("notifications", Notification))

    # Audit log
    from app.db.models.audit import AuditV1Entry
    delete_targets.append(("audit_log", AuditV1Entry))

    # Reports
    from app.db.models.report import GeneratedReport, ReportTemplate
    delete_targets += [
        ("generated_reports", GeneratedReport),
        ("report_templates", ReportTemplate),
    ]

    # Devices (after variables/dashboards that reference them)
    from app.db.models.device import Device
    delete_targets.append(("devices", Device))

    for label, model in delete_targets:
        try:
            res = await db.execute(sa_delete(model))
            summary[label] = res.rowcount
        except Exception as e:
            logger.warning("reset: failed to delete %s: %s", label, e)
            summary[label] = -1

    await db.commit()
    return {"status": "ok", "deleted": summary}
