import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_org import get_jwt_user_id
from app.core.security import (
    AuthTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.capabilities import validate_caps
from app.core.system_events import emit_system_event
from app.db.models.orgs import Organization, OrganizationUser, PLAN_DEFAULTS
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth")

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}$")


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SwitchOrgIn(BaseModel):
    org_id: int


async def _find_user_org(db: AsyncSession, user_id: int) -> int | None:
    """Return the org_id if user belongs to exactly one org, else None."""
    res = await db.execute(
        select(OrganizationUser).where(OrganizationUser.user_id == user_id)
    )
    memberships = list(res.scalars().all())
    if len(memberships) == 1:
        return memberships[0].org_id
    return None


def _default_slug(email: str, user_id: int) -> str:
    """Generate a unique default org slug from email + user ID."""
    local = email.split("@")[0].lower()
    local = re.sub(r"[^a-z0-9\-]", "-", local)
    local = re.sub(r"-+", "-", local).strip("-") or "org"
    slug = f"{local[:48]}-{user_id}"
    return slug


@router.post("/register", response_model=TokenOut)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="email already registered")

    user = User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    await db.flush()

    # Create default organization for new user
    now = datetime.now(timezone.utc)
    slug = _default_slug(data.email, user.id)
    limits = PLAN_DEFAULTS["free"]
    org = Organization(
        name=f"{data.email}'s Org",
        slug=slug,
        plan="free",
        max_devices=limits["max_devices"],
        max_users=limits["max_users"],
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    await db.flush()

    membership = OrganizationUser(
        org_id=org.id,
        user_id=user.id,
        role="owner",
        invited_at=now,
        joined_at=now,
    )
    db.add(membership)
    await emit_system_event(db, "org.created", {
        "org_id": org.id,
        "slug": org.slug,
        "creator_user_id": user.id,
    })
    await db.commit()

    return TokenOut(
        access_token=create_access_token(str(user.id), org_id=org.id)
    )


@router.post("/login", response_model=TokenOut)
async def login(
    data: RegisterIn,
    db: AsyncSession = Depends(get_db),
    access_token_expire_seconds: int | None = Header(default=None, alias="X-Access-Token-Expire-Seconds"),
):
    res = await db.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    caps = user.caps or []
    unknown = validate_caps(caps)
    if unknown:
        logger.warning("auth login: dropping unknown caps: %s", unknown)
        caps = [cap for cap in caps if cap not in unknown]

    org_id = await _find_user_org(db, user.id)

    return TokenOut(
        access_token=create_access_token(
            str(user.id),
            access_token_expire_seconds,
            caps=caps,
            org_id=org_id,
        )
    )


@router.post("/switch-org", response_model=TokenOut)
async def switch_org(
    data: SwitchOrgIn,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")

    # Verify user is a member of the requested org
    res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == data.org_id,
            OrganizationUser.user_id == user_id,
        )
    )
    membership = res.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="not a member of this organization")

    # Fetch user caps
    user = await db.get(User, user_id)
    caps = (user.caps or []) if user else []
    unknown = validate_caps(caps)
    if unknown:
        caps = [cap for cap in caps if cap not in unknown]

    return TokenOut(
        access_token=create_access_token(str(user_id), caps=caps, org_id=data.org_id)
    )
