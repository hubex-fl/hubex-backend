import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.jwt_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_exp_minutes
ISSUER = settings.jwt_issuer


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(
    subject: str,
    expires_seconds: Optional[int] = None,
    caps: Optional[list[str]] = None,
    org_id: Optional[int] = None,
    role: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires_seconds is None:
        expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expires = now + timedelta(seconds=expires_seconds)
    payload = {
        "sub": subject,
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid4().hex,
    }
    if caps:
        payload["caps"] = caps
    if org_id is not None:
        payload["org_id"] = org_id
    if role:
        payload["role"] = role
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


class AuthTokenError(ValueError):
    pass


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer=ISSUER)
    except ExpiredSignatureError as e:
        raise AuthTokenError("expired token") from e
    except JWTError as e:
        raise AuthTokenError("invalid token") from e


# --- Device token hashing (HMAC-SHA256, keyed by JWT secret) ---

def hash_device_token(token_plain: str) -> str:
    """HMAC-SHA256 keyed hash for device tokens.

    Unlike plain SHA256, this is not brute-forceable without the server secret,
    even if the database is leaked.
    """
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        token_plain.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
