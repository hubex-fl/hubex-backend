"""Metrics endpoint — GET /api/v1/metrics."""
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.alerts import AlertEvent
from app.db.models.device import Device
from app.db.models.entities import Entity
from app.db.models.events import EventV1
from app.db.models.user import User
from app.db.models.webhooks import WebhookSubscription

router = APIRouter(tags=["metrics"])

_START_TIME = time.time()

ONLINE_WINDOW_SECONDS = 300
STALE_WINDOW_SECONDS = 900


class DeviceMetrics(BaseModel):
    total: int
    online: int
    stale: int
    offline: int


class AlertMetrics(BaseModel):
    firing: int
    acknowledged: int


class MetricsOut(BaseModel):
    devices: DeviceMetrics
    entities_total: int
    effects_total: int
    alerts: AlertMetrics
    events_24h: int
    webhooks_active: int
    uptime_seconds: float


@router.get("/metrics", response_model=MetricsOut)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    cutoff_online = now - timedelta(seconds=ONLINE_WINDOW_SECONDS)
    cutoff_stale = now - timedelta(seconds=STALE_WINDOW_SECONDS)
    cutoff_24h = now - timedelta(hours=24)

    # Devices — scoped to current user
    user_device_filter = Device.owner_user_id == current_user.id
    total_devices = (await db.execute(
        select(func.count()).select_from(Device).where(user_device_filter)
    )).scalar_one()
    online_devices = (
        await db.execute(
            select(func.count()).select_from(Device).where(
                user_device_filter,
                Device.last_seen_at.is_not(None),
                Device.last_seen_at >= cutoff_online,
            )
        )
    ).scalar_one()
    stale_devices = (
        await db.execute(
            select(func.count()).select_from(Device).where(
                user_device_filter,
                Device.last_seen_at.is_not(None),
                Device.last_seen_at >= cutoff_stale,
                Device.last_seen_at < cutoff_online,
            )
        )
    ).scalar_one()
    offline_devices = total_devices - online_devices - stale_devices

    # Entities
    entities_total = (await db.execute(select(func.count()).select_from(Entity))).scalar_one()

    # Effects — import here to avoid circular import at module level is fine, but
    # let's import at top of file; EffectV1 might not be in scope, use raw query
    from app.db.models.effects import EffectV1
    effects_total = (await db.execute(select(func.count()).select_from(EffectV1))).scalar_one()

    # Alerts
    firing_alerts = (
        await db.execute(
            select(func.count()).select_from(AlertEvent).where(AlertEvent.status == "firing")
        )
    ).scalar_one()
    acked_alerts = (
        await db.execute(
            select(func.count()).select_from(AlertEvent).where(AlertEvent.status == "acknowledged")
        )
    ).scalar_one()

    # Events (last 24h)
    events_24h = (
        await db.execute(
            select(func.count()).select_from(EventV1).where(EventV1.ts >= cutoff_24h)
        )
    ).scalar_one()

    # Webhooks
    webhooks_active = (
        await db.execute(
            select(func.count()).select_from(WebhookSubscription).where(
                WebhookSubscription.active.is_(True)
            )
        )
    ).scalar_one()

    return MetricsOut(
        devices=DeviceMetrics(
            total=total_devices,
            online=online_devices,
            stale=stale_devices,
            offline=offline_devices,
        ),
        entities_total=entities_total,
        effects_total=effects_total,
        alerts=AlertMetrics(firing=firing_alerts, acknowledged=acked_alerts),
        events_24h=events_24h,
        webhooks_active=webhooks_active,
        uptime_seconds=time.time() - _START_TIME,
    )
