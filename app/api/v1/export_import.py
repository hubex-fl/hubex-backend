"""Export/Import API — export and import HUBEX configuration as JSON bundles."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_current_org_id
from app.core.system_events import emit_system_event
from app.db.models.user import User
from app.db.models.dashboard import Dashboard, DashboardWidget
from app.db.models.automation import AutomationRule, AutomationStep
from app.db.models.variables import VariableDefinition
from app.db.models.alerts import AlertRule
from app.db.models.semantic_type import SemanticType

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/export", tags=["Export/Import"])

EXPORT_VERSION = "1.0"


@router.get("")
async def export_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Export full configuration as JSON bundle."""
    bundle: dict = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": user.email,
    }

    # Dashboards + widgets
    dash_result = await db.execute(
        select(Dashboard).where(Dashboard.owner_id == user.id)
    )
    dashboards = []
    for d in dash_result.scalars().all():
        widgets_result = await db.execute(
            select(DashboardWidget).where(DashboardWidget.dashboard_id == d.id)
            .order_by(DashboardWidget.sort_order)
        )
        widgets = [
            {
                "widget_type": w.widget_type,
                "variable_key": w.variable_key,
                "device_uid": w.device_uid,
                "label": w.label,
                "unit": w.unit,
                "min_value": w.min_value,
                "max_value": w.max_value,
                "display_config": w.display_config,
                "grid_col": w.grid_col,
                "grid_row": w.grid_row,
                "grid_span_w": w.grid_span_w,
                "grid_span_h": w.grid_span_h,
                "sort_order": w.sort_order,
            }
            for w in widgets_result.scalars().all()
        ]
        dashboards.append({
            "name": d.name,
            "description": d.description,
            "is_default": d.is_default,
            "widgets": widgets,
        })
    bundle["dashboards"] = dashboards

    # Automations
    auto_result = await db.execute(select(AutomationRule))
    automations = []
    for r in auto_result.scalars().all():
        steps_result = await db.execute(
            select(AutomationStep).where(AutomationStep.rule_id == r.id)
            .order_by(AutomationStep.step_order)
        )
        steps = [
            {
                "step_order": s.step_order,
                "action_type": s.action_type,
                "action_config": s.action_config,
                "delay_seconds": s.delay_seconds,
                "condition_type": s.condition_type,
                "condition_config": s.condition_config,
            }
            for s in steps_result.scalars().all()
        ]
        automations.append({
            "name": r.name,
            "description": r.description,
            "trigger_type": r.trigger_type,
            "trigger_config": r.trigger_config,
            "action_type": r.action_type,
            "action_config": r.action_config,
            "cooldown_seconds": r.cooldown_seconds,
            "enabled": r.enabled,
            "steps": steps,
        })
    bundle["automations"] = automations

    # Variable definitions
    var_result = await db.execute(select(VariableDefinition))
    bundle["variable_definitions"] = [
        {
            "key": v.key,
            "label": v.label,
            "data_type": v.data_type,
            "unit": v.unit,
            "semantic_type": v.semantic_type,
            "device_writable": v.device_writable,
            "constraints": v.constraints,
            "formula": v.formula,
            "compute_trigger": v.compute_trigger,
        }
        for v in var_result.scalars().all()
    ]

    # Alert rules
    alert_result = await db.execute(select(AlertRule))
    bundle["alert_rules"] = [
        {
            "name": a.name,
            "condition_type": a.condition_type,
            "condition_config": a.condition_config,
            "severity": a.severity,
            "cooldown_seconds": a.cooldown_seconds,
            "enabled": a.enabled,
        }
        for a in alert_result.scalars().all()
    ]

    # Semantic types
    type_result = await db.execute(select(SemanticType))
    bundle["semantic_types"] = [
        {
            "key": t.key,
            "label": t.label,
            "icon": t.icon,
            "color": t.color,
            "unit_default": t.unit_default,
            "data_type": t.data_type,
        }
        for t in type_result.scalars().all()
    ]

    await emit_system_event(db, "config.exported", {
        "user_id": user.id,
        "dashboards": len(dashboards),
        "automations": len(automations),
        "variable_definitions": len(bundle["variable_definitions"]),
    })
    await db.commit()

    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": f'attachment; filename="hubex-export-{datetime.now().strftime("%Y%m%d")}.json"'},
    )


class ImportResult(BaseModel):
    dashboards_imported: int
    automations_imported: int
    variable_definitions_imported: int
    alert_rules_imported: int
    semantic_types_imported: int
    errors: list[str]


