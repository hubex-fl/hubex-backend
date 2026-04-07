"""MFA (TOTP) setup and verification endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_jwt_user_id
from app.core.mfa import (
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp,
    generate_recovery_codes,
    hash_recovery_code,
)
from app.core.security import create_access_token, decode_access_token
from app.core.system_events import emit_system_event
from app.db.models.mfa import UserTotpSecret
from app.db.models.user import User
from app.db.models.refresh_token import RefreshToken

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/auth/mfa", tags=["MFA"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class TotpSetupOut(BaseModel):
    secret: str
    provisioning_uri: str


class TotpConfirmIn(BaseModel):
    code: str


class TotpConfirmOut(BaseModel):
    recovery_codes: list[str]


class MfaStatusOut(BaseModel):
    totp_enabled: bool


class MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str


class MfaDisableIn(BaseModel):
    code: str


# ── Setup Flow ───────────────────────────────────────────────────────────────

@router.post("/totp/setup", response_model=TotpSetupOut)
async def totp_setup(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a TOTP secret. Returns the secret + provisioning URI for QR."""
    # Check if already has TOTP
    res = await db.execute(
        select(UserTotpSecret).where(UserTotpSecret.user_id == user.id)
    )
    existing = res.scalar_one_or_none()
    if existing and existing.confirmed:
        raise HTTPException(status_code=409, detail="TOTP already enabled. Disable first.")

    secret = generate_totp_secret()
    uri = get_provisioning_uri(secret, user.email)

    # Upsert: delete unconfirmed, create new
    if existing:
        await db.delete(existing)
        await db.flush()

    db.add(UserTotpSecret(
        user_id=user.id,
        secret_enc=secret,  # TODO: encrypt at rest with AES-GCM
        confirmed=False,
    ))
    await db.commit()

    return TotpSetupOut(secret=secret, provisioning_uri=uri)


@router.post("/totp/confirm", response_model=TotpConfirmOut)
async def totp_confirm(
    data: TotpConfirmIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Confirm TOTP setup by verifying the first code. Returns recovery codes."""
    res = await db.execute(
        select(UserTotpSecret).where(UserTotpSecret.user_id == user.id)
    )
    totp = res.scalar_one_or_none()
    if not totp:
        raise HTTPException(status_code=404, detail="no TOTP setup in progress")
    if totp.confirmed:
        raise HTTPException(status_code=409, detail="TOTP already confirmed")

    if not verify_totp(totp.secret_enc, data.code):
        raise HTTPException(status_code=400, detail="invalid code")

    # Generate recovery codes
    codes = generate_recovery_codes()
    totp.recovery_codes_hash = [hash_recovery_code(c) for c in codes]
    totp.confirmed = True

    # Enable MFA on user
    user.mfa_enabled = True

    await emit_system_event(db, "mfa.totp.enabled", {"user_id": user.id})
    await db.commit()

    return TotpConfirmOut(recovery_codes=codes)


@router.delete("/totp", status_code=204)
async def totp_disable(
    data: MfaDisableIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Disable TOTP — requires a valid code."""
    res = await db.execute(
        select(UserTotpSecret).where(UserTotpSecret.user_id == user.id)
    )
    totp = res.scalar_one_or_none()
    if not totp or not totp.confirmed:
        raise HTTPException(status_code=404, detail="TOTP not enabled")

    if not verify_totp(totp.secret_enc, data.code):
        raise HTTPException(status_code=400, detail="invalid code")

    await db.delete(totp)
    user.mfa_enabled = False

    await emit_system_event(db, "mfa.totp.disabled", {"user_id": user.id})
    await db.commit()


@router.get("/status", response_model=MfaStatusOut)
async def mfa_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return MfaStatusOut(totp_enabled=user.mfa_enabled)


# ── Verification (called during login) ──────────────────────────────────────

@router.post("/verify")
async def mfa_verify(
    data: MfaVerifyIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify MFA code during login. Accepts mfa_token + code, returns real tokens."""
    from app.api.v1.auth import _resolve_user_caps, _create_refresh_token, _find_user_org, TokenOut

    # Decode the MFA challenge token
    try:
        payload = decode_access_token(data.mfa_token)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired MFA token")

    if payload.get("purpose") != "mfa_challenge":
        raise HTTPException(status_code=401, detail="invalid token purpose")

    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    # Verify TOTP code
    res = await db.execute(
        select(UserTotpSecret).where(
            UserTotpSecret.user_id == user_id,
            UserTotpSecret.confirmed == True,
        )
    )
    totp = res.scalar_one_or_none()
    if not totp:
        raise HTTPException(status_code=400, detail="MFA not configured")

    valid = verify_totp(totp.secret_enc, data.code)

    # Check recovery codes if TOTP fails
    if not valid and totp.recovery_codes_hash:
        code_hash = hash_recovery_code(data.code)
        if code_hash in totp.recovery_codes_hash:
            valid = True
            # Remove used recovery code
            totp.recovery_codes_hash = [h for h in totp.recovery_codes_hash if h != code_hash]

    if not valid:
        raise HTTPException(status_code=400, detail="invalid code")

    # Issue real tokens
    org_id = await _find_user_org(db, user.id)
    caps, role = await _resolve_user_caps(db, user, org_id)
    refresh_raw = await _create_refresh_token(db, user.id, request=request)
    await db.commit()

    return TokenOut(
        access_token=create_access_token(
            str(user.id), caps=caps, org_id=org_id, role=role,
        ),
        refresh_token=refresh_raw,
    )
