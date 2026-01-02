from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.audit import AuditV1Entry

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEntryOut(BaseModel):
    id: int
    ts: datetime
    actor_type: str
    actor_id: str
    action: str
    resource: str | None
    audit_metadata: dict | None = Field(
        default=None, serialization_alias="metadata", validation_alias="audit_metadata"
    )
    trace_id: str | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


@router.get("", response_model=list[AuditEntryOut])
async def list_audit_entries(
    actor_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditV1Entry)
    if actor_id:
        stmt = stmt.where(AuditV1Entry.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditV1Entry.action == action)
    res = await db.execute(stmt.order_by(desc(AuditV1Entry.id)).limit(limit))
    return list(res.scalars().all())


@router.get("/{entry_id}", response_model=AuditEntryOut)
async def get_audit_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(AuditV1Entry).where(AuditV1Entry.id == entry_id))
    entry = res.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="audit entry not found")
    return entry
