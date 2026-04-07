"""Dashboard Builder API — CRUD for dashboards and widgets."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.dashboard import Dashboard, DashboardWidget
from app.db.models.device import Device
from app.db.models.user import User
from app.db.models.variables import VariableHistory
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardOut,
    DashboardSummaryOut,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetOut,
    DashboardWidgetUpdate,
    LayoutUpdate,
)
from app.schemas.variables import VariableHistoryOut, VariableHistoryPointOut

router = APIRouter(prefix="/dashboards")


async def _get_dashboard_or_404(
    dashboard_id: int, user_id: int, db: AsyncSession
) -> Dashboard:
    res = await db.execute(
        select(Dashboard)
        .options(selectinload(Dashboard.widgets))
        .where(Dashboard.id == dashboard_id, Dashboard.owner_id == user_id)
    )
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return d


@router.get("", response_model=list[DashboardSummaryOut])
async def list_dashboards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Dashboard)
        .options(selectinload(Dashboard.widgets))
        .where(Dashboard.owner_id == current_user.id)
        .order_by(Dashboard.is_default.desc(), Dashboard.created_at.asc())
    )
    dashboards = list(res.scalars().all())
    return [
        DashboardSummaryOut(
            id=d.id,
            name=d.name,
            description=d.description,
            is_default=d.is_default,
            sharing_mode=d.sharing_mode,
            widget_count=len(d.widgets),
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in dashboards
    ]


@router.post("", response_model=DashboardOut, status_code=201)
async def create_dashboard(
    data: DashboardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    # If setting as default, unset existing default
    if data.is_default:
        await db.execute(
            update(Dashboard)
            .where(Dashboard.owner_id == current_user.id, Dashboard.is_default.is_(True))
            .values(is_default=False)
        )
    d = Dashboard(
        name=data.name,
        description=data.description,
        is_default=data.is_default,
        sharing_mode=data.sharing_mode,
        owner_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(d)
    await db.flush()
    # reload with widgets
    res = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.widgets)).where(Dashboard.id == d.id)
    )
    d = res.scalar_one()
    await db.commit()
    return d


@router.get("/default", response_model=DashboardOut)
async def get_default_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Dashboard)
        .options(selectinload(Dashboard.widgets))
        .where(Dashboard.owner_id == current_user.id, Dashboard.is_default.is_(True))
        .limit(1)
    )
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="No default dashboard")
    return d


@router.get("/public/{token}", response_model=DashboardOut)
async def get_public_dashboard(
    token: str,
    pin: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Access a publicly shared dashboard by its token. No authentication required."""
    res = await db.execute(
        select(Dashboard)
        .options(selectinload(Dashboard.widgets))
        .where(Dashboard.public_token == token, Dashboard.sharing_mode != "private")
    )
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Dashboard not found or not shared")
    if d.public_pin and d.public_pin != (pin or ""):
        raise HTTPException(status_code=403, detail="Invalid PIN")
    return d


