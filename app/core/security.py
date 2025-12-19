from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
ISSUER = os.getenv("JWT_ISSUER", "hubex")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(subject: str, expires_seconds: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    env_seconds = os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS")
    if expires_seconds is None and env_seconds:
        try:
            expires_seconds = int(env_seconds)
        except ValueError:
            expires_seconds = None
    if expires_seconds is None:
        expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expires = now + timedelta(seconds=expires_seconds)
    payload = {
        "sub": subject,
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
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
