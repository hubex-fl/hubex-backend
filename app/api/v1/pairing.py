# app/api/v1/pairing.py

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi import APIRouter, Depends, Body, Query, Request
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_rate_limit import FixedWindowLimiter
from app.api.v1.error_utils import raise_api_error
from app.core.security import hash_device_token
from app.db.models.device import Device
from app.db.models.pairing import PairingSession, DeviceToken
from app.db.models.tasks import Task
from app.db.models.audit import AuditV1Entry

# Canonical pairing routes live under /api/v1/devices/pairing
router = APIRouter(prefix="/devices/pairing", tags=["pairing"])
legacy_router = APIRouter(prefix="/pairing", tags=["pairing"])


PAIRING_TTL_MINUTES = 10
PAIRING_HELLO_LIMIT = 10
PAIRING_HELLO_WINDOW_SECONDS = 60
_pairing_hello_limiter = FixedWindowLimiter()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _gen_pairing_code() -> str:
    # simple, user-friendly (kein O/0, I/1 etc.)
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _gen_device_token_plain() -> str:
    # ausreichend stark, URL-safe
    return secrets.token_urlsafe(32)


def _hash_token(token_plain: str) -> str:
    return hash_device_token(token_plain)


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _pairing_hello_rate_limit(request: Request, device_uid: str) -> None:
    key = f"{device_uid}:{_client_ip(request)}"
    ok, retry_after = _pairing_hello_limiter.allow(
        key, PAIRING_HELLO_LIMIT, PAIRING_HELLO_WINDOW_SECONDS
    )
    if not ok:
        raise_api_error(
            429,
            "PAIRING_RATE_LIMITED",
            "pairing hello rate limited",
            meta={"retry_after": max(1, retry_after)},
        )

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


class PairingHelloIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=128)
    firmware_version: str | None = None
    capabilities: dict | None = None


class PairingHelloOut(BaseModel):
    claimed: bool
    pairing_active: bool
    pairing_code: str | None = None
    expires_at: datetime | None = None
    ttl_seconds: int | None = None


class PairingStatusOut(BaseModel):
    pairing_code: str
    device_uid: str
    claimed: bool
    claimed_at: datetime | None = None
    expires_at: datetime
    ttl_seconds: int


