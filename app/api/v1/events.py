from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.events import EventV1, EventV1Checkpoint

router = APIRouter(prefix="/events", tags=["events"])


class EventItemOut(BaseModel):
    cursor: int
    ts: datetime
    type: str
    payload: dict


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


@router.get("", response_model=EventReadOut)
async def read_events(
    stream: str = Query(..., min_length=1, max_length=128),
    cursor: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(EventV1)
        .where(EventV1.stream == stream, EventV1.id > cursor)
        .order_by(EventV1.id.asc())
        .limit(limit)
    )
    rows = res.scalars().all()
    items = [
        EventItemOut(cursor=row.id, ts=row.ts, type=row.type, payload=row.payload)
        for row in rows
    ]
    next_cursor = items[-1].cursor if items else cursor
    return EventReadOut(stream=stream, cursor=cursor, next_cursor=next_cursor, items=items)


@router.get("/{event_id}", response_model=EventItemOut)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(EventV1).where(EventV1.id == event_id))
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    return EventItemOut(cursor=row.id, ts=row.ts, type=row.type, payload=row.payload)


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
