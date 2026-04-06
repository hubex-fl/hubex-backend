"""Email Template CRUD + preview endpoints."""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.email_template import EmailTemplate

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])

# Built-in templates seeded on first access
_BUILTINS = [
    {
        "name": "Alert Notification",
        "category": "alert",
        "subject": "[HUBEX] Alert: {alert_name}",
        "body_html": "<h2>Alert Triggered</h2><p><strong>{alert_name}</strong> fired on device <strong>{device_name}</strong>.</p><p>Variable: {variable_key} = {value}</p><p>Severity: {severity}</p><p><a href='{dashboard_url}'>View Dashboard</a></p>",
        "body_text": "Alert: {alert_name}\nDevice: {device_name}\nVariable: {variable_key} = {value}\nSeverity: {severity}",
        "variables": ["alert_name", "device_name", "variable_key", "value", "severity", "dashboard_url"],
    },
    {
        "name": "Daily Report",
        "category": "report",
        "subject": "[HUBEX] Daily Report — {date}",
        "body_html": "<h2>Daily Report for {date}</h2><p>Devices online: {devices_online} / {devices_total}</p><p>Alerts fired: {alerts_count}</p><p>Automations executed: {automations_count}</p>",
        "body_text": "Daily Report for {date}\nDevices online: {devices_online}/{devices_total}\nAlerts: {alerts_count}\nAutomations: {automations_count}",
        "variables": ["date", "devices_online", "devices_total", "alerts_count", "automations_count"],
    },
    {
        "name": "Welcome",
        "category": "system",
        "subject": "Welcome to HUBEX, {user_name}!",
        "body_html": "<h2>Welcome to HUBEX</h2><p>Hi {user_name},</p><p>Your account has been created. Get started by adding your first device.</p><p><a href='{login_url}'>Sign in</a></p>",
        "body_text": "Welcome to HUBEX\n\nHi {user_name}, your account is ready.\nSign in: {login_url}",
        "variables": ["user_name", "login_url"],
    },
    {
        "name": "Device Offline",
        "category": "alert",
        "subject": "[HUBEX] Device Offline: {device_name}",
        "body_html": "<h2>Device Offline</h2><p><strong>{device_name}</strong> ({device_uid}) has been offline since {offline_since}.</p><p>Last known IP: {last_ip}</p>",
        "body_text": "Device Offline: {device_name} ({device_uid})\nOffline since: {offline_since}",
        "variables": ["device_name", "device_uid", "offline_since", "last_ip"],
    },
]


class TemplateCreateIn(BaseModel):
    name: str
    category: str = "custom"
    subject: str
    body_html: str = ""
    body_text: str = ""
    variables: list[str] | None = None


class TemplateUpdateIn(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    variables: list[str] | None = None


class TemplateOut(BaseModel):
    id: int
    name: str
    category: str
    subject: str
    body_html: str
    body_text: str
    variables: list[str] | None
    is_builtin: bool
    created_at: str
    updated_at: str


class PreviewIn(BaseModel):
    template_id: int
    test_data: dict[str, str] = {}


class PreviewOut(BaseModel):
    subject: str
    body_html: str
    body_text: str


async def _ensure_builtins(db: AsyncSession) -> None:
    """Seed built-in templates if none exist."""
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.is_builtin == True).limit(1)
    )
    if result.scalar_one_or_none():
        return  # Already seeded

    for tpl in _BUILTINS:
        db.add(EmailTemplate(
            name=tpl["name"],
            category=tpl["category"],
            subject=tpl["subject"],
            body_html=tpl["body_html"],
            body_text=tpl["body_text"],
            variables=tpl["variables"],
            is_builtin=True,
        ))
    await db.flush()


@router.get("", response_model=list[TemplateOut])
async def list_templates(db: AsyncSession = Depends(get_db)):
    await _ensure_builtins(db)
    await db.commit()
    result = await db.execute(
        select(EmailTemplate).order_by(EmailTemplate.category, EmailTemplate.name)
    )
    templates = list(result.scalars().all())
    return [
        TemplateOut(
            id=t.id, name=t.name, category=t.category, subject=t.subject,
            body_html=t.body_html, body_text=t.body_text,
            variables=t.variables, is_builtin=t.is_builtin,
            created_at=t.created_at.isoformat(), updated_at=t.updated_at.isoformat(),
        )
        for t in templates
    ]


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(data: TemplateCreateIn, db: AsyncSession = Depends(get_db)):
    tpl = EmailTemplate(
        name=data.name.strip(),
        category=data.category,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        variables=data.variables,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return TemplateOut(
        id=tpl.id, name=tpl.name, category=tpl.category, subject=tpl.subject,
        body_html=tpl.body_html, body_text=tpl.body_text,
        variables=tpl.variables, is_builtin=False,
        created_at=tpl.created_at.isoformat(), updated_at=tpl.updated_at.isoformat(),
    )


@router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int, data: TemplateUpdateIn, db: AsyncSession = Depends(get_db)
):
    tpl = await db.get(EmailTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="template not found")
    if data.name is not None:
        tpl.name = data.name
    if data.subject is not None:
        tpl.subject = data.subject
    if data.body_html is not None:
        tpl.body_html = data.body_html
    if data.body_text is not None:
        tpl.body_text = data.body_text
    if data.variables is not None:
        tpl.variables = data.variables
    tpl.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tpl)
    return TemplateOut(
        id=tpl.id, name=tpl.name, category=tpl.category, subject=tpl.subject,
        body_html=tpl.body_html, body_text=tpl.body_text,
        variables=tpl.variables, is_builtin=tpl.is_builtin,
        created_at=tpl.created_at.isoformat(), updated_at=tpl.updated_at.isoformat(),
    )


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    tpl = await db.get(EmailTemplate, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="template not found")
    if tpl.is_builtin:
        raise HTTPException(status_code=403, detail="cannot delete built-in templates")
    await db.delete(tpl)
    await db.commit()


@router.post("/preview", response_model=PreviewOut)
async def preview_template(data: PreviewIn, db: AsyncSession = Depends(get_db)):
    """Render a template with test data."""
    tpl = await db.get(EmailTemplate, data.template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="template not found")

    def render(text: str, ctx: dict[str, str]) -> str:
        for key, val in ctx.items():
            text = text.replace(f"{{{key}}}", str(val))
        return text

    # Fill missing variables with placeholder
    test = dict(data.test_data)
    for var in (tpl.variables or []):
        if var not in test:
            test[var] = f"[{var}]"

    return PreviewOut(
        subject=render(tpl.subject, test),
        body_html=render(tpl.body_html, test),
        body_text=render(tpl.body_text, test),
    )
