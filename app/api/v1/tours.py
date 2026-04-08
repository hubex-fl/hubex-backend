"""Tour Builder API — CRUD for custom guided tours."""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_current_org_id
from app.db.models.custom_tour import CustomTour
from app.db.models.user import User
from app.schemas.tour import (
    TourCreate,
    TourOut,
    TourSummaryOut,
    TourUpdate,
)

router = APIRouter(prefix="/tours")


async def _get_tour_or_404(
    tour_id: int, org_id: int | None, db: AsyncSession
) -> CustomTour:
    stmt = select(CustomTour).where(CustomTour.id == tour_id)
    if org_id is not None:
        stmt = stmt.where(CustomTour.org_id == org_id)
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tour not found")
    return t


@router.get("", response_model=list[TourSummaryOut])
async def list_tours(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """List all tours for the current organization."""
    stmt = select(CustomTour).order_by(CustomTour.created_at.desc())
    if org_id is not None:
        stmt = stmt.where(CustomTour.org_id == org_id)
    res = await db.execute(stmt)
    tours = list(res.scalars().all())
    return [
        TourSummaryOut(
            id=t.id,
            name=t.name,
            description=t.description,
            step_count=len(t.steps) if t.steps else 0,
            is_public=t.is_public,
            category=t.category,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tours
    ]


@router.post("", response_model=TourOut, status_code=201)
async def create_tour(
    data: TourCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Create a new custom tour."""
    now = datetime.now(timezone.utc)
    t = CustomTour(
        org_id=org_id,
        owner_id=user.id,
        name=data.name,
        description=data.description,
        steps=[s.model_dump() for s in data.steps],
        is_public=data.is_public,
        category=data.category,
        created_at=now,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


@router.get("/public/{token}", response_model=TourOut)
async def get_public_tour(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Access a publicly shared tour by its token. No authentication required."""
    res = await db.execute(
        select(CustomTour).where(
            CustomTour.public_token == token,
            CustomTour.is_public.is_(True),
        )
    )
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tour not found or not shared")
    return t


@router.get("/{tour_id}", response_model=TourOut)
async def get_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Get a single tour by ID."""
    return await _get_tour_or_404(tour_id, org_id, db)


@router.put("/{tour_id}", response_model=TourOut)
async def update_tour(
    tour_id: int,
    data: TourUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Update a tour."""
    t = await _get_tour_or_404(tour_id, org_id, db)
    if data.name is not None:
        t.name = data.name
    if data.description is not None:
        t.description = data.description
    if data.steps is not None:
        t.steps = [s.model_dump() for s in data.steps]
    if data.is_public is not None:
        t.is_public = data.is_public
    if data.category is not None:
        t.category = data.category
    t.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(t)
    return t


@router.delete("/{tour_id}", status_code=204)
async def delete_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Delete a tour."""
    t = await _get_tour_or_404(tour_id, org_id, db)
    await db.delete(t)
    await db.commit()


@router.post("/{tour_id}/share")
async def share_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Generate a public sharing link for a tour."""
    t = await _get_tour_or_404(tour_id, org_id, db)
    if not t.public_token:
        t.public_token = secrets.token_urlsafe(24)
    t.is_public = True
    t.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"public_token": t.public_token, "url": f"/tours/public/{t.public_token}"}
