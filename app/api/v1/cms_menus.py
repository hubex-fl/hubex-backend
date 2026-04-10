"""CMS Menus API — navigation menus with pages, links, sections and dividers."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.cms_menu import CmsMenu
from app.db.models.cms_page import CmsPage
from app.db.models.user import User
from app.schemas.cms_menu import (
    CmsMenuCreate,
    CmsMenuOut,
    CmsMenuPublicOut,
    CmsMenuUpdate,
)

router = APIRouter(prefix="/cms", tags=["cms-menus"])


async def _get_menu_or_404(menu_id: int, user_id: int, db: AsyncSession) -> CmsMenu:
    res = await db.execute(
        select(CmsMenu).where(CmsMenu.id == menu_id, CmsMenu.owner_id == user_id)
    )
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Menu not found")
    return m


@router.get("/menus", response_model=list[CmsMenuOut])
async def list_menus(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(CmsMenu)
        .where(CmsMenu.owner_id == current_user.id)
        .order_by(CmsMenu.location.asc(), CmsMenu.id.asc())
    )
    return list(res.scalars().all())


@router.post("/menus", response_model=CmsMenuOut, status_code=201)
async def create_menu(
    data: CmsMenuCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Location must be unique for this owner
    existing = await db.execute(
        select(CmsMenu.id).where(
            CmsMenu.owner_id == current_user.id,
            CmsMenu.location == data.location,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Menu location already used")
    now = datetime.now(timezone.utc)
    m = CmsMenu(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        name=data.name,
        location=data.location,
        items=data.items or [],
        created_at=now,
        updated_at=now,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


@router.get("/menus/location/{location}", response_model=CmsMenuPublicOut)
async def get_menu_by_location(
    location: str,
    db: AsyncSession = Depends(get_db),
):
    """Public menu lookup by location — used by frontend to render nav bars.

    Resolves menu items that reference pages by id: if a referenced page is
    private/unpublished, it is filtered out so it never leaks into the UI.
    """
    res = await db.execute(
        select(CmsMenu).where(CmsMenu.location == location).limit(1)
    )
    m = res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Menu not found")

    items = m.items or []
    filtered = await _filter_items_for_public(items, db)
    return CmsMenuPublicOut(name=m.name, location=m.location, items=filtered)


async def _filter_items_for_public(
    items: list, db: AsyncSession
) -> list:
    """Walk the items tree and strip out page refs that aren't publicly published."""
    # Collect all page ids referenced in the tree
    ids: set[int] = set()

    def _collect(nodes):
        for n in nodes or []:
            if not isinstance(n, dict):
                continue
            if n.get("type") == "page" and isinstance(n.get("page_id"), int):
                ids.add(int(n["page_id"]))
            _collect(n.get("children"))

    _collect(items)
    allowed: set[int] = set()
    page_slugs: dict[int, str] = {}
    page_titles: dict[int, str] = {}
    if ids:
        res = await db.execute(
            select(CmsPage).where(CmsPage.id.in_(ids))
        )
        for p in res.scalars().all():
            if p.published and p.visibility != "private":
                allowed.add(p.id)
                page_slugs[p.id] = p.slug
                page_titles[p.id] = p.title

    def _filter(nodes):
        out: list[dict] = []
        for n in nodes or []:
            if not isinstance(n, dict):
                continue
            node = dict(n)
            t = node.get("type")
            if t == "page":
                pid = node.get("page_id")
                if not isinstance(pid, int) or pid not in allowed:
                    continue
                node["slug"] = page_slugs.get(pid)
                if not node.get("label"):
                    node["label"] = page_titles.get(pid)
            node["children"] = _filter(node.get("children") or [])
            out.append(node)
        return out

    return _filter(items)


@router.get("/menus/{menu_id}", response_model=CmsMenuOut)
async def get_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_menu_or_404(menu_id, current_user.id, db)


@router.put("/menus/{menu_id}", response_model=CmsMenuOut)
async def update_menu(
    menu_id: int,
    data: CmsMenuUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = await _get_menu_or_404(menu_id, current_user.id, db)
    payload = data.model_dump(exclude_none=True)

    new_location = payload.get("location")
    if new_location and new_location != m.location:
        collision = await db.execute(
            select(CmsMenu.id).where(
                CmsMenu.owner_id == current_user.id,
                CmsMenu.location == new_location,
                CmsMenu.id != m.id,
            )
        )
        if collision.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Menu location already used")

    for field, value in payload.items():
        setattr(m, field, value)
    m.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(m)
    return m


@router.delete("/menus/{menu_id}", status_code=204)
async def delete_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = await _get_menu_or_404(menu_id, current_user.id, db)
    await db.delete(m)
    await db.commit()
