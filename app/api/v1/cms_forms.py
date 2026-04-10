"""CMS Forms API — user-defined web forms with submissions."""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.email import send_email
from app.db.models.cms_form import CmsForm, CmsFormSubmission
from app.db.models.user import User
from app.schemas.cms_form import (
    CmsFormCreate,
    CmsFormOut,
    CmsFormPublicOut,
    CmsFormSubmissionCreate,
    CmsFormSubmissionOut,
    CmsFormSummaryOut,
    CmsFormUpdate,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/cms", tags=["cms-forms"])


# ── Helpers ───────────────────────────────────────────────────────────────


async def _get_form_or_404(form_id: int, user_id: int, db: AsyncSession) -> CmsForm:
    res = await db.execute(
        select(CmsForm).where(CmsForm.id == form_id, CmsForm.owner_id == user_id)
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Form not found")
    return f


async def _slug_exists(db: AsyncSession, slug: str, exclude_id: int | None = None) -> bool:
    stmt = select(CmsForm.id).where(CmsForm.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(CmsForm.id != exclude_id)
    r = await db.execute(stmt)
    return r.scalar_one_or_none() is not None


async def _submission_count(db: AsyncSession, form_id: int) -> int:
    r = await db.execute(
        select(func.count()).select_from(CmsFormSubmission).where(
            CmsFormSubmission.form_id == form_id
        )
    )
    return int(r.scalar_one() or 0)


def _serialize_form(f: CmsForm, count: int) -> dict[str, Any]:
    return {
        "id": f.id,
        "org_id": f.org_id,
        "owner_id": f.owner_id,
        "name": f.name,
        "slug": f.slug,
        "description": f.description,
        "fields": f.fields or [],
        "submit_button_text": f.submit_button_text,
        "success_message": f.success_message,
        "action": f.action,
        "email_to": f.email_to,
        "webhook_url": f.webhook_url,
        "enabled": f.enabled,
        "submission_count": count,
        "created_at": f.created_at,
        "updated_at": f.updated_at,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────


@router.get("/forms", response_model=list[CmsFormSummaryOut])
async def list_forms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(CmsForm)
        .where(CmsForm.owner_id == current_user.id)
        .order_by(desc(CmsForm.updated_at))
    )
    forms = list(res.scalars().all())
    results = []
    for f in forms:
        count = await _submission_count(db, f.id)
        results.append(
            CmsFormSummaryOut(
                id=f.id,
                name=f.name,
                slug=f.slug,
                description=f.description,
                enabled=f.enabled,
                action=f.action,
                submission_count=count,
                updated_at=f.updated_at,
                created_at=f.created_at,
            )
        )
    return results


@router.post("/forms", response_model=CmsFormOut, status_code=201)
async def create_form(
    data: CmsFormCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if await _slug_exists(db, data.slug):
        raise HTTPException(status_code=409, detail="Slug already exists")
    now = datetime.now(timezone.utc)
    f = CmsForm(
        org_id=getattr(current_user, "org_id", None),
        owner_id=current_user.id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        fields=data.fields or [],
        submit_button_text=data.submit_button_text,
        success_message=data.success_message,
        action=data.action,
        email_to=data.email_to,
        webhook_url=data.webhook_url,
        enabled=data.enabled,
        created_at=now,
        updated_at=now,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return CmsFormOut(**_serialize_form(f, 0))


@router.get("/forms/{form_id}", response_model=CmsFormOut)
async def get_form(
    form_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = await _get_form_or_404(form_id, current_user.id, db)
    count = await _submission_count(db, f.id)
    return CmsFormOut(**_serialize_form(f, count))


@router.put("/forms/{form_id}", response_model=CmsFormOut)
async def update_form(
    form_id: int,
    data: CmsFormUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = await _get_form_or_404(form_id, current_user.id, db)
    payload = data.model_dump(exclude_none=True)
    if "slug" in payload and payload["slug"] != f.slug:
        if await _slug_exists(db, payload["slug"], exclude_id=f.id):
            raise HTTPException(status_code=409, detail="Slug already exists")
    for field, value in payload.items():
        setattr(f, field, value)
    f.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(f)
    count = await _submission_count(db, f.id)
    return CmsFormOut(**_serialize_form(f, count))


@router.delete("/forms/{form_id}", status_code=204)
async def delete_form(
    form_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = await _get_form_or_404(form_id, current_user.id, db)
    await db.delete(f)
    await db.commit()


# ── Public submission endpoint ────────────────────────────────────────────


@router.get("/forms/public/{slug}", response_model=CmsFormPublicOut)
async def get_public_form(slug: str, db: AsyncSession = Depends(get_db)):
    """Public form schema — no auth required. Only returns enabled forms."""
    res = await db.execute(
        select(CmsForm).where(CmsForm.slug == slug, CmsForm.enabled.is_(True))
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Form not found")
    return CmsFormPublicOut(
        name=f.name,
        slug=f.slug,
        description=f.description,
        fields=f.fields or [],
        submit_button_text=f.submit_button_text,
        success_message=f.success_message,
    )


@router.post("/forms/public/{slug}/submit")
async def submit_public_form(
    slug: str,
    data: CmsFormSubmissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public submission endpoint — no auth required."""
    res = await db.execute(
        select(CmsForm).where(CmsForm.slug == slug, CmsForm.enabled.is_(True))
    )
    form = res.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # Validate required fields
    fields_def = form.fields or []
    for field_def in fields_def:
        if not isinstance(field_def, dict):
            continue
        if field_def.get("required") and field_def.get("id"):
            fid = field_def["id"]
            val = data.data.get(fid)
            if val is None or val == "" or val == []:
                label = field_def.get("label", fid)
                raise HTTPException(status_code=400, detail=f"Field '{label}' is required")

    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    submission = CmsFormSubmission(
        form_id=form.id,
        data=data.data,
        submitted_at=datetime.now(timezone.utc),
        ip_address=client_host,
        user_agent=user_agent[:500] if user_agent else None,
        read=False,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Action handling
    action = form.action or "store"
    if action in ("email", "both") and form.email_to:
        try:
            rows_html = "".join(
                f"<tr><td style='padding:4px 8px;color:#71717A'>{k}</td>"
                f"<td style='padding:4px 8px;color:#F5F5F5'>{v}</td></tr>"
                for k, v in data.data.items()
            )
            body_html = (
                f"<h2>New submission for form '{form.name}'</h2>"
                f"<table>{rows_html}</table>"
            )
            send_email(
                to=form.email_to,
                subject=f"[HUBEX] New form submission: {form.name}",
                body_html=body_html,
            )
        except Exception as e:
            logger.warning("form submission email failed: %s", e)

    if action in ("webhook", "both") and form.webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    form.webhook_url,
                    json={
                        "form_slug": form.slug,
                        "form_name": form.name,
                        "submission_id": submission.id,
                        "submitted_at": submission.submitted_at.isoformat(),
                        "data": data.data,
                    },
                )
        except Exception as e:
            logger.warning("form submission webhook failed: %s", e)

    return {
        "ok": True,
        "submission_id": submission.id,
        "message": form.success_message,
    }


# ── Submissions ───────────────────────────────────────────────────────────


@router.get("/forms/{form_id}/submissions", response_model=list[CmsFormSubmissionOut])
async def list_submissions(
    form_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_form_or_404(form_id, current_user.id, db)
    res = await db.execute(
        select(CmsFormSubmission)
        .where(CmsFormSubmission.form_id == form_id)
        .order_by(desc(CmsFormSubmission.submitted_at))
    )
    return list(res.scalars().all())


@router.get(
    "/forms/{form_id}/submissions/{submission_id}",
    response_model=CmsFormSubmissionOut,
)
async def get_submission(
    form_id: int,
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_form_or_404(form_id, current_user.id, db)
    res = await db.execute(
        select(CmsFormSubmission).where(
            CmsFormSubmission.id == submission_id,
            CmsFormSubmission.form_id == form_id,
        )
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if not sub.read:
        sub.read = True
        await db.commit()
        await db.refresh(sub)
    return sub


@router.delete(
    "/forms/{form_id}/submissions/{submission_id}", status_code=204
)
async def delete_submission(
    form_id: int,
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_form_or_404(form_id, current_user.id, db)
    res = await db.execute(
        select(CmsFormSubmission).where(
            CmsFormSubmission.id == submission_id,
            CmsFormSubmission.form_id == form_id,
        )
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    await db.delete(sub)
    await db.commit()
