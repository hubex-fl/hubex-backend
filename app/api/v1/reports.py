"""Report Generator — template CRUD, generation, and download."""

import io
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.system_events import emit_system_event
from app.db.models.report import ReportTemplate, GeneratedReport
from app.db.models.device import Device
from app.db.models.variables import VariableValue, VariableDefinition
from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.automation import AutomationFireLog
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/reports", tags=["Reports"])


class TemplateCreateIn(BaseModel):
    name: str
    description: str | None = None
    layout: dict = {}
    data_sources: dict = {}
    schedule_cron: str | None = None
    email_recipients: list[str] | None = None
    email_template_id: int | None = None


class TemplateOut(BaseModel):
    id: int
    name: str
    description: str | None
    layout: dict
    data_sources: dict
    schedule_cron: str | None
    email_recipients: list[str] | None
    enabled: bool
    created_at: str


class ReportOut(BaseModel):
    id: int
    template_id: int
    title: str
    format: str
    generated_at: str


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReportTemplate).order_by(ReportTemplate.created_at.desc())
    )
    return [
        TemplateOut(
            id=t.id, name=t.name, description=t.description,
            layout=t.layout, data_sources=t.data_sources,
            schedule_cron=t.schedule_cron,
            email_recipients=t.email_recipients, enabled=t.enabled,
            created_at=t.created_at.isoformat(),
        )
        for t in result.scalars().all()
    ]


@router.post("/templates", response_model=TemplateOut, status_code=201)
async def create_template(
    data: TemplateCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tpl = ReportTemplate(
        name=data.name.strip(),
        description=data.description,
        layout=data.layout,
        data_sources=data.data_sources,
        schedule_cron=data.schedule_cron,
        email_recipients=data.email_recipients,
        email_template_id=data.email_template_id,
        created_by=user.id,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return TemplateOut(
        id=tpl.id, name=tpl.name, description=tpl.description,
        layout=tpl.layout, data_sources=tpl.data_sources,
        schedule_cron=tpl.schedule_cron,
        email_recipients=tpl.email_recipients, enabled=tpl.enabled,
        created_at=tpl.created_at.isoformat(),
    )


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    tpl = await db.get(ReportTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="template not found")
    await db.delete(tpl)
    await db.commit()


@router.post("/generate/{template_id}", response_model=ReportOut)
async def generate_report(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a report from a template. Collects data and renders HTML."""
    tpl = await db.get(ReportTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="template not found")

    now = datetime.now(timezone.utc)
    data_snapshot: dict = {"generated_at": now.isoformat(), "template": tpl.name}

    # Collect data based on data_sources config
    # Device summary
    dev_count = await db.execute(select(func.count(Device.id)))
    data_snapshot["devices_total"] = dev_count.scalar_one() or 0

    online_count = await db.execute(
        select(func.count(Device.id)).where(Device.last_seen_at > now - timedelta(seconds=300))
    )
    data_snapshot["devices_online"] = online_count.scalar_one() or 0

    # Alert summary
    alert_firing = await db.execute(
        select(func.count(AlertEvent.id)).where(AlertEvent.status == "firing")
    )
    data_snapshot["alerts_firing"] = alert_firing.scalar_one() or 0

    alert_total = await db.execute(
        select(func.count(AlertEvent.id)).where(AlertEvent.triggered_at > now - timedelta(days=7))
    )
    data_snapshot["alerts_7d"] = alert_total.scalar_one() or 0

    # Automation stats
    auto_count = await db.execute(
        select(func.count(AutomationFireLog.id)).where(
            AutomationFireLog.fired_at > now - timedelta(days=7)
        )
    )
    data_snapshot["automations_7d"] = auto_count.scalar_one() or 0

    # Variable count
    var_count = await db.execute(select(func.count(VariableDefinition.id)))
    data_snapshot["variable_definitions"] = var_count.scalar_one() or 0

    # Render HTML
    html = _render_report_html(tpl.name, tpl.description, data_snapshot, tpl.layout)

    report = GeneratedReport(
        template_id=tpl.id,
        title=f"{tpl.name} — {now.strftime('%Y-%m-%d %H:%M')}",
        format="html",
        content_html=html,
        data_snapshot=data_snapshot,
        generated_by=user.id,
    )
    db.add(report)
    await emit_system_event(db, "report.generated", {
        "template_id": tpl.id, "user_id": user.id,
    })
    await db.commit()
    await db.refresh(report)

    return ReportOut(
        id=report.id, template_id=report.template_id,
        title=report.title, format=report.format,
        generated_at=report.generated_at.isoformat(),
    )


@router.get("/history", response_model=list[ReportOut])
async def list_generated_reports(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GeneratedReport).order_by(desc(GeneratedReport.generated_at)).limit(limit)
    )
    return [
        ReportOut(
            id=r.id, template_id=r.template_id,
            title=r.title, format=r.format,
            generated_at=r.generated_at.isoformat(),
        )
        for r in result.scalars().all()
    ]


@router.get("/download/{report_id}")
async def download_report(report_id: int, db: AsyncSession = Depends(get_db)):
    """Download a generated report as HTML."""
    report = await db.get(GeneratedReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")

    if not report.content_html:
        raise HTTPException(status_code=404, detail="report has no content")

    return HTMLResponse(
        content=report.content_html,
        headers={"Content-Disposition": f'inline; filename="{report.title}.html"'},
    )


def _render_report_html(name: str, desc: str | None, data: dict, layout: dict) -> str:
    """Render a simple HTML report from collected data."""
    logo = layout.get("logo_url", "")
    color = layout.get("primary_color", "#F5A623")

    rows = ""
    for key, value in data.items():
        if key in ("generated_at", "template"):
            continue
        label = key.replace("_", " ").title()
        rows += f"<tr><td style='padding:8px 12px;border-bottom:1px solid #eee;color:#666'>{label}</td><td style='padding:8px 12px;border-bottom:1px solid #eee;font-weight:600'>{value}</td></tr>"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{name}</title></head>
<body style="font-family:Inter,sans-serif;max-width:800px;margin:0 auto;padding:40px 20px;color:#1f1f2e">
  <div style="border-bottom:3px solid {color};padding-bottom:20px;margin-bottom:30px">
    {f'<img src="{logo}" alt="Logo" style="height:40px;margin-bottom:10px">' if logo else ''}
    <h1 style="margin:0;font-size:24px">{name}</h1>
    {f'<p style="margin:4px 0 0;color:#666;font-size:14px">{desc}</p>' if desc else ''}
    <p style="margin:8px 0 0;color:#999;font-size:12px">Generated: {data.get("generated_at", "")}</p>
  </div>
  <table style="width:100%;border-collapse:collapse">
    {rows}
  </table>
  <div style="margin-top:40px;padding-top:20px;border-top:1px solid #eee;color:#999;font-size:11px">
    Generated by HUBEX Report Generator
  </div>
</body>
</html>"""
