"""Helper for emitting system lifecycle events into events_v1."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.events import EventV1

SYSTEM_STREAM = "system"


async def emit_system_event(
    db: AsyncSession,
    event_type: str,
    payload: dict,
) -> EventV1:
    """Write a system event to events_v1. Caller must commit."""
    event = EventV1(
        stream=SYSTEM_STREAM,
        ts=datetime.now(timezone.utc),
        type=event_type,
        payload=payload,
    )
    db.add(event)
    return event
