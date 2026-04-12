from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device, get_current_user
from app.db.models.device import Device
from app.db.models.events import EventV1, EventV1Checkpoint
from app.db.models.user import User

router = APIRouter(prefix="/events", tags=["events"])


class EventItemOut(BaseModel):
    cursor: int
    ts: datetime
    type: str
    payload: dict
    trace_id: str | None = None


class EventReadOut(BaseModel):
    stream: str
    cursor: int
    next_cursor: int
    items: list[EventItemOut]


class EventAckIn(BaseModel):
    stream: str = Field(min_length=1, max_length=128)
    subscriber_id: str = Field(min_length=1, max_length=128)
    cursor: int = Field(ge=0)

    model_config = ConfigDict(extra="ignore")


class EventAckOut(BaseModel):
    ok: bool
    stored_cursor: int
    status: str


class EventEmitIn(BaseModel):
    type: str = Field(min_length=1, max_length=128)
    payload: dict
    trace_id: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="ignore")


class EventEmitOut(BaseModel):
    ok: bool
    event_id: int


@router.get("", response_model=EventReadOut)
async def read_events(
    stream: str = Query("system", min_length=1, max_length=128),
    cursor: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    from_ts: Optional[float] = Query(None, description="Unix timestamp (seconds). If set, returns events after this time and overrides cursor."),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(EventV1).where(EventV1.stream == stream)
    if from_ts is not None:
        dt = datetime.fromtimestamp(from_ts, tz=timezone.utc)
        stmt = stmt.where(EventV1.ts >= dt)
    else:
        stmt = stmt.where(EventV1.id > cursor)
    res = await db.execute(
        stmt.order_by(EventV1.id.asc()).limit(limit)
    )
    rows = res.scalars().all()
    items = [
        EventItemOut(
            cursor=row.id,
            ts=row.ts,
            type=row.type,
            payload=row.payload,
            trace_id=row.trace_id,
        )
        for row in rows
    ]
    next_cursor = items[-1].cursor if items else cursor
    return EventReadOut(stream=stream, cursor=cursor, next_cursor=next_cursor, items=items)


@router.get("/my-activity", response_model=list[EventItemOut])
async def read_my_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sprint 8 R4 NU-F05 fix: Dashboard activity feed was pulling from the
    global `stream=system` which shows events from every org. This endpoint
    returns the most recent events whose stream matches one of the CURRENT
    user's devices — mirroring the metrics.py events_24h scoping pattern.

    Returns events ordered by most-recent-first, limited to `limit` rows.
    Returns an empty list for users with no devices.
    """
    # Look up the current user's device UIDs. Events are streamed as
    # `device:<uid>` so we filter by that prefix + list.
    uid_rows = await db.execute(
        select(Device.device_uid).where(Device.owner_user_id == current_user.id)
    )
    uids = [row[0] for row in uid_rows.all() if row[0]]
    if not uids:
        return []

    # Match either the prefixed form (`device:xxx`) or the bare UID for
    # compat. The emit_event handler on this router writes prefixed streams,
    # but legacy data may exist with bare UIDs.
    stream_keys = uids + [f"device:{u}" for u in uids]

    res = await db.execute(
        select(EventV1)
        .where(EventV1.stream.in_(stream_keys))
        .order_by(EventV1.id.desc())
        .limit(limit)
    )
    rows = res.scalars().all()
    return [
        EventItemOut(
            cursor=row.id,
            ts=row.ts,
            type=row.type,
            payload=row.payload,
            trace_id=row.trace_id,
        )
        for row in rows
    ]


@router.get("/{event_id}", response_model=EventItemOut)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(EventV1).where(EventV1.id == event_id))
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    return EventItemOut(
        cursor=row.id,
        ts=row.ts,
        type=row.type,
        payload=row.payload,
        trace_id=row.trace_id,
    )


@router.post("/ack", response_model=EventAckOut)
async def ack_events(
    data: EventAckIn,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(EventV1Checkpoint)
        .where(
            EventV1Checkpoint.stream == data.stream,
            EventV1Checkpoint.subscriber_id == data.subscriber_id,
        )
    )
    checkpoint = res.scalar_one_or_none()
    status = "OK"
    if checkpoint is None:
        checkpoint = EventV1Checkpoint(
            stream=data.stream, subscriber_id=data.subscriber_id, cursor=data.cursor
        )
        db.add(checkpoint)
        await db.commit()
        await db.refresh(checkpoint)
        return EventAckOut(ok=True, stored_cursor=checkpoint.cursor, status=status)

    if data.cursor < checkpoint.cursor:
        status = "NOOP"
        return EventAckOut(ok=True, stored_cursor=checkpoint.cursor, status=status)
    if data.cursor == checkpoint.cursor:
        status = "NOOP"
        return EventAckOut(ok=True, stored_cursor=checkpoint.cursor, status=status)

    checkpoint.cursor = data.cursor
    checkpoint.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return EventAckOut(ok=True, stored_cursor=checkpoint.cursor, status=status)


@router.post("/emit", response_model=EventEmitOut)
async def emit_event(
    data: EventEmitIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    stream = f"device:{device.device_uid}"
    event = EventV1(stream=stream, type=data.type, payload=data.payload, trace_id=data.trace_id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return EventEmitOut(ok=True, event_id=event.id)


class FeedbackIn(BaseModel):
    type: str = Field(default="other", pattern="^(bug|feature|other)$")
    message: str = Field(min_length=1, max_length=5000)
    metadata: dict = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class FeedbackOut(BaseModel):
    ok: bool
    feedback_id: int


@router.post("/feedback", response_model=FeedbackOut)
async def submit_feedback(
    data: FeedbackIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit user feedback with silent metadata for analysis.

    Feedback is stored as an event in the 'feedback' stream so admins
    can query, filter, and export it using the standard events API.
    The metadata (page, viewport, recent pages, console errors, etc.)
    is collected silently by the frontend widget — the user only sees
    and fills in the message text.
    """
    import logging
    logger = logging.getLogger("uvicorn.error")

    payload = {
        "message": data.message,
        "feedback_type": data.type,
        "user_email": user.email,
        "user_id": user.id,
        **data.metadata,
    }

    event = EventV1(
        stream="feedback",
        type=f"feedback.{data.type}",
        payload=payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info(
        "Feedback [%s] from %s: %s",
        data.type, user.email, data.message[:100],
    )

    return FeedbackOut(ok=True, feedback_id=event.id)


@router.get("/export")
async def export_events(
    stream: str = Query("system"),
    limit: int = Query(1000, le=10000),
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
):
    """Export events as CSV or JSON."""
    import csv
    import io
    import json
    from fastapi.responses import StreamingResponse

    result = await db.execute(
        select(EventV1)
        .where(EventV1.stream == stream)
        .order_by(EventV1.id.desc())
        .limit(limit)
    )
    events = list(result.scalars().all())

    if format == "json":
        data = [
            {"id": e.id, "type": e.type, "payload": e.payload, "trace_id": e.trace_id,
             "created_at": e.received_at.isoformat() if e.received_at else None}
            for e in events
        ]
        return StreamingResponse(
            io.BytesIO(json.dumps(data, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="events-export.json"'},
        )

    # CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "type", "payload", "trace_id", "created_at"])
    for e in events:
        writer.writerow([
            e.id, e.type, json.dumps(e.payload) if e.payload else "",
            e.trace_id or "", e.received_at.isoformat() if e.received_at else "",
        ])
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="events-export.csv"'},
    )
