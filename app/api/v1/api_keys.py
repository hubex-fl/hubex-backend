"""Scoped API Key management endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_jwt_user_id, get_current_org_id
from app.core.api_keys import generate_api_key
from app.core.capabilities import CAPABILITY_REGISTRY
from app.core.system_events import emit_system_event
from app.db.models.api_key import ApiKey
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ApiKeyCreateIn(BaseModel):
    name: str
    caps: list[str]
    expires_in_days: int | None = None


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    caps: list[str]
    expires_at: str | None
    last_used_at: str | None
    revoked: bool
    created_at: str


class ApiKeyCreatedOut(ApiKeyOut):
    key: str  # only returned on creation


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=ApiKeyCreatedOut, status_code=201)
async def create_api_key(
    data: ApiKeyCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    if not data.name.strip():
        raise HTTPException(status_code=422, detail="name is required")

    # Validate caps are known
    unknown = [c for c in data.caps if c not in CAPABILITY_REGISTRY]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown capabilities: {unknown}")

    # Validate caps are subset of user's caps
    user_caps = set(user.caps or [])
    if user_caps:  # if user has explicit caps, enforce subset
        over = [c for c in data.caps if c not in user_caps]
        if over:
            raise HTTPException(status_code=403, detail=f"cannot grant capabilities you don't have: {over}")

    key_plain, key_prefix, key_hash = generate_api_key()

    expires_at = None
    if data.expires_in_days and data.expires_in_days > 0:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    api_key = ApiKey(
        user_id=user.id,
        org_id=org_id,
        name=data.name.strip(),
        key_prefix=key_prefix,
        key_hash=key_hash,
        caps=data.caps,
        expires_at=expires_at,
    )
    db.add(api_key)

    await emit_system_event(db, "apikey.created", {
        "user_id": user.id,
        "name": data.name.strip(),
        "caps_count": len(data.caps),
    })

    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreatedOut(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key=key_plain,
        caps=api_key.caps,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        last_used_at=None,
        revoked=False,
        created_at=api_key.created_at.isoformat(),
    )


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = list(res.scalars().all())
    return [
        ApiKeyOut(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            caps=k.caps or [],
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            revoked=k.revoked,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    api_key = await db.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.revoked = True

    await emit_system_event(db, "apikey.revoked", {
        "user_id": user.id,
        "key_id": key_id,
        "name": api_key.name,
    })

    await db.commit()
