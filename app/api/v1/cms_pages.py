"""CMS Pages API — custom HTML/Markdown pages with template variables and sharing."""
import re
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.cms_templates import PREDEFINED_TEMPLATES, get_template, list_templates
from app.db.models.cms_page import CmsPage
from app.db.models.cms_page_version import CmsPageVersion
from app.db.models.device import Device
from app.db.models.user import User
from app.db.models.variables import VariableValue
from app.schemas.cms_page import (
    CmsPageCreate,
    CmsPageMove,
    CmsPageOut,
    CmsPagePublicOut,
    CmsPageScheduleIn,
    CmsPageSummaryOut,
    CmsPageTreeNode,
    CmsPageUpdate,
    CmsPageVersionOut,
    CmsPageVersionSummary,
)

router = APIRouter(prefix="/cms", tags=["cms"])


# ── Template variable substitution ────────────────────────────────────────

_TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([^}\s]+)\s*\}\}")
_SIMPLE_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


async def _resolve_template_var(
    db: AsyncSession,
    kind: str,
    ref: str,
    user_id: int | None,
) -> str:
    """Resolve a single template var like {{variable:temperature}} to its string value."""
    try:
        if kind == "variable":
            # ref may be "key" or "device_uid:key"
            device_uid: str | None = None
            key = ref
            if ":" in ref:
                device_uid, key = ref.split(":", 1)
            stmt = select(VariableValue).where(VariableValue.variable_key == key)
            if device_uid:
                dev_res = await db.execute(select(Device.id).where(Device.device_uid == device_uid))
                dev_id = dev_res.scalar_one_or_none()
                if dev_id is not None:
                    stmt = stmt.where(VariableValue.device_id == dev_id)
            stmt = stmt.limit(1)
            res = await db.execute(stmt)
            val = res.scalar_one_or_none()
            if val is None or val.value_json is None:
                return "—"
            return str(val.value_json)

        if kind == "device":
            # ref is "device_uid:attr" (attr = name|type|status)
            device_uid: str | None = None
            attr = "name"
            if ":" in ref:
                device_uid, attr = ref.split(":", 1)
            else:
                device_uid = ref
            res = await db.execute(select(Device).where(Device.device_uid == device_uid))
            dev = res.scalar_one_or_none()
            if not dev:
                return "—"
            if attr == "name":
                return dev.name or dev.device_uid
            if attr == "type":
                return dev.device_type or ""
            if attr == "uid":
                return dev.device_uid
            if attr == "status":
                return "online" if dev.last_seen_at else "offline"
            return "—"

        if kind == "metric":
            # Compute basic metrics on the fly
            if ref == "devices_total":
                q = select(func.count()).select_from(Device)
                if user_id is not None:
                    q = q.where(Device.owner_user_id == user_id)
                r = await db.execute(q)
                return str(r.scalar_one())
            if ref == "devices_online":
                from datetime import timedelta as _td
                now = datetime.now(timezone.utc)
                cutoff = now - _td(seconds=90)
                q = select(func.count()).select_from(Device).where(
                    Device.last_seen_at.is_not(None),
                    Device.last_seen_at >= cutoff,
                )
                if user_id is not None:
                    q = q.where(Device.owner_user_id == user_id)
                r = await db.execute(q)
                return str(r.scalar_one())
            return "—"

        if kind == "timestamp":
            # e.g. {{timestamp:iso}} / {{timestamp:date}}
            now = datetime.now(timezone.utc)
            if ref == "iso":
                return now.isoformat()
            if ref == "date":
                return now.strftime("%Y-%m-%d")
            if ref == "time":
                return now.strftime("%H:%M:%S")
            return now.isoformat()
    except Exception:
        return "—"
    return "—"


