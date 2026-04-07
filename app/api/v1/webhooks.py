from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_org import get_current_org_id
from app.db.models.webhooks import WebhookSubscription, WebhookDelivery

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    secret: str = Field(min_length=1, max_length=256)
    event_filter: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class WebhookOut(BaseModel):
    id: int
    url: str
    event_filter: list[str]
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=WebhookOut, status_code=201)
async def create_webhook(
    data: WebhookCreateIn,
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    sub = WebhookSubscription(
        url=data.url,
        secret=data.secret,
        event_filter=data.event_filter,
        org_id=org_id,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("", response_model=list[WebhookOut])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    stmt = select(WebhookSubscription).order_by(WebhookSubscription.id)
    if org_id is not None:
        stmt = stmt.where(WebhookSubscription.org_id == org_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{webhook_id}", response_model=WebhookOut)
async def get_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    sub = await db.get(WebhookSubscription, webhook_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="webhook not found")
    return sub


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    sub = await db.get(WebhookSubscription, webhook_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="webhook not found")
    await db.delete(sub)
    await db.commit()


class DeliveryOut(BaseModel):
    id: int
    webhook_id: int
    event_id: int
    status_code: int | None
    response_time_ms: float | None
    attempt: int
    success: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/{webhook_id}/deliveries", response_model=list[DeliveryOut])
async def list_deliveries(
    webhook_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List recent delivery attempts for a webhook."""
    sub = await db.get(WebhookSubscription, webhook_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="webhook not found")

    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
