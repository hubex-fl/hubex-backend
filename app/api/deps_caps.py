import logging
from typing import Iterable

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, AuthTokenError
from app.core.token_revoke import is_token_revoked
from app.core.capabilities import (
    enforcement_enabled,
    is_public_route,
    resolve_required_caps,
    validate_caps,
)
from app.api.deps import get_db

logger = logging.getLogger("uvicorn.error")

bearer = HTTPBearer(auto_error=False)
device_token_header = APIKeyHeader(name="X-Device-Token", auto_error=False)

DEVICE_CAPS: set[str] = {"vars.read", "vars.ack", "telemetry.emit"}


def _http_401(detail: dict) -> None:
    raise HTTPException(status_code=401, detail=detail)


def _http_403(detail: dict) -> None:
    raise HTTPException(status_code=403, detail=detail)


def _detail(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _has_required_caps(required: Iterable[str], caps: Iterable[str]) -> bool:
    cap_set = set(caps)
    return all(cap in cap_set for cap in required)


async def capability_guard(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    device_token: str | None = Security(device_token_header),
    db: AsyncSession = Depends(get_db),
) -> None:
    method = request.method.upper()
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)

    required = resolve_required_caps(method, path)
    enforce = enforcement_enabled()

    if required is None:
        if enforce:
            _http_403(_detail("CAP_MAPPING_MISSING", "capability mapping missing"))
        logger.warning("CAP_MAPPING_MISSING %s %s", method, path)
        return

    if is_public_route(method, path):
        return

    if device_token and _has_required_caps(required, DEVICE_CAPS):
        return

    if not creds or not creds.credentials:
        if enforce:
            _http_401(_detail("CAP_AUTH_REQUIRED", "missing bearer token"))
        logger.warning("CAP_AUTH_MISSING %s %s", method, path)
        return

    try:
        payload = decode_access_token(creds.credentials)
    except AuthTokenError as e:
        if enforce:
            _http_401(_detail("CAP_AUTH_INVALID", str(e)))
        logger.warning("CAP_AUTH_INVALID %s %s", method, path)
        return
    except Exception:
        if enforce:
            _http_401(_detail("CAP_AUTH_INVALID", "invalid token"))
        logger.warning("CAP_AUTH_INVALID %s %s", method, path)
        return

    jti = payload.get("jti")
    if jti and await is_token_revoked(db, str(jti)):
        _http_401(_detail("CAP_TOKEN_REVOKED", "token revoked"))

    caps = payload.get("caps") or []
    if not isinstance(caps, list):
        caps = []

    unknown = validate_caps(caps)
    if unknown:
        if enforce:
            _http_403(_detail("CAP_UNKNOWN", "unknown capability"))
        logger.warning("CAP_UNKNOWN %s %s caps=%s", method, path, unknown)
        return

    if not _has_required_caps(required, caps):
        if enforce:
            _http_403(_detail("CAP_FORBIDDEN", "insufficient capability"))
        logger.warning("CAP_FORBIDDEN %s %s required=%s", method, path, required)
        return