async def render_template_vars(
    content: str,
    db: AsyncSession,
    user_id: int | None,
) -> str:
    """Replace {{kind:ref}} and simple {{kind}} placeholders in content."""
    if not content:
        return content

    async def _find_and_replace() -> str:
        matches = list(_TEMPLATE_RE.finditer(content))
        out = content
        for m in matches:
            kind = m.group(1)
            ref = m.group(2)
            value = await _resolve_template_var(db, kind, ref, user_id)
            out = out.replace(m.group(0), value)

        # Handle simple forms like {{timestamp}}
        simple_matches = list(_SIMPLE_RE.finditer(out))
        for m in simple_matches:
            kind = m.group(1)
            value = await _resolve_template_var(db, kind, "iso" if kind == "timestamp" else "", user_id)
            out = out.replace(m.group(0), value)
        return out

    return await _find_and_replace()


# ── Helpers ───────────────────────────────────────────────────────────────

async def _get_page_or_404(page_id: int, user_id: int, db: AsyncSession) -> CmsPage:
    res = await db.execute(
        select(CmsPage).where(CmsPage.id == page_id, CmsPage.owner_id == user_id)
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="CMS page not found")
    return p


async def _slug_exists(db: AsyncSession, slug: str, exclude_id: int | None = None) -> bool:
    stmt = select(CmsPage.id).where(CmsPage.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(CmsPage.id != exclude_id)
    r = await db.execute(stmt)
    return r.scalar_one_or_none() is not None


# ── Search ────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_pages(
    q: str = Query(..., min_length=1, max_length=256),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full-text search in title, description and content_html. Returns max 20 results with snippets."""
    pattern = f"%{q}%"
    stmt = (
        select(CmsPage)
        .where(CmsPage.owner_id == current_user.id)
        .where(
            (CmsPage.title.ilike(pattern))
            | (CmsPage.description.ilike(pattern))
            | (CmsPage.content_html.ilike(pattern))
        )
        .order_by(CmsPage.updated_at.desc())
        .limit(20)
    )
    res = await db.execute(stmt)
    pages = list(res.scalars().all())

    def _snippet(text: str | None, needle: str, around: int = 60) -> str:
        if not text:
            return ""
        # Strip HTML tags for snippet display
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        lower = plain.lower()
        idx = lower.find(needle.lower())
        if idx < 0:
            return (plain[:120] + "…") if len(plain) > 120 else plain
        start = max(0, idx - around)
        end = min(len(plain), idx + len(needle) + around)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(plain) else ""
        return f"{prefix}{plain[start:end]}{suffix}"

    results = []
    needle = q.lower()
    for p in pages:
        # Pick the best source for the snippet
        source = p.title
        if p.description and needle in (p.description or "").lower():
            source = p.description
        elif p.content_html and needle in (p.content_html or "").lower():
            source = p.content_html
        results.append({
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "layout": p.layout,
            "visibility": p.visibility,
            "published": p.published,
            "updated_at": p.updated_at,
            "snippet": _snippet(source, q),
        })
    return {"query": q, "count": len(results), "results": results}


# ── CRUD ──────────────────────────────────────────────────────────────────

@router.get("/pages", response_model=list[CmsPageSummaryOut])
async def list_pages(
    filter: str | None = Query(default=None, description="all|published|drafts|public"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(CmsPage).where(CmsPage.owner_id == current_user.id)
    if filter == "published":
        stmt = stmt.where(CmsPage.published.is_(True))
    elif filter == "drafts":
        stmt = stmt.where(CmsPage.published.is_(False))
    elif filter == "public":
        stmt = stmt.where(CmsPage.visibility != "private")
    stmt = stmt.order_by(CmsPage.updated_at.desc())
    res = await db.execute(stmt)
    pages = list(res.scalars().all())
    return pages


@router.get("/pages/tree", response_model=list[CmsPageTreeNode])
async def get_pages_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return owned pages as a nested tree ordered by menu_order."""
    res = await db.execute(
        select(CmsPage)
        .where(CmsPage.owner_id == current_user.id)
        .order_by(CmsPage.menu_order.asc(), CmsPage.id.asc())
    )
    pages = list(res.scalars().all())

    # Build map id -> tree node dict
    node_map: dict[int, dict[str, Any]] = {}
    for p in pages:
        node_map[p.id] = {
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "layout": p.layout,
            "visibility": p.visibility,
            "published": p.published,
            "parent_id": p.parent_id,
            "menu_order": p.menu_order or 0,
            "show_in_menu": bool(p.show_in_menu),
            "children": [],
        }

    roots: list[dict[str, Any]] = []
    for p in pages:
        node = node_map[p.id]
        parent = node_map.get(p.parent_id) if p.parent_id else None
        if parent is not None and p.parent_id != p.id:
            parent["children"].append(node)
        else:
            roots.append(node)

    return roots


@router.post("/pages", response_model=CmsPageOut, status_code=201)
async def create_page(
    data: CmsPageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if await _slug_exists(db, data.slug):
        raise HTTPException(status_code=409, detail="Slug already exists")
    now = datetime.now(timezone.utc)
    # Validate parent_id if provided
    if data.parent_id is not None:
        parent_res = await db.execute(
            select(CmsPage.id).where(
                CmsPage.id == data.parent_id,
                CmsPage.owner_id == current_user.id,
            )
        )
        if parent_res.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="Parent page not found")

    p = CmsPage(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        slug=data.slug,
        title=data.title,
        description=data.description,
        content_html=data.content_html or "",
        content_mode=data.content_mode,
        layout=data.layout,
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        og_image=data.og_image,
        visibility=data.visibility,
        published=data.published,
        published_at=now if data.published else None,
        created_at=now,
        updated_at=now,
        blocks=data.blocks,
        parent_id=data.parent_id,
        menu_order=data.menu_order or 0,
        show_in_menu=bool(data.show_in_menu),
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


async def _render_page_html(p: CmsPage, db: AsyncSession) -> str:
    """Render a page to HTML — uses blocks if present, otherwise content_html."""
    if getattr(p, "blocks", None):
        from app.core.cms_renderer import render_blocks_to_html
        return await render_blocks_to_html(p.blocks, db, p.owner_id)
    return await render_template_vars(p.content_html or "", db, p.owner_id)


@router.get("/pages/slug/{slug}", response_model=CmsPagePublicOut)
async def get_page_by_slug(
    slug: str,
    pin: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Public view by slug — only works for published public pages."""
    res = await db.execute(
        select(CmsPage).where(
            CmsPage.slug == slug,
            CmsPage.published.is_(True),
            CmsPage.visibility != "private",
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Page not found")
    if p.public_pin and p.public_pin != (pin or ""):
        raise HTTPException(status_code=403, detail="Invalid PIN")

    # Analytics: increment view count (best-effort)
    try:
        p.view_count = int(getattr(p, "view_count", 0) or 0) + 1
        p.last_viewed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        await db.rollback()

    rendered = await _render_page_html(p, db)
    return CmsPagePublicOut(
        slug=p.slug,
        title=p.title,
        description=p.description,
        content_html=rendered,
        content_mode=p.content_mode,
        layout=p.layout,
        meta_title=p.meta_title,
        meta_description=p.meta_description,
        og_image=p.og_image,
        published_at=p.published_at,
    )


@router.get("/pages/public/{token}", response_model=CmsPagePublicOut)
async def get_public_page(
    token: str,
    pin: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Public view by token — no auth. Supports embed."""
    res = await db.execute(
        select(CmsPage).where(
            CmsPage.public_token == token,
            CmsPage.visibility != "private",
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Page not found or not shared")
    if p.public_pin and p.public_pin != (pin or ""):
        raise HTTPException(status_code=403, detail="Invalid PIN")

    rendered = await _render_page_html(p, db)

    out = CmsPagePublicOut(
        slug=p.slug,
        title=p.title,
        description=p.description,
        content_html=rendered,
        content_mode=p.content_mode,
        layout=p.layout,
        meta_title=p.meta_title,
        meta_description=p.meta_description,
        og_image=p.og_image,
        published_at=p.published_at,
    )

    # If embed: permissive framing headers
    if p.visibility == "embed":
        return JSONResponse(
            content=out.model_dump(mode="json"),
            headers={
                "X-Frame-Options": "ALLOWALL",
                "Content-Security-Policy": "frame-ancestors *",
            },
        )
    return out


@router.get("/pages/{page_id}", response_model=CmsPageOut)
async def get_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    return CmsPageOut.from_orm_with_pin(p)


async def _snapshot_version(
    db: AsyncSession, page: CmsPage, created_by: int | None, note: str | None = None
) -> None:
    """Snapshot the CURRENT state of `page` into a new version row.

    Keeps the last 50 versions per page (older ones get deleted).
    """
    # Determine next version_num
    res = await db.execute(
        select(func.max(CmsPageVersion.version_num)).where(CmsPageVersion.page_id == page.id)
    )
    latest = res.scalar() or 0
    version_num = latest + 1
    ver = CmsPageVersion(
        page_id=page.id,
        version_num=version_num,
        title=page.title,
        content_html=page.content_html or "",
        blocks=getattr(page, "blocks", None),
        created_by=created_by,
        note=note,
    )
    db.add(ver)

    # Prune older versions beyond the 50 most recent
    res_all = await db.execute(
        select(CmsPageVersion.id)
        .where(CmsPageVersion.page_id == page.id)
        .order_by(CmsPageVersion.version_num.desc())
    )
    all_ids = [row[0] for row in res_all.fetchall()]
    if len(all_ids) >= 50:
        to_delete = all_ids[49:]
        if to_delete:
            await db.execute(
                CmsPageVersion.__table__.delete().where(CmsPageVersion.id.in_(to_delete))
            )


@router.put("/pages/{page_id}", response_model=CmsPageOut)
async def update_page(
    page_id: int,
    data: CmsPageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    payload = data.model_dump(exclude_none=True)
    if "slug" in payload and payload["slug"] != p.slug:
        if await _slug_exists(db, payload["slug"], exclude_id=p.id):
            raise HTTPException(status_code=409, detail="Slug already exists")

    # Snapshot the CURRENT state before applying updates.
    try:
        content_keys = {"content_html", "blocks", "title", "content_mode", "layout"}
        if content_keys & set(payload.keys()):
            note = "Published" if (data.published is True) else "Auto-save"
            await _snapshot_version(db, p, created_by=current_user.id, note=note)
    except Exception:
        pass

    for field, value in payload.items():
        setattr(p, field, value)
    if data.published is True and not p.published_at:
        p.published_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


# ── Version history ──────────────────────────────────────────────────────

@router.get("/pages/{page_id}/versions", response_model=list[CmsPageVersionSummary])
async def list_page_versions(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_page_or_404(page_id, current_user.id, db)
    res = await db.execute(
        select(CmsPageVersion)
        .where(CmsPageVersion.page_id == page_id)
        .order_by(CmsPageVersion.version_num.desc())
    )
    return list(res.scalars().all())


@router.get("/pages/{page_id}/versions/{ver}", response_model=CmsPageVersionOut)
async def get_page_version(
    page_id: int,
    ver: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_page_or_404(page_id, current_user.id, db)
    res = await db.execute(
        select(CmsPageVersion).where(
            CmsPageVersion.page_id == page_id,
            CmsPageVersion.version_num == ver,
        )
    )
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return v


@router.post("/pages/{page_id}/versions/{ver}/restore", response_model=CmsPageOut)
async def restore_page_version(
    page_id: int,
    ver: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    res = await db.execute(
        select(CmsPageVersion).where(
            CmsPageVersion.page_id == page_id,
            CmsPageVersion.version_num == ver,
        )
    )
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    try:
        await _snapshot_version(
            db, p, created_by=current_user.id, note=f"Before restore to v{ver}"
        )
    except Exception:
        pass
    p.title = v.title
    p.content_html = v.content_html or ""
    p.blocks = v.blocks
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.put("/pages/{page_id}/move", response_model=CmsPageOut)
async def move_page(
    page_id: int,
    data: CmsPageMove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a page to a new parent and/or reorder within its siblings.

    Prevents cycles: a page cannot become a descendant of itself.
    """
    p = await _get_page_or_404(page_id, current_user.id, db)

    new_parent_id = data.parent_id

    if new_parent_id is not None:
        if new_parent_id == p.id:
            raise HTTPException(status_code=400, detail="Cannot set page as its own parent")
        # Check parent exists + owned by user
        parent_res = await db.execute(
            select(CmsPage).where(
                CmsPage.id == new_parent_id,
                CmsPage.owner_id == current_user.id,
            )
        )
        parent = parent_res.scalar_one_or_none()
        if parent is None:
            raise HTTPException(status_code=404, detail="Target parent not found")

        # Walk up from parent to ensure we don't create a cycle
        visited: set[int] = set()
        cur = parent
        while cur is not None and cur.parent_id is not None:
            if cur.parent_id in visited:
                break
            visited.add(cur.parent_id)
            if cur.parent_id == p.id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move page: target is a descendant of this page",
                )
            res = await db.execute(
                select(CmsPage).where(CmsPage.id == cur.parent_id)
            )
            cur = res.scalar_one_or_none()

    p.parent_id = new_parent_id
    p.menu_order = data.menu_order or 0
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.delete("/pages/{page_id}", status_code=204)
async def delete_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    await db.delete(p)
    await db.commit()


@router.post("/pages/{page_id}/publish", response_model=CmsPageOut)
async def publish_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.published = True
    p.published_at = datetime.now(timezone.utc)
    p.status = "published"
    p.scheduled_at = None
    p.updated_at = p.published_at
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.post("/pages/{page_id}/unpublish", response_model=CmsPageOut)
async def unpublish_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.published = False
    p.status = "draft"
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.post("/pages/{page_id}/share")
async def share_page(
    page_id: int,
    mode: str = Query(default="public"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate or return a public share token. mode = 'public' | 'embed'."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    if not p.public_token:
        p.public_token = secrets.token_urlsafe(32)
    if mode == "embed":
        p.visibility = "embed"
    else:
        p.visibility = "public"
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "public_token": p.public_token,
        "visibility": p.visibility,
        "public_url": f"/p/{p.slug}",
        "embed_url": f"/api/v1/cms/pages/public/{p.public_token}",
    }


@router.delete("/pages/{page_id}/share")
async def unshare_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.visibility = "private"
    p.public_token = None
    p.public_pin = None
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.post("/pages/{page_id}/pin")
async def set_page_pin(
    page_id: int,
    pin: str = Query(..., min_length=4, max_length=8),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.public_pin = pin
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/pages/{page_id}/pin")
async def remove_page_pin(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.public_pin = None
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.post("/pages/{page_id}/clone", response_model=CmsPageOut, status_code=201)
async def clone_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    src = await _get_page_or_404(page_id, current_user.id, db)
    now = datetime.now(timezone.utc)
    # Find a unique slug
    base = f"{src.slug}-copy"
    slug = base
    i = 1
    while await _slug_exists(db, slug):
        i += 1
        slug = f"{base}-{i}"
    new_p = CmsPage(
        org_id=src.org_id,
        owner_id=current_user.id,
        slug=slug,
        title=f"{src.title} (Copy)",
        description=src.description,
        content_html=src.content_html,
        content_mode=src.content_mode,
        layout=src.layout,
        meta_title=src.meta_title,
        meta_description=src.meta_description,
        og_image=src.og_image,
        visibility="private",
        published=False,
        created_at=now,
        updated_at=now,
        blocks=getattr(src, "blocks", None),
    )
    db.add(new_p)
    await db.commit()
    await db.refresh(new_p)
    return CmsPageOut.from_orm_with_pin(new_p)


@router.get("/pages/{page_id}/render")
async def render_page_preview(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Render the page with template variables substituted — for logged-in preview."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    if getattr(p, "blocks", None):
        from app.core.cms_renderer import render_blocks_to_html
        rendered = await render_blocks_to_html(p.blocks, db, current_user.id)
    else:
        rendered = await render_template_vars(p.content_html or "", db, current_user.id)
    return {
        "slug": p.slug,
        "title": p.title,
        "content_html": rendered,
        "layout": p.layout,
        "content_mode": p.content_mode,
        "blocks": getattr(p, "blocks", None),
    }


# ── Templates ─────────────────────────────────────────────────────────────


@router.get("/templates")
async def list_cms_templates():
    """Return list of predefined CMS page templates."""
    return {"templates": list_templates()}


@router.get("/templates/{template_id}")
async def get_cms_template(template_id: str):
    """Return a single template's full details (including content_html)."""
    t = get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.post("/pages/from-template/{template_id}", response_model=CmsPageOut, status_code=201)
async def create_page_from_template(
    template_id: str,
    slug: str = Query(..., min_length=1, max_length=128),
    title: str = Query(..., min_length=1, max_length=256),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new CMS page from a predefined template."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if await _slug_exists(db, slug):
        raise HTTPException(status_code=409, detail="Slug already exists")
    now = datetime.now(timezone.utc)
    p = CmsPage(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        slug=slug,
        title=title,
        description=template.get("description"),
        content_html=template.get("content_html", ""),
        content_mode=template.get("content_mode", "html"),
        layout=template.get("layout", "default"),
        visibility="private",
        published=False,
        created_at=now,
        updated_at=now,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


# ── Export / Import ───────────────────────────────────────────────────────

@router.get("/pages/{page_id}/export")
async def export_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export a page as JSON (all fields + blocks) for backup or transfer."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    return {
        "schema_version": 1,
        "slug": p.slug,
        "title": p.title,
        "description": p.description,
        "content_html": p.content_html or "",
        "content_mode": p.content_mode,
        "layout": p.layout,
        "meta_title": p.meta_title,
        "meta_description": p.meta_description,
        "og_image": p.og_image,
        "visibility": "private",  # Always reset visibility on export
        "blocks": getattr(p, "blocks", None),
        "parent_id": None,  # Parent refs don't carry across exports
        "menu_order": getattr(p, "menu_order", 0) or 0,
        "show_in_menu": bool(getattr(p, "show_in_menu", True)),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/pages/import", response_model=CmsPageOut, status_code=201)
async def import_page(
    data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import a page from exported JSON. On slug collision, append -imported-N."""
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    base_slug = str(data.get("slug") or "").strip()
    title = str(data.get("title") or "").strip()
    if not base_slug or not title:
        raise HTTPException(status_code=400, detail="slug and title are required")

    # Find a non-conflicting slug
    slug = base_slug
    if await _slug_exists(db, slug):
        i = 1
        while True:
            candidate = f"{base_slug}-imported-{i}"
            if not await _slug_exists(db, candidate):
                slug = candidate
                break
            i += 1
            if i > 1000:
                raise HTTPException(status_code=409, detail="Cannot determine unique slug")

    now = datetime.now(timezone.utc)
    p = CmsPage(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        slug=slug,
        title=title,
        description=data.get("description"),
        content_html=str(data.get("content_html") or ""),
        content_mode=str(data.get("content_mode") or "html"),
        layout=str(data.get("layout") or "default"),
        meta_title=data.get("meta_title"),
        meta_description=data.get("meta_description"),
        og_image=data.get("og_image"),
        visibility="private",
        published=False,
        blocks=data.get("blocks") if isinstance(data.get("blocks"), list) else None,
        menu_order=int(data.get("menu_order") or 0),
        show_in_menu=bool(data.get("show_in_menu", True)),
        created_at=now,
        updated_at=now,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


# ── Publishing workflow: schedule / archive ───────────────────────────────

@router.post("/pages/{page_id}/schedule", response_model=CmsPageOut)
async def schedule_page(
    page_id: int,
    data: CmsPageScheduleIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Schedule a page to be published automatically at a given time."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    when = data.published_at
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="scheduled time must be in the future")
    p.status = "scheduled"
    p.scheduled_at = when
    p.published = False
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.post("/pages/{page_id}/archive", response_model=CmsPageOut)
async def archive_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Archive a page (hidden but preserved)."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.status = "archived"
    p.published = False
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.post("/pages/{page_id}/unarchive", response_model=CmsPageOut)
async def unarchive_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore an archived page to draft status."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    p.status = "draft"
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


@router.get("/pages/{page_id}/stats")
async def get_page_stats(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return simple analytics for a page: view count, last viewed timestamp."""
    p = await _get_page_or_404(page_id, current_user.id, db)
    return {
        "id": p.id,
        "view_count": int(getattr(p, "view_count", 0) or 0),
        "last_viewed_at": getattr(p, "last_viewed_at", None),
        "status": getattr(p, "status", "draft"),
        "scheduled_at": getattr(p, "scheduled_at", None),
    }
