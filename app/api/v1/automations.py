"""Automation Rules API.

CRUD + test-fire + history endpoints for AutomationRule.

Routes:
  GET    /api/v1/automations          — list rules for org
  POST   /api/v1/automations          — create rule
  GET    /api/v1/automations/{id}     — get one rule
  PATCH  /api/v1/automations/{id}     — update rule
  DELETE /api/v1/automations/{id}     — delete rule
  POST   /api/v1/automations/{id}/test    — fire action once (ignores cooldown)
  GET    /api/v1/automations/{id}/history — last 50 fire log entries
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_org import get_current_org_id
from app.db.models.automation import AutomationFireLog, AutomationRule
from app.schemas.automation import (
    VALID_ACTION_TYPES,
    VALID_TRIGGER_TYPES,
    AutomationFireLogOut,
    AutomationRuleCreate,
    AutomationRuleOut,
    AutomationRulePatch,
)

router = APIRouter(tags=["automations"])


def _validate_types(trigger_type: str, action_type: str) -> None:
    if trigger_type not in VALID_TRIGGER_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid trigger_type '{trigger_type}'. Valid: {sorted(VALID_TRIGGER_TYPES)}",
        )
    if action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action_type '{action_type}'. Valid: {sorted(VALID_ACTION_TYPES)}",
        )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get("/automations", response_model=list[AutomationRuleOut])
async def list_automations(
    enabled: Optional[bool] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> list[AutomationRule]:
    stmt = select(AutomationRule).where(AutomationRule.org_id == org_id)
    if enabled is not None:
        stmt = stmt.where(AutomationRule.enabled.is_(enabled))
    stmt = stmt.order_by(AutomationRule.id.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post("/automations", response_model=AutomationRuleOut, status_code=201)
async def create_automation(
    body: AutomationRuleCreate,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> AutomationRule:
    _validate_types(body.trigger_type, body.action_type)
    rule = AutomationRule(
        org_id=org_id,
        name=body.name,
        description=body.description,
        enabled=body.enabled,
        trigger_type=body.trigger_type,
        trigger_config=body.trigger_config,
        action_type=body.action_type,
        action_config=body.action_config,
        cooldown_seconds=body.cooldown_seconds,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# Get one
# ---------------------------------------------------------------------------


@router.get("/automations/{rule_id}", response_model=AutomationRuleOut)
async def get_automation(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> AutomationRule:
    rule = await _get_or_404(db, rule_id, org_id)
    return rule


# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------


@router.patch("/automations/{rule_id}", response_model=AutomationRuleOut)
async def patch_automation(
    rule_id: int,
    body: AutomationRulePatch,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> AutomationRule:
    rule = await _get_or_404(db, rule_id, org_id)
    updates = body.model_dump(exclude_unset=True)

    # Validate types if being changed
    new_trigger = updates.get("trigger_type", rule.trigger_type)
    new_action = updates.get("action_type", rule.action_type)
    _validate_types(new_trigger, new_action)

    for field, value in updates.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@router.delete("/automations/{rule_id}", status_code=204)
async def delete_automation(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> None:
    rule = await _get_or_404(db, rule_id, org_id)
    await db.delete(rule)
    await db.commit()


# ---------------------------------------------------------------------------
# Test fire
# ---------------------------------------------------------------------------


@router.post("/automations/{rule_id}/test")
async def test_automation(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> dict:
    rule = await _get_or_404(db, rule_id, org_id)
    from app.core.automation_engine import execute_action

    success = True
    error: str | None = None
    try:
        await execute_action(db, rule, context={"test": True})
        await db.commit()
    except Exception as exc:
        success = False
        error = str(exc)

    # Log the test fire
    log_entry = AutomationFireLog(
        rule_id=rule.id,
        fired_at=datetime.now(timezone.utc),
        success=success,
        error_message=error,
        context_json={"test": True},
    )
    db.add(log_entry)
    await db.commit()

    return {"success": success, "message": error or "Action executed successfully (test fire)"}


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get("/automations/{rule_id}/history", response_model=list[AutomationFireLogOut])
async def get_automation_history(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    org_id: int = Depends(get_current_org_id),
) -> list[AutomationFireLog]:
    # Verify ownership
    await _get_or_404(db, rule_id, org_id)
    stmt = (
        select(AutomationFireLog)
        .where(AutomationFireLog.rule_id == rule_id)
        .order_by(AutomationFireLog.fired_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_or_404(db: AsyncSession, rule_id: int, org_id: int) -> AutomationRule:
    result = await db.execute(
        select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.org_id == org_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return rule