class PairingUserClaimIn(BaseModel):
    pairing_code: str = Field(
        min_length=4,
        max_length=32,
        validation_alias=AliasChoices("pairing_code", "pairingCode"),
    )
    device_uid: str | None = Field(
        default=None,
        validation_alias=AliasChoices("device_uid", "deviceUid"),
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class PairingUserClaimOut(BaseModel):
    pairing_code: str
    device_uid: str
    claimed_at: datetime


@legacy_router.post("/hello", response_model=PairingHelloOut, deprecated=True)
@router.post("/hello", response_model=PairingHelloOut)
async def pairing_hello(
    request: Request,
    data: PairingHelloIn = Body(...),
    db: AsyncSession = Depends(get_db),
):
    if request is not None:
        _pairing_hello_rate_limit(request, data.device_uid)

    res = await db.execute(select(Device).where(Device.device_uid == data.device_uid))
    device = res.scalar_one_or_none()

    now = _now_utc()

    if device is None:
        device = Device(
            device_uid=data.device_uid,
            firmware_version=data.firmware_version,
            capabilities=data.capabilities,
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.firmware_version = data.firmware_version
        device.capabilities = data.capabilities
        device.last_seen_at = now

    device.is_claimed = device.owner_user_id is not None
    await db.commit()
    await db.refresh(device)

    claimed = device.owner_user_id is not None or device.is_claimed
    if claimed:
        await db.execute(
            update(PairingSession)
            .where(
                PairingSession.device_uid == device.device_uid,
                PairingSession.is_used.is_(False),
            )
            .values(is_used=True)
        )
        await db.commit()
        return PairingHelloOut(
            claimed=True,
            pairing_active=False,
            pairing_code=None,
            expires_at=None,
            ttl_seconds=None,
        )

    res = await db.execute(
        select(PairingSession)
        .where(
            PairingSession.device_uid == device.device_uid,
            PairingSession.is_used.is_(False),
            PairingSession.expires_at > now,
        )
        .order_by(PairingSession.expires_at.desc())
    )
    existing = res.scalar_one_or_none()

    if existing is None:
        await db.execute(
            update(PairingSession)
            .where(
                PairingSession.device_uid == device.device_uid,
                PairingSession.is_used.is_(False),
            )
            .values(is_used=True)
        )
        code = _gen_pairing_code()
        expires_at = now + timedelta(minutes=PAIRING_TTL_MINUTES)
        session = PairingSession(
            device_uid=device.device_uid,
            pairing_code=code,
            expires_at=expires_at,
            is_used=False,
            user_id=None,
            claimed_at=None,
        )
        db.add(session)
        await db.commit()
        pairing_code = code
    else:
        pairing_code = existing.pairing_code
        expires_at = _ensure_utc(existing.expires_at)

    ttl_seconds = max(0, int((expires_at - now).total_seconds()))
    return PairingHelloOut(
        claimed=False,
        pairing_active=True,
        pairing_code=pairing_code,
        expires_at=expires_at,
        ttl_seconds=ttl_seconds,
    )


@legacy_router.post("/start", response_model=PairingStartOut, deprecated=True)
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
        expires_at = _ensure_utc(existing.expires_at)
        ttl_seconds = max(0, int((expires_at - now).total_seconds()))
        raise_api_error(
            409,
            "PAIRING_ALREADY_ACTIVE",
            "pairing already active",
            meta={"expires_at": expires_at.isoformat(), "ttl_seconds": ttl_seconds},
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

    await db.execute(
        update(PairingSession)
        .where(
            PairingSession.device_uid == device.device_uid,
            PairingSession.is_used.is_(False),
        )
        .values(is_used=True)
    )

    # neue Session erzeugen (alte Sessions invalidieren)
    code = _gen_pairing_code()
    expires_at = now + timedelta(minutes=PAIRING_TTL_MINUTES)

    session = PairingSession(
        device_uid=device.device_uid,
        pairing_code=code,
        expires_at=expires_at,
        is_used=False,
        user_id=current_user.id,
        claimed_at=now,
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


@legacy_router.post("/claim", response_model=PairingUserClaimOut, deprecated=True)
@router.post("/claim", response_model=PairingUserClaimOut)
async def claim_pairing(
    data: PairingUserClaimIn = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    User -> Backend:
    - binds a pairing_code to the current user (claim)
    """
    now = _now_utc()
    res = await db.execute(
        select(PairingSession).where(PairingSession.pairing_code == data.pairing_code)
    )
    ps = res.scalar_one_or_none()
    if ps is None:
        raise_api_error(404, "PAIRING_CODE_NOT_FOUND", "pairing code not found")
    if _ensure_utc(ps.expires_at) <= now:
        raise_api_error(410, "PAIRING_CODE_EXPIRED", "pairing code expired")
    if ps.is_used:
        res = await db.execute(select(Device).where(Device.device_uid == ps.device_uid))
        device = res.scalar_one_or_none()
        if device and device.owner_user_id == current_user.id:
            return PairingUserClaimOut(
                pairing_code=ps.pairing_code,
                device_uid=ps.device_uid,
                claimed_at=ps.claimed_at,
            )
        raise_api_error(403, "PAIRING_CODE_ALREADY_CLAIMED", "pairing code already claimed")
    if data.device_uid and ps.device_uid != data.device_uid:
        raise_api_error(409, "PAIRING_CODE_DEVICE_MISMATCH", "pairing code device mismatch")
    if ps.user_id is not None and ps.user_id != current_user.id:
        raise_api_error(403, "PAIRING_CODE_ALREADY_CLAIMED", "pairing code already claimed")

    res = await db.execute(select(Device).where(Device.device_uid == ps.device_uid))
    device = res.scalar_one_or_none()
    if device is None:
        raise_api_error(404, "DEVICE_UNKNOWN_UID", "Unknown device UID")
    if device.owner_user_id is not None and device.owner_user_id != current_user.id:
        raise_api_error(403, "DEVICE_ALREADY_CLAIMED", "device already claimed")

    ps.user_id = current_user.id
    ps.claimed_at = now
    db.add(
        AuditV1Entry(
            actor_type="user",
            actor_id=str(current_user.id),
            action="device.claim",
            resource=device.device_uid,
            audit_metadata={
                "device_uid": device.device_uid,
                "device_id": device.id,
                "pairing_code_hash": hashlib.sha256(data.pairing_code.encode("utf-8")).hexdigest(),
            },
            trace_id=None,
        )
    )
    await db.commit()

    return PairingUserClaimOut(
        pairing_code=ps.pairing_code,
        device_uid=ps.device_uid,
        claimed_at=ps.claimed_at,
    )


@legacy_router.post("/confirm", response_model=PairingClaimOut, deprecated=True)
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

    try:
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
            if _ensure_utc(ps.expires_at) <= now:
                raise_api_error(410, "PAIRING_CODE_EXPIRED", "pairing code expired")
            if ps.user_id is None:
                raise_api_error(409, "PAIRING_CODE_NOT_CLAIMED", "pairing code not claimed")

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
            await db.execute(
                update(PairingSession)
                .where(
                    PairingSession.device_uid == device.device_uid,
                    PairingSession.is_used.is_(False),
                )
                .values(is_used=True)
            )

            # Device Token (nur einmal als Klartext)
            token_plain = _gen_device_token_plain()
            token_hash = _hash_token(token_plain)
            db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    res = await db.execute(select(Device).where(Device.id == device.id))
    persisted = res.scalar_one_or_none()
    if (
        persisted is None
        or persisted.owner_user_id != ps.user_id
        or not persisted.is_claimed
    ):
        raise_api_error(
            500,
            "PAIRING_CLAIM_NOT_PERSISTED",
            "pairing claim did not persist",
        )

    return PairingClaimOut(
        device_id=persisted.id,
        owner_user_id=persisted.owner_user_id,
        device_uid=persisted.device_uid,
        device_token=token_plain,
        claimed_at=now,
    )


@legacy_router.get("/status", response_model=PairingStatusOut, deprecated=True)
@router.get("/status", response_model=PairingStatusOut)
async def pairing_status(
    pairing_code: str = Query(..., alias="pairingCode"),
    db: AsyncSession = Depends(get_db),
):
    """
    Read-only status for a pairing_code.
    - claimed=true when code has been used/claimed by a user
    """
    now = _now_utc()
    res = await db.execute(
        select(PairingSession).where(PairingSession.pairing_code == pairing_code)
    )
    ps = res.scalar_one_or_none()
    if ps is None:
        raise_api_error(404, "PAIRING_CODE_NOT_FOUND", "pairing code not found")
    if _ensure_utc(ps.expires_at) <= now:
        raise_api_error(410, "PAIRING_CODE_EXPIRED", "pairing code expired")

    expires_at = _ensure_utc(ps.expires_at)
    ttl_seconds = max(0, int((expires_at - now).total_seconds()))
    claimed = bool(ps.claimed_at) or bool(ps.is_used)
    return PairingStatusOut(
        pairing_code=ps.pairing_code,
        device_uid=ps.device_uid,
        claimed=claimed,
        claimed_at=ps.claimed_at,
        expires_at=expires_at,
        ttl_seconds=ttl_seconds,
    )
