"""Session management — list and revoke active sessions."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.system_events import emit_system_event
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth/sessions", tags=["Sessions"])


class SessionOut(BaseModel):
    id: int
    user_agent: str | None
    ip_address: str | None
    created_at: str
    expires_at: str
    is_current: bool


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all active (non-revoked, non-expired) sessions for the current user."""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.created_at.desc())
    )
    tokens = list(res.scalars().all())

    # Determine "current" session by matching IP + UA from the request
    req_ip = request.client.host if request.client else None
    req_ua = request.headers.get("user-agent", "")

    return [
        SessionOut(
            id=t.id,
            user_agent=t.user_agent,
            ip_address=t.ip_address,
            created_at=t.created_at.isoformat(),
            expires_at=t.expires_at.isoformat(),
            is_current=(t.ip_address == req_ip and t.user_agent == req_ua[:512] if req_ua else False),
        )
        for t in tokens
    ]


@router.delete("/{session_id}", status_code=204)
async def revoke_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revoke a specific session."""
    rt = await db.get(RefreshToken, session_id)
    if not rt or rt.user_id != user.id:
        raise HTTPException(status_code=404, detail="session not found")

    rt.revoked = True
    await emit_system_event(db, "session.revoked", {
        "user_id": user.id,
        "session_id": session_id,
    })
    await db.commit()


@router.delete("", status_code=204)
async def revoke_all_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Revoke all sessions except the current one (matched by IP + UA)."""
    req_ip = request.client.host if request.client else None
    req_ua = (request.headers.get("user-agent") or "")[:512]

    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > now,
        )
    )
    tokens = list(res.scalars().all())
    revoked = 0
    for t in tokens:
        if t.ip_address == req_ip and t.user_agent == req_ua:
            continue  # keep current session
        t.revoked = True
        revoked += 1

    if revoked:
        await emit_system_event(db, "session.revoked_all", {
            "user_id": user.id,
            "revoked_count": revoked,
        })
        await db.commit()
