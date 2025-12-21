# app/api/v1/pairing.py

from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.v1.error_utils import raise_api_error
from app.db.models.device import Device
from app.db.models.pairing import PairingSession, DeviceToken
from app.db.models.tasks import Task

# Canonical pairing routes live under /api/v1/pairing
router = APIRouter(prefix="/pairing", tags=["pairing"])


PAIRING_TTL_MINUTES = 10


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _gen_pairing_code() -> str:
    # simple, user-friendly (kein O/0, I/1 etc.)
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _gen_device_token_plain() -> str:
    # ausreichend stark, URL-safe
    return secrets.token_urlsafe(32)


def _hash_token(token_plain: str) -> str:
    # für DeviceToken: stabil, schnell, keine bcrypt-72byte-Problematik
    return hashlib.sha256(token_plain.encode("utf-8")).hexdigest()

class PairingStartIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=128)


class PairingStartOut(BaseModel):
    device_uid: str
    pairing_code: str
    expires_at: datetime
    ttl_seconds: int


class PairingClaimIn(BaseModel):
    # Accept camelCase payloads from frontend clients.
    device_uid: str = Field(
        min_length=4,
        max_length=128,
        validation_alias=AliasChoices("device_uid", "deviceUid"),
    )
    pairing_code: str = Field(
        min_length=4,
        max_length=32,
        validation_alias=AliasChoices("pairing_code", "pairingCode"),
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

class PairingClaimOut(BaseModel):
    device_id: int
    owner_user_id: int
    device_uid: str
    device_token: str  # nur EINMAL ausgeben
    claimed_at: datetime


@router.post("/start", response_model=PairingStartOut)
async def start_pairing(
    data: PairingStartIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    User -> Backend:
    - stellt sicher, dass das Device existiert
    - erstellt eine PairingSession mit Ablaufzeit
    """
    res = await db.execute(select(Device).where(Device.device_uid == data.device_uid))
    device = res.scalar_one_or_none()

    if device is None:
        raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
    if device.last_seen_at is None:
        raise_api_error(404, "DEVICE_NOT_PROVISIONED", "device not provisioned")
    if device.owner_user_id is not None or device.is_claimed:
        raise_api_error(409, "DEVICE_ALREADY_CLAIMED", "device already claimed")

    now = _now_utc()
    res = await db.execute(
        select(PairingSession).where(
            PairingSession.device_uid == device.device_uid,
            PairingSession.is_used.is_(False),
            PairingSession.expires_at > now,
        )
    )
    existing = res.scalar_one_or_none()
    if existing is not None:
        ttl_seconds = max(0, int((existing.expires_at - now).total_seconds()))
        raise_api_error(
            409,
            "PAIRING_ALREADY_ACTIVE",
            "pairing already active",
            meta={"expires_at": existing.expires_at.isoformat(), "ttl_seconds": ttl_seconds},
        )
    res = await db.execute(
        select(Task.id).where(
            Task.client_id == device.id,
            Task.lease_expires_at.is_not(None),
            Task.lease_expires_at > now,
            Task.lease_token.is_not(None),
            Task.status == "in_flight",
        )
    )
    if res.scalar_one_or_none() is not None:
        raise_api_error(409, "DEVICE_BUSY", "device busy")

    # neue Session erzeugen (alte Sessions lassen wir erstmal in Ruhe)
    code = _gen_pairing_code()
    expires_at = now + timedelta(minutes=PAIRING_TTL_MINUTES)

    session = PairingSession(
        device_uid=device.device_uid,
        pairing_code=code,
        expires_at=expires_at,
        is_used=False,
        user_id=current_user.id,
    )
    db.add(session)
    await db.commit()

    ttl_seconds = max(0, int((expires_at - now).total_seconds()))
    return PairingStartOut(
        device_uid=device.device_uid,
        pairing_code=code,
        expires_at=expires_at,
        ttl_seconds=ttl_seconds,
    )


@router.post("/confirm", response_model=PairingClaimOut)
async def confirm_pairing(
    data: PairingClaimIn = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Device -> Backend (ohne JWT):
    - validiert pairing_code (existiert, nicht used, nicht expired)
    - setzt device.owner_user_id + is_claimed
    - erstellt DeviceToken (plaintext nur einmal zurückgeben)
    """
    token_plain: str | None = None
    now = _now_utc()

    async with db.begin_nested():
        res = await db.execute(
            select(PairingSession)
            .where(
                PairingSession.device_uid == data.device_uid,
                PairingSession.pairing_code == data.pairing_code,
            )
            .with_for_update()
        )
        ps = res.scalar_one_or_none()
        if ps is None:
            raise_api_error(404, "PAIRING_CODE_NOT_FOUND", "pairing code not found")

        if ps.is_used:
            raise_api_error(
                409, "PAIRING_CODE_ALREADY_USED", "pairing code already used"
            )
        if ps.expires_at <= now:
            raise_api_error(410, "PAIRING_CODE_EXPIRED", "pairing code expired")

        res = await db.execute(
            select(Device)
            .where(Device.device_uid == ps.device_uid)
            .with_for_update()
        )
        device = res.scalar_one_or_none()
        if device is None:
            raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
        if device.last_seen_at is None:
            raise_api_error(404, "DEVICE_NOT_PROVISIONED", "device not provisioned")
        if device.owner_user_id is not None or device.is_claimed:
            raise_api_error(409, "DEVICE_ALREADY_CLAIMED", "device already claimed")

        res = await db.execute(
            select(Task.id).where(
                Task.client_id == device.id,
                Task.lease_expires_at.is_not(None),
                Task.lease_expires_at > now,
                Task.lease_token.is_not(None),
                Task.status == "in_flight",
            )
        )
        if res.scalar_one_or_none() is not None:
            raise_api_error(409, "DEVICE_BUSY", "device busy")

        res = await db.execute(
            select(func.count())
            .select_from(DeviceToken)
            .where(
                DeviceToken.device_id == device.id,
                DeviceToken.is_active.is_(True),
            )
        )
        active_tokens = res.scalar_one()
        if active_tokens > 0:
            raise_api_error(409, "DEVICE_ALREADY_CLAIMED", "device already claimed")

        # Claim
        device.owner_user_id = ps.user_id
        device.is_claimed = True
        ps.is_used = True

        # Device Token (nur einmal als Klartext)
        token_plain = _gen_device_token_plain()
        token_hash = _hash_token(token_plain)
        db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))
    await db.refresh(device)

    return PairingClaimOut(
        device_id=device.id,
        owner_user_id=device.owner_user_id,
        device_uid=device.device_uid,
        device_token=token_plain,
        claimed_at=now,
    )
