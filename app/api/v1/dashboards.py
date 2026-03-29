"""Dashboard Builder API — CRUD for dashboards and widgets."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.dashboard import Dashboard, DashboardWidget
from app.db.models.user import User
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
        widget_id = item.get("id")
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