@router.get("/public/{token}/history", response_model=VariableHistoryOut)
async def get_public_variable_history(
    token: str,
    key: str = Query(...),
    device_uid: str | None = Query(default=None, alias="deviceUid"),
    from_time: int | None = Query(default=None, alias="from"),
    limit: int = Query(default=300, ge=1, le=1000),
    pin: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Fetch variable history for a widget on a public dashboard.
    Only allows fetching data for variable_keys that actually exist
    on the dashboard's widgets (security guard).
    """
    # Validate token + PIN
    res = await db.execute(
        select(Dashboard)
        .options(selectinload(Dashboard.widgets))
        .where(Dashboard.public_token == token, Dashboard.sharing_mode != "private")
    )
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Dashboard not found or not shared")
    if d.public_pin and d.public_pin != (pin or ""):
        raise HTTPException(status_code=403, detail="Invalid PIN")

    # Security: only allow variable_keys present on this dashboard
    allowed_keys = {w.variable_key for w in d.widgets if w.variable_key}
    if key not in allowed_keys:
        raise HTTPException(status_code=403, detail="Variable not on this dashboard")

    # Resolve device_id from uid
    device_id = None
    if device_uid:
        dev_res = await db.execute(select(Device.id).where(Device.device_uid == device_uid))
        device_id = dev_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if from_time:
        from_dt = datetime.fromtimestamp(from_time, tz=timezone.utc)
    else:
        from_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(VariableHistory)
        .where(
            VariableHistory.variable_key == key,
            VariableHistory.recorded_at >= from_dt,
            VariableHistory.recorded_at <= now,
        )
    )
    if device_id is not None:
        stmt = stmt.where(VariableHistory.device_id == device_id)

    stmt = stmt.order_by(VariableHistory.recorded_at.desc()).limit(limit)
    res = await db.execute(stmt)
    rows = res.scalars().all()
    points = [
        VariableHistoryPointOut(
            recorded_at=row.recorded_at,
            value=row.value_json,
            numeric_value=row.numeric_value,
            source=row.source,
            t=row.recorded_at.timestamp() if row.recorded_at else 0,
            v=row.numeric_value,
            raw=row.value_json,
        )
        for row in reversed(rows)
    ]
    return VariableHistoryOut(key=key, device_uid=device_uid, points=points, downsampled=False)


@router.post("/{dashboard_id}/share")
async def share_dashboard(
    dashboard_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a public sharing link for a dashboard."""
    import secrets
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    if not d.public_token:
        d.public_token = secrets.token_urlsafe(32)
    d.sharing_mode = "public"
    await db.commit()
    return {"public_token": d.public_token, "url": f"/dashboards/public/{d.public_token}"}


@router.post("/{dashboard_id}/share/pin")
async def set_dashboard_pin(
    dashboard_id: int,
    pin: str = Query(..., min_length=4, max_length=6),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set a PIN for a shared dashboard."""
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    d.public_pin = pin
    d.sharing_mode = "pin"
    await db.commit()
    return {"ok": True, "sharing_mode": "pin"}


@router.post("/{dashboard_id}/unshare")
async def unshare_dashboard(
    dashboard_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove public sharing from a dashboard."""
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    d.sharing_mode = "private"
    d.public_token = None
    d.public_pin = None
    await db.commit()
    return {"ok": True, "sharing_mode": "private"}


@router.get("/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(
    dashboard_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_dashboard_or_404(dashboard_id, current_user.id, db)


@router.put("/{dashboard_id}", response_model=DashboardOut)
async def update_dashboard(
    dashboard_id: int,
    data: DashboardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    if data.name is not None:
        d.name = data.name
    if data.description is not None:
        d.description = data.description
    if data.sharing_mode is not None:
        d.sharing_mode = data.sharing_mode
    if data.is_default is not None:
        if data.is_default and not d.is_default:
            await db.execute(
                update(Dashboard)
                .where(
                    Dashboard.owner_id == current_user.id,
                    Dashboard.is_default.is_(True),
                    Dashboard.id != dashboard_id,
                )
                .values(is_default=False)
            )
        d.is_default = data.is_default
    d.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return d


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(
    dashboard_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    await db.delete(d)
    await db.commit()


# ── Widget endpoints ──────────────────────────────────────────────────────────

@router.post("/{dashboard_id}/widgets", response_model=DashboardWidgetOut, status_code=201)
async def add_widget(
    dashboard_id: int,
    data: DashboardWidgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    w = DashboardWidget(
        dashboard_id=d.id,
        widget_type=data.widget_type,
        variable_key=data.variable_key,
        device_uid=data.device_uid,
        label=data.label,
        unit=data.unit,
        min_value=data.min_value,
        max_value=data.max_value,
        display_config=data.display_config,
        grid_col=data.grid_col,
        grid_row=data.grid_row,
        grid_span_w=data.grid_span_w,
        grid_span_h=data.grid_span_h,
        sort_order=data.sort_order if data.sort_order else len(d.widgets),
        created_at=datetime.now(timezone.utc),
    )
    db.add(w)
    d.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(w)
    return w


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=DashboardWidgetOut)
async def update_widget(
    dashboard_id: int,
    widget_id: int,
    data: DashboardWidgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    res = await db.execute(
        select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
    )
    w = res.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(w, field, val)
    await db.commit()
    await db.refresh(w)
    return w


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def delete_widget(
    dashboard_id: int,
    widget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    res = await db.execute(
        select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id,
        )
    )
    w = res.scalar_one_or_none()
    if w:
        await db.delete(w)
        await db.commit()


@router.put("/{dashboard_id}/layout")
async def update_layout(
    dashboard_id: int,
    data: LayoutUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk update widget positions for drag-drop reorder."""
    d = await _get_dashboard_or_404(dashboard_id, current_user.id, db)
    for item in data.widgets:
        widget_id = item.get("widget_id") or item.get("id")
        if not widget_id:
            continue
        updates = {
            k: v for k, v in item.items()
            if k in ("grid_col", "grid_row", "grid_span_w", "grid_span_h", "sort_order")
            and v is not None
        }
        if updates:
            await db.execute(
                update(DashboardWidget)
                .where(
                    DashboardWidget.id == widget_id,
                    DashboardWidget.dashboard_id == dashboard_id,
                )
                .values(**updates)
            )
    d.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}
