"""Advanced Observability — traces, incidents, support bundle, anomaly hints."""

import io
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.events import EventV1
from app.db.models.audit import AuditV1Entry
from app.db.models.alerts import AlertEvent
from app.db.models.automation import AutomationFireLog
from app.db.models.device import Device
from app.db.models.variables import VariableHistory
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/observability", tags=["Observability"])


# ── Trace/Timeline ───────────────────────────────────────────────────────────

class TraceEntry(BaseModel):
    timestamp: str
    source: str  # event, audit, alert, automation
    type: str
    summary: str
    trace_id: str | None = None
    device_uid: str | None = None


@router.get("/traces", response_model=list[TraceEntry])
async def get_traces(
    minutes: int = Query(60, le=1440),
    device_uid: str | None = Query(None),
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Timeline view: correlated events, audit entries, alerts, and automations."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    entries: list[TraceEntry] = []

    # System events
    evt_stmt = select(EventV1).where(
        EventV1.stream == "system",
        EventV1.received_at > cutoff,
    ).order_by(desc(EventV1.id)).limit(limit)
    if device_uid:
        # Filter by payload containing device_uid
        pass  # Can't easily filter JSONB here, include all
    evt_result = await db.execute(evt_stmt)
    for e in evt_result.scalars().all():
        payload = e.payload or {}
        d_uid = payload.get("device_uid")
        if device_uid and d_uid != device_uid:
            continue
        entries.append(TraceEntry(
            timestamp=e.received_at.isoformat() if e.received_at else "",
            source="event",
            type=e.type or "",
            summary=f"{e.type}: {json.dumps(payload)[:100]}",
            trace_id=e.trace_id,
            device_uid=d_uid,
        ))

    # Audit entries
    audit_stmt = select(AuditV1Entry).where(
        AuditV1Entry.ts > cutoff,
    ).order_by(desc(AuditV1Entry.id)).limit(limit // 2)
    audit_result = await db.execute(audit_stmt)
    for a in audit_result.scalars().all():
        entries.append(TraceEntry(
            timestamp=a.ts.isoformat() if a.ts else "",
            source="audit",
            type=a.action,
            summary=f"{a.actor_type}:{a.actor_id} → {a.action} ({a.resource or ''})",
            trace_id=a.trace_id,
        ))

    # Alert events
    alert_stmt = select(AlertEvent).where(
        AlertEvent.triggered_at > cutoff,
    ).order_by(desc(AlertEvent.id)).limit(limit // 4)
    alert_result = await db.execute(alert_stmt)
    for al in alert_result.scalars().all():
        entries.append(TraceEntry(
            timestamp=al.triggered_at.isoformat() if al.triggered_at else "",
            source="alert",
            type=f"alert.{al.status}",
            summary=f"Alert #{al.rule_id}: {al.status} (severity: {al.severity})",
        ))

    # Automation fire logs
    auto_stmt = select(AutomationFireLog).where(
        AutomationFireLog.fired_at > cutoff,
    ).order_by(desc(AutomationFireLog.id)).limit(limit // 4)
    auto_result = await db.execute(auto_stmt)
    for af in auto_result.scalars().all():
        entries.append(TraceEntry(
            timestamp=af.fired_at.isoformat() if af.fired_at else "",
            source="automation",
            type="automation.fired",
            summary=f"Rule #{af.rule_id}: {'success' if af.success else 'failed'}",
        ))

    # Sort by timestamp descending
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries[:limit]


# ── Incident Summary ─────────────────────────────────────────────────────────

class IncidentSummary(BaseModel):
    active_alerts: int
    automations_fired_24h: int
    devices_offline: int
    error_events_1h: int


@router.get("/incidents", response_model=IncidentSummary)
async def get_incident_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    # Active alerts
    alert_count = await db.execute(
        select(func.count(AlertEvent.id)).where(AlertEvent.status == "firing")
    )
    active_alerts = alert_count.scalar_one() or 0

    # Automations in 24h
    auto_count = await db.execute(
        select(func.count(AutomationFireLog.id)).where(
            AutomationFireLog.fired_at > now - timedelta(hours=24)
        )
    )
    automations_fired = auto_count.scalar_one() or 0

    # Offline devices
    offline_threshold = now - timedelta(seconds=300)
    offline_count = await db.execute(
        select(func.count(Device.id)).where(
            Device.last_seen_at < offline_threshold
        )
    )
    devices_offline = offline_count.scalar_one() or 0

    # Error events in 1h
    error_count = await db.execute(
        select(func.count(EventV1.id)).where(
            EventV1.stream == "system",
            EventV1.type.like("%.error%"),
            EventV1.received_at > now - timedelta(hours=1),
        )
    )
    error_events = error_count.scalar_one() or 0

    return IncidentSummary(
        active_alerts=active_alerts,
        automations_fired_24h=automations_fired,
        devices_offline=devices_offline,
        error_events_1h=error_events,
    )


# ── Support Bundle ───────────────────────────────────────────────────────────

@router.get("/support-bundle")
async def download_support_bundle(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a diagnostics bundle (JSON) for support tickets."""
    now = datetime.now(timezone.utc)

    # Collect diagnostics
    bundle: dict = {
        "generated_at": now.isoformat(),
        "generated_by": user.email,
    }

    # Device summary
    dev_result = await db.execute(select(func.count(Device.id)))
    bundle["device_count"] = dev_result.scalar_one() or 0

    online_result = await db.execute(
        select(func.count(Device.id)).where(
            Device.last_seen_at > now - timedelta(seconds=300)
        )
    )
    bundle["devices_online"] = online_result.scalar_one() or 0

    # Recent errors
    err_result = await db.execute(
        select(EventV1).where(
            EventV1.stream == "system",
            EventV1.type.like("%.error%"),
        ).order_by(desc(EventV1.id)).limit(20)
    )
    bundle["recent_errors"] = [
        {"type": e.type, "payload": e.payload, "at": e.received_at.isoformat() if e.received_at else None}
        for e in err_result.scalars().all()
    ]

    # Alert summary
    alert_result = await db.execute(
        select(AlertEvent.status, func.count(AlertEvent.id)).group_by(AlertEvent.status)
    )
    bundle["alert_summary"] = {row[0]: row[1] for row in alert_result.fetchall()}

    # Automation stats
    auto_result = await db.execute(
        select(func.count(AutomationFireLog.id)).where(
            AutomationFireLog.fired_at > now - timedelta(hours=24)
        )
    )
    bundle["automations_fired_24h"] = auto_result.scalar_one() or 0

    return StreamingResponse(
        io.BytesIO(json.dumps(bundle, indent=2, default=str).encode()),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="hubex-support-{now.strftime("%Y%m%d")}.json"'},
    )


# ── Anomaly Hints ────────────────────────────────────────────────────────────

class AnomalyHint(BaseModel):
    variable_key: str
    device_id: int | None
    current_value: float | None
    mean: float
    stddev: float
    z_score: float
    hint: str


@router.get("/anomalies", response_model=list[AnomalyHint])
async def detect_anomalies(
    hours: int = Query(24, le=168),
    threshold: float = Query(2.5),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Simple z-score anomaly detection on recent variable history."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Get aggregates per variable_key
    agg_result = await db.execute(
        select(
            VariableHistory.variable_key,
            VariableHistory.device_id,
            func.avg(VariableHistory.numeric_value).label("mean"),
            func.stddev(VariableHistory.numeric_value).label("stddev"),
            func.count(VariableHistory.id).label("cnt"),
        ).where(
            VariableHistory.recorded_at > cutoff,
            VariableHistory.numeric_value.isnot(None),
        ).group_by(
            VariableHistory.variable_key,
            VariableHistory.device_id,
        ).having(
            func.count(VariableHistory.id) > 10,
            func.stddev(VariableHistory.numeric_value) > 0,
        )
    )

    hints: list[AnomalyHint] = []
    for row in agg_result.fetchall():
        var_key, dev_id, mean, stddev, cnt = row
        if stddev is None or stddev == 0:
            continue

        # Get latest value
        latest = await db.execute(
            select(VariableHistory.numeric_value).where(
                VariableHistory.variable_key == var_key,
                VariableHistory.device_id == dev_id,
            ).order_by(desc(VariableHistory.recorded_at)).limit(1)
        )
        current = latest.scalar_one_or_none()
        if current is None:
            continue

        z = abs(current - float(mean)) / float(stddev)
        if z >= threshold:
            hints.append(AnomalyHint(
                variable_key=var_key,
                device_id=dev_id,
                current_value=float(current),
                mean=round(float(mean), 2),
                stddev=round(float(stddev), 2),
                z_score=round(z, 2),
                hint=f"{var_key} is {z:.1f} standard deviations from mean ({mean:.1f} ± {stddev:.1f})",
            ))

    hints.sort(key=lambda h: h.z_score, reverse=True)
    return hints[:20]
