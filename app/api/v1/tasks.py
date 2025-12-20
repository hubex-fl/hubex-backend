from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List, Literal
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.api.v1.validators import validate_json_object
from app.db.models.device import Device
from app.db.models.tasks import ExecutionContext, Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

MIN_LEASE_SECONDS = 5
MAX_LEASE_SECONDS = 600
TASK_STATUS_QUEUED = "queued"
TASK_STATUS_IN_FLIGHT = "in_flight"
TERMINAL_STATUSES = {"done", "failed", "canceled"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ContextHeartbeatIn(BaseModel):
    context_key: str = Field(min_length=1, max_length=128)
    capabilities: Dict[str, Any]
    meta: Optional[Dict[str, Any]] = None


class ContextHeartbeatOut(BaseModel):
    id: int
    context_key: str
    last_seen_at: datetime


class TaskPollOut(BaseModel):
    id: int
    type: str
    payload: Dict[str, Any]
    created_at: datetime
    lease_expires_at: datetime
    execution_context_id: Optional[int]
    lease_token: str

    model_config = ConfigDict(from_attributes=True)


class TaskCompleteIn(BaseModel):
    status: Literal["done", "failed", "canceled"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    lease_token: Optional[str] = None


class TaskCompleteOut(BaseModel):
    id: int
    status: str
    completed_at: datetime


class TaskRenewOut(BaseModel):
    id: int
    lease_expires_at: datetime


@router.post("/context/heartbeat", response_model=ContextHeartbeatOut)
async def context_heartbeat(
    data: ContextHeartbeatIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    meta = data.meta or {}
    validate_json_object(data.capabilities, "capabilities")
    validate_json_object(meta, "meta")
    now = _now_utc()
    stmt = (
        insert(ExecutionContext)
        .values(
            client_id=device.id,
            context_key=data.context_key,
            capabilities=data.capabilities,
            meta=meta,
            last_seen_at=now,
        )
        .on_conflict_do_update(
            index_elements=["client_id", "context_key"],
            set_={"capabilities": data.capabilities, "meta": meta, "last_seen_at": now},
        )
        .returning(
            ExecutionContext.id,
            ExecutionContext.context_key,
            ExecutionContext.last_seen_at,
        )
    )
    res = await db.execute(stmt)
    row = res.one()
    device.last_seen_at = now
    await db.commit()
    return ContextHeartbeatOut(id=row.id, context_key=row.context_key, last_seen_at=row.last_seen_at)


@router.post("/poll", response_model=List[TaskPollOut])
async def poll_tasks(
    limit: int = Query(1),
    context_key: Optional[str] = Query(default=None),
    lease_seconds: int = Query(60),
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    limit = max(1, min(50, limit))
    lease_seconds = max(MIN_LEASE_SECONDS, min(MAX_LEASE_SECONDS, lease_seconds))
    now = _now_utc()
    context_id = None
    if context_key:
        res = await db.execute(
            select(ExecutionContext.id).where(
                ExecutionContext.client_id == device.id,
                ExecutionContext.context_key == context_key,
            )
        )
        context_id = res.scalar_one_or_none()
        if context_id is None:
            return []

    stmt = select(Task).where(
        Task.client_id == device.id,
        or_(
            Task.status == TASK_STATUS_QUEUED,
            (Task.status == TASK_STATUS_IN_FLIGHT) & (Task.lease_expires_at < now),
        ),
    )
    if context_id is not None:
        stmt = stmt.where(Task.execution_context_id == context_id)
    stmt = stmt.order_by(desc(Task.priority), Task.created_at).limit(limit).with_for_update(
        skip_locked=True
    )
    res = await db.execute(stmt)
    tasks = list(res.scalars().all())
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    for task in tasks:
        task.status = TASK_STATUS_IN_FLIGHT
        task.claimed_at = now
        task.lease_expires_at = lease_expires_at
        task.lease_token = secrets.token_urlsafe(16)
    device.last_seen_at = now
    await db.commit()

    return [
        TaskPollOut(
            id=task.id,
            type=task.type,
            payload=task.payload,
            created_at=task.created_at,
            lease_expires_at=task.lease_expires_at,
            execution_context_id=task.execution_context_id,
            lease_token=task.lease_token,
        )
        for task in tasks
    ]


@router.post("/{task_id}/complete", response_model=TaskCompleteOut)
async def complete_task(
    task_id: int,
    data: TaskCompleteIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    if data.result is not None:
        validate_json_object(data.result, "result")
    now = _now_utc()
    res = await db.execute(
        select(Task)
        .where(Task.id == task_id, Task.client_id == device.id)
        .with_for_update()
    )
    task = res.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="task already completed")
    if task.status != TASK_STATUS_IN_FLIGHT:
        raise HTTPException(status_code=409, detail="task not in flight")
    if task.lease_expires_at is None or task.lease_expires_at <= now:
        raise HTTPException(status_code=409, detail="task lease expired")
    if not data.lease_token:
        raise HTTPException(status_code=409, detail="task lease token required")
    if task.lease_token != data.lease_token:
        raise HTTPException(status_code=409, detail="task lease token mismatch")
    task.status = data.status
    task.completed_at = now
    task.result = data.result
    task.error = data.error
    await db.commit()
    return TaskCompleteOut(id=task.id, status=task.status, completed_at=task.completed_at)


@router.post("/{task_id}/renew", response_model=TaskRenewOut)
async def renew_task(
    task_id: int,
    lease_seconds: int = Query(60),
    lease_token: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    lease_seconds = max(MIN_LEASE_SECONDS, min(MAX_LEASE_SECONDS, lease_seconds))
    now = _now_utc()
    res = await db.execute(
        select(Task)
        .where(Task.id == task_id, Task.client_id == device.id)
        .with_for_update()
    )
    task = res.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status != TASK_STATUS_IN_FLIGHT:
        raise HTTPException(status_code=409, detail="task not in flight")
    if task.lease_expires_at is None or task.lease_expires_at <= now:
        raise HTTPException(status_code=409, detail="task lease expired")
    if lease_token and task.lease_token != lease_token:
        raise HTTPException(status_code=409, detail="task lease token mismatch")
    task.lease_expires_at = now + timedelta(seconds=lease_seconds)
    await db.commit()
    return TaskRenewOut(id=task.id, lease_expires_at=task.lease_expires_at)
