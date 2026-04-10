"""CMS URL redirects API — manage HTTP 301/302 redirects for migrated pages."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.cms_redirect import CmsRedirect
from app.db.models.user import User

router = APIRouter(prefix="/cms/redirects", tags=["cms"])


class CmsRedirectIn(BaseModel):
    from_path: str = Field(..., min_length=1, max_length=512)
    to_path: str = Field(..., min_length=1, max_length=512)
    status_code: int = Field(default=301)
    enabled: bool = True


class CmsRedirectOut(BaseModel):
    id: int
    from_path: str
    to_path: str
    status_code: int
    enabled: bool
    hit_count: int
    last_hit_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


def _normalize_path(p: str) -> str:
    p = (p or "").strip()
    if not p:
        return p
    if not p.startswith("/") and not p.startswith("http"):
        p = "/" + p
    return p


@router.get("", response_model=list[CmsRedirectOut])
async def list_redirects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(CmsRedirect)
        .where(CmsRedirect.owner_id == current_user.id)
        .order_by(CmsRedirect.created_at.desc())
    )
    return list(res.scalars().all())


@router.post("", response_model=CmsRedirectOut, status_code=201)
async def create_redirect(
    data: CmsRedirectIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.status_code not in (301, 302):
        raise HTTPException(status_code=400, detail="status_code must be 301 or 302")

    from_path = _normalize_path(data.from_path)
    to_path = _normalize_path(data.to_path)
    if from_path == to_path:
        raise HTTPException(status_code=400, detail="from_path and to_path must differ")

    # Check for duplicates (per owner)
    existing = await db.execute(
        select(CmsRedirect).where(
            CmsRedirect.owner_id == current_user.id,
            CmsRedirect.from_path == from_path,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A redirect for this from_path already exists")

    r = CmsRedirect(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        from_path=from_path,
        to_path=to_path,
        status_code=int(data.status_code),
        enabled=bool(data.enabled),
        hit_count=0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.put("/{redirect_id}", response_model=CmsRedirectOut)
async def update_redirect(
    redirect_id: int,
    data: CmsRedirectIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(CmsRedirect).where(
            CmsRedirect.id == redirect_id,
            CmsRedirect.owner_id == current_user.id,
        )
    )
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Redirect not found")
    if data.status_code not in (301, 302):
        raise HTTPException(status_code=400, detail="status_code must be 301 or 302")
    r.from_path = _normalize_path(data.from_path)
    r.to_path = _normalize_path(data.to_path)
    r.status_code = int(data.status_code)
    r.enabled = bool(data.enabled)
    await db.commit()
    await db.refresh(r)
    return r


@router.delete("/{redirect_id}", status_code=204)
async def delete_redirect(
    redirect_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(CmsRedirect).where(
            CmsRedirect.id == redirect_id,
            CmsRedirect.owner_id == current_user.id,
        )
    )
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Redirect not found")
    await db.delete(r)
    await db.commit()


@router.get("/lookup")
async def lookup_redirect(
    path: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Look up an enabled redirect for an incoming path (no auth; used by middleware).

    Also increments hit_count on match (best-effort).
    """
    normalized = _normalize_path(path)
    res = await db.execute(
        select(CmsRedirect).where(
            CmsRedirect.from_path == normalized,
            CmsRedirect.enabled.is_(True),
        )
    )
    r = res.scalar_one_or_none()
    if not r:
        return {"match": False}
    try:
        r.hit_count = int(r.hit_count or 0) + 1
        r.last_hit_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        await db.rollback()
    return {
        "match": True,
        "to_path": r.to_path,
        "status_code": r.status_code,
    }
