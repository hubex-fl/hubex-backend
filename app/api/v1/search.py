"""Global search endpoint (M25/UX Overhaul).

GET /api/v1/search?q=<query>
ILIKE search across devices, variables, automations, alert rules.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.device import Device
from app.db.models.automation import AutomationRule
from app.db.models.alerts import AlertRule
from app.db.models.user import User
from app.db.models.variables import VariableDefinition

router = APIRouter(tags=["search"])

MAX_PER_CATEGORY = 5


@router.get("/search")
async def global_search(
    q: str = Query(min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Search across all entity types."""
    pattern = f"%{q}%"
    results: dict[str, list[dict]] = {}

    # Devices
    stmt = (
        select(Device)
        .where(
            Device.owner_user_id == current_user.id,
            or_(
                Device.device_uid.ilike(pattern),
                Device.name.ilike(pattern),
            ),
        )
        .limit(MAX_PER_CATEGORY)
    )
    devices = (await db.execute(stmt)).scalars().all()
    if devices:
        results["devices"] = [
            {"id": d.id, "label": d.name or d.device_uid, "uid": d.device_uid, "type": d.device_type}
            for d in devices
        ]

    # Variables
    stmt = (
        select(VariableDefinition)
        .where(VariableDefinition.key.ilike(pattern))
        .limit(MAX_PER_CATEGORY)
    )
    variables = (await db.execute(stmt)).scalars().all()
    if variables:
        results["variables"] = [
            {"key": v.key, "label": v.key, "scope": v.scope, "type": v.value_type}
            for v in variables
        ]

    # Automations
    stmt = (
        select(AutomationRule)
        .where(AutomationRule.name.ilike(pattern))
        .limit(MAX_PER_CATEGORY)
    )
    automations = (await db.execute(stmt)).scalars().all()
    if automations:
        results["automations"] = [
            {"id": r.id, "label": r.name, "enabled": r.enabled}
            for r in automations
        ]

    # Alert Rules
    stmt = (
        select(AlertRule)
        .where(AlertRule.name.ilike(pattern))
        .limit(MAX_PER_CATEGORY)
    )
    alert_rules = (await db.execute(stmt)).scalars().all()
    if alert_rules:
        results["alerts"] = [
            {"id": r.id, "label": r.name, "severity": r.severity}
            for r in alert_rules
        ]

    return results
