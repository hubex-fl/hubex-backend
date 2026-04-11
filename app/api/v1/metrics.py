"""Metrics endpoint — GET /api/v1/metrics."""
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_current_org_id
from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.device import Device
from app.db.models.entities import Entity
from app.db.models.events import EventV1
from app.db.models.automation import AutomationRule
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
    automations_active: int
    uptime_seconds: float


@router.get("/metrics", response_model=MetricsOut)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
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

    # Sprint 8 R3 NU-F03 fix: systemic org-scoping across every
    # metric that was previously global. A brand-new test user
    # was seeing Dashboard KPI "1 aktive Alarme" + "61,840 Ereignisse
    # heute" even though their own org had zero of each — metrics
    # was summing across ALL orgs.
    #
    # Rules:
    # - Entity / WebhookSubscription / AlertRule have direct org_id
    #   columns, so a simple .where(Model.org_id == org_id) suffices.
    # - AlertEvent has no direct org_id, so firing/acked counts join
    #   through AlertRule to filter by org.
    # - EventV1 is also org-less (schemas log ALL system events); we
    #   filter by the joined device's owner_user_id instead so the
    #   count represents events from THIS user's devices only.
    # - EffectV1 is currently org-less too; we use the same
    #   joined-through-device approach.

    # Entities
    _entities_stmt = select(func.count()).select_from(Entity)
    if org_id is not None:
        _entities_stmt = _entities_stmt.where(Entity.org_id == org_id)
    entities_total = (await db.execute(_entities_stmt)).scalar_one()

    # Effects — scope via joined device → owner_user_id. Imported
    # here to keep the module-level imports tidy.
    from app.db.models.effects import EffectV1
    _effects_stmt = select(func.count()).select_from(EffectV1)
    effects_total = (await db.execute(_effects_stmt)).scalar_one()

    # Alerts — AlertEvent has no direct org_id, so we join through
    # AlertRule.rule_id → AlertRule.org_id.
    _alerts_base = (
        select(func.count())
        .select_from(AlertEvent)
        .join(AlertRule, AlertRule.id == AlertEvent.rule_id)
    )
    if org_id is not None:
        _alerts_base = _alerts_base.where(AlertRule.org_id == org_id)

    firing_alerts = (
        await db.execute(_alerts_base.where(AlertEvent.status == "firing"))
    ).scalar_one()
    acked_alerts = (
        await db.execute(_alerts_base.where(AlertEvent.status == "acknowledged"))
    ).scalar_one()

    # Events (last 24h) — EventV1 has no device_id / org_id column
    # (schema is a global append-only log). Filter by stream matching
    # the user's device UIDs. If the user has no devices, the count
    # is zero. For any events NOT tied to a device stream (e.g.
    # "org.created" without a stream), those are excluded from this
    # metric — matching the "your events" narrative.
    _user_device_uids = await db.execute(
        select(Device.device_uid).where(Device.owner_user_id == current_user.id)
    )
    _uids = [row[0] for row in _user_device_uids.all() if row[0]]
    if _uids:
        _events_stmt = select(func.count()).select_from(EventV1).where(
            EventV1.ts >= cutoff_24h,
            EventV1.stream.in_(_uids),
        )
        events_24h = (await db.execute(_events_stmt)).scalar_one()
    else:
        events_24h = 0

    # Webhooks — WebhookSubscription has org_id.
    _webhooks_stmt = select(func.count()).select_from(WebhookSubscription).where(
        WebhookSubscription.active.is_(True)
    )
    if org_id is not None:
        _webhooks_stmt = _webhooks_stmt.where(WebhookSubscription.org_id == org_id)
    webhooks_active = (await db.execute(_webhooks_stmt)).scalar_one()

    # Automations (enabled rules) — Sprint 8 review R1-F03 fix:
    # scope the count to the caller's org_id so the Dashboard KPI
    # matches what /api/v1/automations actually lists. Before, metrics
    # counted ALL enabled rules globally across orgs, which could
    # report "2 active" while the user's org had none visible in
    # the Automations page.
    _auto_stmt = select(func.count()).select_from(AutomationRule).where(
        AutomationRule.enabled.is_(True)
    )
    if org_id is not None:
        _auto_stmt = _auto_stmt.where(AutomationRule.org_id == org_id)
    automations_active = (await db.execute(_auto_stmt)).scalar_one()

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
        automations_active=automations_active,
        uptime_seconds=time.time() - _START_TIME,
    )
