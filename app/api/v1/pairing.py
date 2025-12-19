# app/api/v1/pairing.py

from datetime import datetime, timedelta, timezone
import secrets
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.device import Device
from app.core.device_state import DeviceState, derive_device_states
from app.db.models.pairing import PairingSession, DeviceToken

router = APIRouter(prefix="/pairing")


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


class PairingClaimIn(BaseModel):
    device_uid: str = Field(min_length=4, max_length=128)
    pairing_code: str = Field(min_length=4, max_length=32)


class PairingClaimOut(BaseModel):
    device_id: int
    owner_user_id: int
    device_token: str  # nur EINMAL ausgeben


@router.post("/start", response_model=PairingStartOut)
async def start_pairing(
    data: PairingStartIn,
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
        device = Device(device_uid=data.device_uid, is_claimed=False)
        db.add(device)
        await db.commit()
        await db.refresh(device)

    # neue Session erzeugen (alte Sessions lassen wir erstmal in Ruhe)
    code = _gen_pairing_code()
    expires_at = _now_utc() + timedelta(minutes=PAIRING_TTL_MINUTES)

    session = PairingSession(
        device_uid=device.device_uid,
        pairing_code=code,
        expires_at=expires_at,
        is_used=False,
        user_id=current_user.id,
    )
    db.add(session)
    await db.commit()

    return PairingStartOut(
        device_uid=device.device_uid,
        pairing_code=code,
        expires_at=expires_at,
    )


@router.post("/confirm", response_model=PairingClaimOut)
async def confirm_pairing(data: PairingClaimIn, db: AsyncSession = Depends(get_db)):
    """
    Device -> Backend (ohne JWT):
    - validiert pairing_code (existiert, nicht used, nicht expired)
    - setzt device.owner_user_id + is_claimed
    - erstellt DeviceToken (plaintext nur einmal zurückgeben)
    """
    device = None
    token_plain = None

    async with db.begin():
        res = await db.execute(
            select(PairingSession)
            .where(
                PairingSession.device_uid == data.device_uid,
                PairingSession.pairing_code == data.pairing_code,
            )
            .with_for_update()
        )
        session = res.scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=404, detail="pairing code not found")

        now = _now_utc()
        if session.is_used:
            raise HTTPException(status_code=409, detail="pairing code already used")
        if session.expires_at <= now:
            raise HTTPException(status_code=410, detail="pairing code expired")

        res = await db.execute(
            select(Device)
            .where(Device.device_uid == session.device_uid)
            .with_for_update()
        )
        device = res.scalar_one_or_none()
        if device is None:
            raise HTTPException(status_code=404, detail="device not found")

        states = derive_device_states(device, pairing_active=True, now=now)
        if DeviceState.claimed in states:
            raise HTTPException(status_code=409, detail="device already claimed")

        # Claim durchziehen
        device.owner_user_id = session.user_id
        device.is_claimed = True

        session.is_used = True

        # Device Token erstellen (nur einmal plaintext)
        token_plain = _gen_device_token_plain()
        token_hash = _hash_token(token_plain)

        db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))

    await db.refresh(device)

    return PairingClaimOut(
        device_id=device.id,
        owner_user_id=device.owner_user_id,
        device_token=token_plain,
    )
