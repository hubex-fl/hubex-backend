import hashlib

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.models.device import Device
from app.db.models.pairing import DeviceToken

bearer = HTTPBearer(auto_error=False)
device_token_header = APIKeyHeader(name="X-Device-Token", auto_error=False)

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="missing bearer token")

    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")

    return user

async def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return user.id

async def get_current_device(
    device_token: str | None = Security(device_token_header),
    db: AsyncSession = Depends(get_db),
) -> Device:
    if not device_token:
        raise HTTPException(status_code=401, detail="missing device token")

    token_hash = hashlib.sha256(device_token.encode("utf-8")).hexdigest()
    res = await db.execute(
        select(Device)
        .join(DeviceToken, DeviceToken.device_id == Device.id)
        .where(DeviceToken.token_hash == token_hash, DeviceToken.is_active.is_(True))
    )
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=401, detail="invalid device token")

    return device
