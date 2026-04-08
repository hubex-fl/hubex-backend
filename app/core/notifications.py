"""Email notification dispatcher.

Checks user notification preferences and sends email notifications
for alert events, device offline events, and automation errors.
Uses the existing app.core.email module for SMTP delivery.
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.core.email_templates import (
    render_alert_email,
    render_device_offline_email,
    render_automation_error_email,
    render_digest_email,
)
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

# Default notification preferences
DEFAULT_NOTIFICATION_PREFS: dict[str, Any] = {
    "email_enabled": False,
    "email_alerts": True,
    "email_digest": "off",
    "email_device_offline": True,
    "email_automation_errors": False,
}


def get_notification_prefs(user: User) -> dict[str, Any]:
    """Extract notification preferences from user, with defaults."""
    prefs = dict(DEFAULT_NOTIFICATION_PREFS)
    user_prefs = (user.preferences or {}).get("notifications")
    if isinstance(user_prefs, dict):
        prefs.update(user_prefs)
    return prefs


async def get_org_users(db: AsyncSession, org_id: int | None) -> list[User]:
    """Fetch all users belonging to an org (via membership table).

    Falls back to all users if org_id is None.
    """
    if org_id is not None:
        try:
            from app.db.models.org import OrgMembership
            res = await db.execute(
                select(User).join(OrgMembership, OrgMembership.user_id == User.id)
                .where(OrgMembership.org_id == org_id)
            )
            return list(res.scalars().all())
        except Exception:
            logger.debug("notifications: OrgMembership join failed, falling back to all users")

    res = await db.execute(select(User))
    return list(res.scalars().all())


async def notify_alert_fired(
    db: AsyncSession,
    *,
    rule_name: str,
    severity: str,
    message: str,
    rule_id: int,
    alert_event_id: int,
    org_id: int | None = None,
    variable_key: str | None = None,
    device_name: str | None = None,
) -> int:
    """Send email notifications when an alert fires.

    Returns the number of emails sent.
    """
    users = await get_org_users(db, org_id)
    sent = 0

    for user in users:
        prefs = get_notification_prefs(user)
        if not prefs.get("email_enabled"):
            continue
        if not prefs.get("email_alerts"):
            continue

        subject = f"[HUBEX] Alert: {rule_name} fired"
        body_html = render_alert_email(
            rule_name=rule_name,
            severity=severity,
            message=message,
            rule_id=rule_id,
            alert_event_id=alert_event_id,
            variable_key=variable_key,
            device_name=device_name,
        )
        if send_email(user.email, subject, body_html):
            sent += 1

    if sent:
        logger.info("notifications: alert email sent to %d user(s) rule=%s", sent, rule_name)
    return sent


async def notify_device_offline(
    db: AsyncSession,
    *,
    device_name: str,
    device_uid: str,
    device_id: int,
    offline_seconds: int,
    org_id: int | None = None,
) -> int:
    """Send email notifications when a device goes offline.

    Returns the number of emails sent.
    """
    users = await get_org_users(db, org_id)
    sent = 0

    for user in users:
        prefs = get_notification_prefs(user)
        if not prefs.get("email_enabled"):
            continue
        if not prefs.get("email_device_offline"):
            continue

        subject = f"[HUBEX] Device offline: {device_name}"
        body_html = render_device_offline_email(
            device_name=device_name,
            device_uid=device_uid,
            device_id=device_id,
            offline_seconds=offline_seconds,
        )
        if send_email(user.email, subject, body_html):
            sent += 1

    if sent:
        logger.info("notifications: device-offline email sent to %d user(s) device=%s", sent, device_name)
    return sent


async def notify_automation_error(
    db: AsyncSession,
    *,
    rule_name: str,
    rule_id: int,
    error_message: str,
    org_id: int | None = None,
) -> int:
    """Send email notifications when an automation rule fails.

    Returns the number of emails sent.
    """
    users = await get_org_users(db, org_id)
    sent = 0

    for user in users:
        prefs = get_notification_prefs(user)
        if not prefs.get("email_enabled"):
            continue
        if not prefs.get("email_automation_errors"):
            continue

        subject = f"[HUBEX] Automation error: {rule_name}"
        body_html = render_automation_error_email(
            rule_name=rule_name,
            rule_id=rule_id,
            error_message=error_message,
        )
        if send_email(user.email, subject, body_html):
            sent += 1

    if sent:
        logger.info("notifications: automation-error email sent to %d user(s) rule=%s", sent, rule_name)
    return sent
