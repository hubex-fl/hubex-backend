"""Org-scoping dependencies extracted from JWT claims."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


async def get_current_org_id(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> int | None:
    """Extract org_id from JWT. Returns None if absent or token is invalid."""
    if not creds or not creds.credentials:
        return None
    try:
        payload = decode_access_token(creds.credentials)
        org_id = payload.get("org_id")
        return int(org_id) if org_id is not None else None
    except Exception:
        return None


async def get_jwt_user_id(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> int | None:
    """Extract user_id (sub) from JWT. Returns None if absent or invalid."""
    if not creds or not creds.credentials:
        return None
    try:
        payload = decode_access_token(creds.credentials)
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except Exception:
        return None
