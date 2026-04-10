import logging
from typing import Iterable

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, AuthTokenError
from app.core.token_revoke import is_token_revoked
from app.core.capabilities import (
    enforcement_enabled,
    is_public_route,
    resolve_required_caps,
    validate_caps,
)
from app.core.features import is_feature_enabled, resolve_feature_for_route
from app.api.deps import get_db
from app.core.api_keys import is_api_key
from app.db.models.modules import ModuleRegistry
from app.db.models.api_key import ApiKey

logger = logging.getLogger("uvicorn.error")

bearer = HTTPBearer(auto_error=False)
device_token_header = APIKeyHeader(name="X-Device-Token", auto_error=False)

DEVICE_CAPS: set[str] = {"vars.read", "vars.ack", "telemetry.emit", "edge.config"}


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

    enforce = enforcement_enabled()

    # Public routes bypass ALL auth — check FIRST before capability mapping
    if is_public_route(method, path):
        return

    required = resolve_required_caps(method, path)

    if required is None:
        if enforce:
            _http_403(_detail("CAP_MAPPING_MISSING", "capability mapping missing"))
        _log_soft(enforce, "CAP_MAPPING_MISSING %s %s", method, path)
        return

    # Feature flag gate — route may belong to a disabled subsystem
    feature_key = resolve_feature_for_route(method, path)
    if feature_key is not None:
        try:
            feat_enabled = await is_feature_enabled(db, feature_key)
        except Exception:
            feat_enabled = True  # fail-open on DB hiccups
        if not feat_enabled:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "FEATURE_DISABLED",
                    "message": f"feature '{feature_key}' is disabled",
                    "feature": feature_key,
                },
            )

    if device_token and _has_required_caps(required, DEVICE_CAPS):
        return

    # API Key authentication (hbx_ prefix)
    if creds and creds.credentials and is_api_key(creds.credentials):
        from app.core.security import hash_device_token
        from datetime import datetime, timezone

        key_hash = hash_device_token(creds.credentials)
        res = await db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        api_key = res.scalar_one_or_none()
        if api_key is None or api_key.revoked:
            if enforce:
                _http_401(_detail("CAP_APIKEY_INVALID", "invalid or revoked API key"))
            return
        if api_key.expires_at and api_key.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            if enforce:
                _http_401(_detail("CAP_APIKEY_EXPIRED", "API key has expired"))
            return

        # Update last_used_at
        api_key.last_used_at = datetime.now(timezone.utc)

        api_key_caps = api_key.caps or []
        if not _has_required_caps(required, api_key_caps):
            if enforce:
                _http_403(_detail("CAP_APIKEY_FORBIDDEN", "API key lacks required capability"))
            return
        request.state.auth_method = "api_key"
        request.state.api_key_id = api_key.id
        request.state.user_id = api_key.user_id
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
