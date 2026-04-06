import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Request
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
from app.core.capabilities import validate_caps, resolve_caps_for_role
from app.core.system_events import emit_system_event
from app.db.models.orgs import Organization, OrganizationUser, PLAN_DEFAULTS
from app.db.models.user import User
from app.db.models.refresh_token import RefreshToken
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth")

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}$")

# Brute-force constants
_BF_MAX_ATTEMPTS = 5
_BF_LOCKOUT_SECONDS = 15 * 60  # 15 minutes
_BF_WINDOW_SECONDS = 15 * 60


def _get_redis():
    try:
        from app.core.redis_client import get_redis
        return get_redis()
    except Exception:
        return None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class SwitchOrgIn(BaseModel):
    org_id: int


class RefreshIn(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Brute-force helpers (Redis)
# ---------------------------------------------------------------------------

async def _check_brute_force(ip: str) -> None:
    """Raise 429 if IP is locked out."""
    redis = _get_redis()
    if redis is None:
        return
    try:
        lock_key = f"hubex:bf:lock:{ip}"
        locked = await redis.get(lock_key)
        if locked:
            ttl = await redis.ttl(lock_key)
            raise HTTPException(
                status_code=429,
                detail="account_locked",
                headers={"Retry-After": str(max(1, ttl))},
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("brute_force check error: %s", exc)


async def _record_failed_login(ip: str) -> None:
    """Increment failed-login counter; lock out IP after _BF_MAX_ATTEMPTS."""
    redis = _get_redis()
    if redis is None:
        return
    try:
        counter_key = f"hubex:bf:count:{ip}"
        count = await redis.incr(counter_key)
        await redis.expire(counter_key, _BF_WINDOW_SECONDS)
        if count >= _BF_MAX_ATTEMPTS:
            lock_key = f"hubex:bf:lock:{ip}"
            await redis.setex(lock_key, _BF_LOCKOUT_SECONDS, "1")
            await redis.delete(counter_key)
            logger.warning("brute_force: IP %s locked out after %d failures", ip, count)
    except Exception as exc:
        logger.warning("brute_force record error: %s", exc)


async def _clear_brute_force(ip: str) -> None:
    """Clear counters on successful login."""
    redis = _get_redis()
    if redis is None:
        return
    try:
        await redis.delete(f"hubex:bf:count:{ip}", f"hubex:bf:lock:{ip}")
    except Exception:
        pass


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# Refresh token helpers
# ---------------------------------------------------------------------------

def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _create_refresh_token(
    db: AsyncSession,
    user_id: int,
    request: Request | None = None,
) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_exp_days
    )
    user_agent = None
    ip_address = None
    if request:
        user_agent = (request.headers.get("user-agent") or "")[:512]
        ip_address = _client_ip(request)

    db.add(RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    ))
    await db.flush()
    return raw


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

async def _find_user_org(db: AsyncSession, user_id: int) -> int | None:
    """Return the org_id if user belongs to exactly one org, else None."""
    res = await db.execute(
        select(OrganizationUser).where(OrganizationUser.user_id == user_id)
    )
    memberships = list(res.scalars().all())
    if len(memberships) == 1:
        return memberships[0].org_id
    return None


async def _resolve_user_caps(
    db: AsyncSession, user: "User", org_id: int | None
) -> tuple[list[str], str | None]:
    """Resolve effective capabilities from org role + user.caps.

    Returns (caps, role). Looks up the user's OrganizationUser.role
    for the given org_id, maps it to capabilities via ROLE_CAPS,
    and unions with user.caps. Falls back to user.caps alone if no
    org membership found.
    """
    role: str | None = None
    if org_id is not None:
        res = await db.execute(
            select(OrganizationUser).where(
                OrganizationUser.org_id == org_id,
                OrganizationUser.user_id == user.id,
            )
        )
        membership = res.scalar_one_or_none()
        if membership:
            role = membership.role

    user_caps = user.caps or []

    if role:
        caps = resolve_caps_for_role(role, user_caps=user_caps)
    else:
        # No org membership — fall back to legacy user.caps
        caps = [cap for cap in user_caps if cap not in validate_caps(user_caps)]

    return caps, role


