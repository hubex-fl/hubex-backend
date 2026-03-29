"""Notification service — creates DB records and pushes via WebSocket."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notifications import Notification
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: str = "",
    severity: str = "info",
    entity_ref: Optional[str] = None,
) -> Notification:
    """Create a notification for a specific user and push it via WebSocket."""
    notif = Notification(
        user_id=user_id,
        type=type,
        severity=severity,
        title=title,
        message=message,
        entity_ref=entity_ref,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notif)
    await db.flush()

    # Push via WebSocket (non-blocking — ignore errors)
    try:
        from app.realtime import user_hub  # avoid circular at module level

        await user_hub.push_notification(
            user_id,
            {
                "id": notif.id,
                "type": notif.type,
                "severity": notif.severity,
                "title": notif.title,
                "message": notif.message,
                "entity_ref": notif.entity_ref,
                "created_at": notif.created_at.isoformat(),
                "read_at": None,
            },
        )
    except Exception:
        logger.exception("notification_service: failed to push WS notification user_id=%s", user_id)

    return notif


async def create_notification_all_users(
    db: AsyncSession,
    type: str,
    title: str,
    message: str = "",
    severity: str = "info",
    entity_ref: Optional[str] = None,
) -> None:
    """Create the same notification for every user in the system."""
    res = await db.execute(select(User))
    users = list(res.scalars().all())
    for user in users:
        await create_notification(
            db,
            user_id=user.id,
            type=type,
            title=title,
            message=message,
            severity=severity,
            entity_ref=entity_ref,
        )