@router.post("/import", response_model=ImportResult)
async def import_config(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Import a JSON configuration bundle."""
    import json

    try:
        content = await file.read()
        bundle = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if not isinstance(bundle, dict) or "version" not in bundle:
        raise HTTPException(status_code=400, detail="Invalid export format — missing 'version' field")

    result = ImportResult(
        dashboards_imported=0,
        automations_imported=0,
        variable_definitions_imported=0,
        alert_rules_imported=0,
        semantic_types_imported=0,
        errors=[],
    )

    # Import variable definitions
    for vd in bundle.get("variable_definitions", []):
        try:
            existing = await db.execute(
                select(VariableDefinition).where(VariableDefinition.key == vd["key"])
            )
            if existing.scalar_one_or_none():
                continue  # Skip existing
            db.add(VariableDefinition(
                key=vd["key"],
                label=vd.get("label"),
                data_type=vd.get("data_type", "number"),
                unit=vd.get("unit"),
                semantic_type=vd.get("semantic_type"),
                device_writable=vd.get("device_writable", True),
                constraints=vd.get("constraints"),
                formula=vd.get("formula"),
                compute_trigger=vd.get("compute_trigger"),
            ))
            result.variable_definitions_imported += 1
        except Exception as e:
            result.errors.append(f"variable_def {vd.get('key')}: {e}")

    # Import semantic types
    for st in bundle.get("semantic_types", []):
        try:
            existing = await db.execute(
                select(SemanticType).where(SemanticType.key == st["key"])
            )
            if existing.scalar_one_or_none():
                continue
            db.add(SemanticType(
                key=st["key"],
                label=st.get("label"),
                icon=st.get("icon"),
                color=st.get("color"),
                unit_default=st.get("unit_default"),
                data_type=st.get("data_type"),
            ))
            result.semantic_types_imported += 1
        except Exception as e:
            result.errors.append(f"semantic_type {st.get('key')}: {e}")

    # Import dashboards
    for dash in bundle.get("dashboards", []):
        try:
            d = Dashboard(
                name=dash["name"],
                description=dash.get("description"),
                is_default=dash.get("is_default", False),
                owner_id=user.id,
            )
            db.add(d)
            await db.flush()
            for w in dash.get("widgets", []):
                db.add(DashboardWidget(
                    dashboard_id=d.id,
                    widget_type=w.get("widget_type", "sparkline"),
                    variable_key=w.get("variable_key"),
                    device_uid=w.get("device_uid"),
                    label=w.get("label"),
                    unit=w.get("unit"),
                    min_value=w.get("min_value"),
                    max_value=w.get("max_value"),
                    display_config=w.get("display_config"),
                    grid_col=w.get("grid_col", 1),
                    grid_row=w.get("grid_row", 1),
                    grid_span_w=w.get("grid_span_w", 4),
                    grid_span_h=w.get("grid_span_h", 2),
                    sort_order=w.get("sort_order", 0),
                ))
            result.dashboards_imported += 1
        except Exception as e:
            result.errors.append(f"dashboard {dash.get('name')}: {e}")

    # Import automations
    for auto in bundle.get("automations", []):
        try:
            r = AutomationRule(
                name=auto["name"],
                description=auto.get("description"),
                trigger_type=auto.get("trigger_type", "variable_threshold"),
                trigger_config=auto.get("trigger_config", {}),
                action_type=auto.get("action_type", "create_alert_event"),
                action_config=auto.get("action_config", {}),
                cooldown_seconds=auto.get("cooldown_seconds", 300),
                enabled=auto.get("enabled", False),  # Import disabled by default
            )
            db.add(r)
            await db.flush()
            for s in auto.get("steps", []):
                db.add(AutomationStep(
                    rule_id=r.id,
                    step_order=s.get("step_order", 0),
                    action_type=s.get("action_type", ""),
                    action_config=s.get("action_config", {}),
                    delay_seconds=s.get("delay_seconds", 0),
                    condition_type=s.get("condition_type"),
                    condition_config=s.get("condition_config"),
                ))
            result.automations_imported += 1
        except Exception as e:
            result.errors.append(f"automation {auto.get('name')}: {e}")

    # Import alert rules
    for alert in bundle.get("alert_rules", []):
        try:
            db.add(AlertRule(
                name=alert["name"],
                condition_type=alert.get("condition_type", "variable_threshold"),
                condition_config=alert.get("condition_config", {}),
                severity=alert.get("severity", "warning"),
                cooldown_seconds=alert.get("cooldown_seconds", 300),
                enabled=alert.get("enabled", False),
            ))
            result.alert_rules_imported += 1
        except Exception as e:
            result.errors.append(f"alert {alert.get('name')}: {e}")

    await emit_system_event(db, "config.imported", {
        "user_id": user.id,
        "dashboards": result.dashboards_imported,
        "automations": result.automations_imported,
    })
    await db.commit()

    return result