def _default_slug(email: str, user_id: int) -> str:
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

    refresh_raw = await _create_refresh_token(db, user.id)
    await db.commit()

    return TokenOut(
        access_token=create_access_token(str(user.id), org_id=org.id),
        refresh_token=refresh_raw,
    )


@router.post("/login")
async def login(
    request: Request,
    data: RegisterIn,
    db: AsyncSession = Depends(get_db),
    access_token_expire_seconds: int | None = Header(
        default=None, alias="X-Access-Token-Expire-Seconds"
    ),
):
    ip = _client_ip(request)
    await _check_brute_force(ip)

    res = await db.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        await _record_failed_login(ip)
        raise HTTPException(status_code=401, detail="invalid credentials")

    await _clear_brute_force(ip)

    # MFA challenge: if user has MFA enabled, return challenge token
    if user.mfa_enabled:
        mfa_token = create_access_token(
            str(user.id),
            expires_seconds=300,  # 5 minutes
            caps=[],
        )
        # Encode purpose into a separate short-lived token
        from app.core.security import jwt, SECRET_KEY, ALGORITHM, ISSUER
        from uuid import uuid4
        import time as _time
        now = _time.time()
        mfa_payload = {
            "sub": str(user.id),
            "iss": ISSUER,
            "iat": int(now),
            "exp": int(now + 300),
            "jti": uuid4().hex,
            "purpose": "mfa_challenge",
        }
        mfa_token = jwt.encode(mfa_payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"mfa_required": True, "mfa_token": mfa_token, "methods": ["totp"]}

    org_id = await _find_user_org(db, user.id)
    caps, role = await _resolve_user_caps(db, user, org_id)

    refresh_raw = await _create_refresh_token(db, user.id, request=request)
    await db.commit()

    return TokenOut(
        access_token=create_access_token(
            str(user.id),
            access_token_expire_seconds,
            caps=caps,
            org_id=org_id,
            role=role,
        ),
        refresh_token=refresh_raw,
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh_token_endpoint(
    data: RefreshIn,
    db: AsyncSession = Depends(get_db),
):
    token_hash = _hash_refresh_token(data.refresh_token)
    res = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if (
        rt is None
        or rt.revoked
        or rt.expires_at.replace(tzinfo=timezone.utc) < now
    ):
        raise HTTPException(status_code=401, detail="invalid or expired refresh token")

    # Rotate: revoke old token, issue new one
    rt.revoked = True
    await db.flush()

    user = await db.get(User, rt.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    org_id = await _find_user_org(db, user.id)
    caps, role = await _resolve_user_caps(db, user, org_id)

    new_refresh_raw = await _create_refresh_token(db, user.id)
    await db.commit()

    return TokenOut(
        access_token=create_access_token(str(user.id), caps=caps, org_id=org_id, role=role),
        refresh_token=new_refresh_raw,
    )


@router.post("/switch-org", response_model=TokenOut)
async def switch_org(
    data: SwitchOrgIn,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    if user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")

    res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == data.org_id,
            OrganizationUser.user_id == user_id,
        )
    )
    membership = res.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="not a member of this organization")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    caps, role = await _resolve_user_caps(db, user, data.org_id)

    return TokenOut(
        access_token=create_access_token(str(user_id), caps=caps, org_id=data.org_id, role=role)
    )


@router.get("/roles")
async def list_roles():
    """Return available built-in roles with their capability counts."""
    from app.core.capabilities import ROLE_CAPS
    return [
        {"role": role, "caps_count": len(caps), "is_builtin": True}
        for role, caps in ROLE_CAPS.items()
        if role != "member"  # hide alias
    ]
