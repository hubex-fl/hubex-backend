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
from app.db.models.modules import ModuleRegistry

logger = logging.getLogger("uvicorn.error")

bearer = HTTPBearer(auto_error=False)
device_token_header = APIKeyHeader(name="X-Device-Token", auto_error=False)

DEVICE_CAPS: set[str] = {"vars.read", "vars.ack", "telemetry.emit"}


def _log_soft(enforce: bool, msg: str, *args: object) -> None:
    if enforce:
        logger.warning(msg, *args)
    else:
        logger.debug(msg, *args)


def _http_401(detail: dict) -> None:
    raise HTTPException(status_code=401, detail=detail)


def _http_403(detail: dict) -> None:
    raise HTTPException(status_code=403, detail=detail)


def _detail(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _has_required_caps(required: Iterable[str], caps: Iterable[str]) -> bool:
    cap_set = set(caps)
    return all(cap in cap_set for cap in required)

def _module_key_from_subject(subject: str | None) -> str | None:
    if not subject:
        return None
    if subject.startswith("module:"):
        key = subject.split(":", 1)[1].strip()
        return key or None
    return None


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
        _log_soft(enforce, "CAP_MAPPING_MISSING %s %s", method, path)
        return

    if is_public_route(method, path):
        return

    if device_token and _has_required_caps(required, DEVICE_CAPS):
        return

    if not creds or not creds.credentials:
        if enforce:
            _http_401(_detail("CAP_AUTH_REQUIRED", "missing bearer token"))
        _log_soft(enforce, "CAP_AUTH_MISSING %s %s", method, path)
        return

    try:
        payload = decode_access_token(creds.credentials)
    except AuthTokenError as e:
        if enforce:
            _http_401(_detail("CAP_AUTH_INVALID", str(e)))
        _log_soft(enforce, "CAP_AUTH_INVALID %s %s", method, path)
        return
    except Exception:
        if enforce:
            _http_401(_detail("CAP_AUTH_INVALID", "invalid token"))
        _log_soft(enforce, "CAP_AUTH_INVALID %s %s", method, path)
        return

    jti = payload.get("jti")
    if jti and await is_token_revoked(db, str(jti)):
        _http_401(_detail("CAP_TOKEN_REVOKED", "token revoked"))

    module_key = _module_key_from_subject(str(payload.get("sub") or ""))
    if module_key:
        module = await db.get(ModuleRegistry, module_key)
        if module is None:
            _http_403(_detail("MODULE_NOT_FOUND", "module not registered"))
        if not module.enabled:
            _http_403(_detail("MODULE_DISABLED", "module disabled"))

    caps = payload.get("caps") or []
    if not isinstance(caps, list):
        caps = []

    unknown = validate_caps(caps)
    if unknown:
        if enforce:
            _http_403(_detail("CAP_UNKNOWN", "unknown capability"))
        _log_soft(enforce, "CAP_UNKNOWN %s %s caps=%s", method, path, unknown)
        return

    if not _has_required_caps(required, caps):
        if enforce:
            if "devices.purge" in required:
                _http_403(_detail("DEVICE_PURGE_FORBIDDEN", "Missing capability: devices.purge"))
            _http_403(_detail("CAP_FORBIDDEN", "insufficient capability"))
        _log_soft(enforce, "CAP_FORBIDDEN %s %s required=%s", method, path, required)
        return
