"""Alert Rules & Alert Events API.

Alert Rules CRUD: /api/v1/alerts/rules
Alert Events:     /api/v1/alerts  (list, get, ack, resolve)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_org import get_current_org_id
from app.core.system_events import emit_system_event
from app.db.models.alerts import AlertEvent, AlertRule

router = APIRouter(tags=["alerts"])

VALID_CONDITION_TYPES = {"device_offline", "entity_health", "effect_failure_rate", "event_lag", "variable_threshold"}
VALID_SEVERITIES = {"info", "warning", "critical"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AlertRuleOut(BaseModel):
    id: int
    name: str
    condition_type: str
    condition_config: dict
    entity_id: str | None
    severity: str
    enabled: bool
    cooldown_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertRuleCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    condition_type: str
    condition_config: dict = Field(default_factory=dict)
    entity_id: str | None = Field(default=None, max_length=64)
    severity: str = "warning"
    enabled: bool = True
    cooldown_seconds: int = Field(default=300, ge=0)

    model_config = ConfigDict(extra="ignore")


class AlertRuleUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    condition_config: dict | None = None
    entity_id: str | None = Field(default=None, max_length=64)
    severity: str | None = None
    enabled: bool | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="ignore")


class AlertEventOut(BaseModel):
    id: int
    rule_id: int
    entity_id: str | None
    device_id: int | None
    status: str
    message: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    acknowledged_by: str | None

    model_config = ConfigDict(from_attributes=True)


class AckIn(BaseModel):
    acknowledged_by: str | None = None

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_rule_or_404(rule_id: int, db: AsyncSession) -> AlertRule:
    res = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="alert rule not found")
    return rule


async def _get_event_or_404(event_id: int, db: AsyncSession) -> AlertEvent:
    res = await db.execute(select(AlertEvent).where(AlertEvent.id == event_id))
    ev = res.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="alert event not found")
    return ev


# ---------------------------------------------------------------------------
# Alert Rules — CRUD
# ---------------------------------------------------------------------------

@router.post("/alerts/rules", response_model=AlertRuleOut, status_code=201)
async def create_alert_rule(
    data: AlertRuleCreateIn,
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    if data.condition_type not in VALID_CONDITION_TYPES:
        raise HTTPException(status_code=422, detail=f"unknown condition_type '{data.condition_type}'")
    if data.severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"unknown severity '{data.severity}'")

    now = datetime.now(timezone.utc)
    rule = AlertRule(
        name=data.name,
        condition_type=data.condition_type,
        condition_config=data.condition_config,
        entity_id=data.entity_id,
        org_id=org_id,
        severity=data.severity,
        enabled=data.enabled,
        cooldown_seconds=data.cooldown_seconds,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/alerts/rules", response_model=list[AlertRuleOut])
async def list_alert_rules(
    enabled: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    stmt = select(AlertRule).order_by(AlertRule.id)
    if enabled is not None:
        stmt = stmt.where(AlertRule.enabled.is_(enabled))
    if org_id is not None:
        stmt = stmt.where(AlertRule.org_id == org_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/alerts/rules/{rule_id}", response_model=AlertRuleOut)
async def get_alert_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_rule_or_404(rule_id, db)


@router.put("/alerts/rules/{rule_id}", response_model=AlertRuleOut)
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    rule = await _get_rule_or_404(rule_id, db)

    if data.severity is not None and data.severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"unknown severity '{data.severity}'")

    if data.name is not None:
        rule.name = data.name
    if data.condition_config is not None:
        rule.condition_config = data.condition_config
    if data.entity_id is not None:
        rule.entity_id = data.entity_id
    if data.severity is not None:
        rule.severity = data.severity
    if data.enabled is not None:
        rule.enabled = data.enabled
    if data.cooldown_seconds is not None:
        rule.cooldown_seconds = data.cooldown_seconds

    rule.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/alerts/rules/{rule_id}", status_code=204)
async def delete_alert_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await _get_rule_or_404(rule_id, db)
    await db.delete(rule)
    await db.commit()


# ---------------------------------------------------------------------------
# Alert Events — list, get, ack, resolve
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=list[AlertEventOut])
async def list_alert_events(
    status: str | None = Query(default=None),
    rule_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    stmt = select(AlertEvent).order_by(AlertEvent.triggered_at.desc())
    if status is not None:
        stmt = stmt.where(AlertEvent.status == status)
    if rule_id is not None:
        stmt = stmt.where(AlertEvent.rule_id == rule_id)
    if org_id is not None:
        stmt = stmt.join(AlertRule, AlertRule.id == AlertEvent.rule_id).where(
            AlertRule.org_id == org_id
        )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/alerts/{event_id}", response_model=AlertEventOut)
async def get_alert_event(event_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_event_or_404(event_id, db)


@router.post("/alerts/{event_id}/ack", response_model=AlertEventOut)
async def acknowledge_alert_event(
    event_id: int,
    data: AckIn,
    db: AsyncSession = Depends(get_db),
):
    ev = await _get_event_or_404(event_id, db)
    if ev.status != "firing":
        raise HTTPException(status_code=409, detail=f"cannot acknowledge event with status '{ev.status}'")

    now = datetime.now(timezone.utc)
    ev.status = "acknowledged"
    ev.acknowledged_at = now
    ev.acknowledged_by = data.acknowledged_by

    res = await db.execute(select(AlertRule).where(AlertRule.id == ev.rule_id))
    rule = res.scalar_one_or_none()
    await emit_system_event(db, "alert.acknowledged", {
        "alert_event_id": ev.id,
        "rule_id": ev.rule_id,
        "rule_name": rule.name if rule else None,
        "acknowledged_by": data.acknowledged_by,
    })
    await db.commit()
    await db.refresh(ev)
    return ev


@router.post("/alerts/{event_id}/resolve", response_model=AlertEventOut)
async def resolve_alert_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    ev = await _get_event_or_404(event_id, db)
    if ev.status == "resolved":
        raise HTTPException(status_code=409, detail="event is already resolved")

    now = datetime.now(timezone.utc)
    ev.status = "resolved"
    ev.resolved_at = now

    res = await db.execute(select(AlertRule).where(AlertRule.id == ev.rule_id))
    rule = res.scalar_one_or_none()
    await emit_system_event(db, "alert.resolved", {
        "alert_event_id": ev.id,
        "rule_id": ev.rule_id,
        "rule_name": rule.name if rule else None,
    })
    await db.commit()
    await db.refresh(ev)
    return ev
