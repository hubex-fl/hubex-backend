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
from app.db.models.cms_page import CmsPage
from app.db.models.device import Device
from app.db.models.user import User
from app.db.models.variables import VariableValue
from app.schemas.cms_page import (
    CmsPageCreate,
    CmsPageOut,
    CmsPagePublicOut,
    CmsPageSummaryOut,
    CmsPageUpdate,
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


@router.post("/pages", response_model=CmsPageOut, status_code=201)
async def create_page(
    data: CmsPageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if await _slug_exists(db, data.slug):
        raise HTTPException(status_code=409, detail="Slug already exists")
    now = datetime.now(timezone.utc)
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
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return CmsPageOut.from_orm_with_pin(p)


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

    rendered = await render_template_vars(p.content_html or "", db, p.owner_id)
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

    rendered = await render_template_vars(p.content_html or "", db, p.owner_id)

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
    for field, value in payload.items():
        setattr(p, field, value)
    if data.published is True and not p.published_at:
        p.published_at = datetime.now(timezone.utc)
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
    rendered = await render_template_vars(p.content_html or "", db, current_user.id)
    return {
        "slug": p.slug,
        "title": p.title,
        "content_html": rendered,
        "layout": p.layout,
        "content_mode": p.content_mode,
    }
