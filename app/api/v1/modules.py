from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.error_utils import raise_api_error
from app.core.modules import get_module, list_modules, set_module_enabled
from app.core.security import decode_access_token, AuthTokenError

router = APIRouter(prefix="/modules", tags=["modules"])
bearer = HTTPBearer(auto_error=False)


class ModuleOut(BaseModel):
    key: str
    name: str
    version: str
    description: str | None = None
    capabilities: list[str]
    enabled: bool
    installed_at: datetime
    last_seen_at: datetime | None = None
    source_hash: str | None = None

    model_config = ConfigDict(from_attributes=True)

def _actor_from_creds(creds: HTTPAuthorizationCredentials | None) -> tuple[str, str] | None:
    if not creds or not creds.credentials:
        return None
    try:
        payload = decode_access_token(creds.credentials)
    except AuthTokenError:
        return None
    sub = str(payload.get("sub") or "")
    if not sub:
        return None
    if sub.startswith("module:"):
        return "module", sub.split(":", 1)[1].strip()
    if sub.isdigit():
        return "user", sub
    return "token", sub


@router.get("", response_model=list[ModuleOut])
async def list_modules_endpoint(db: AsyncSession = Depends(get_db)):
    items = await list_modules(db)
    return [ModuleOut.model_validate(m) for m in items]


@router.get("/{key}", response_model=ModuleOut)
async def get_module_endpoint(key: str, db: AsyncSession = Depends(get_db)):
    module = await get_module(db, key)
    if module is None:
        raise_api_error(404, "MODULE_NOT_FOUND", "module not found")
    return ModuleOut.model_validate(module)


@router.post("/{key}/enable", response_model=ModuleOut)
async def enable_module_endpoint(
    key: str,
    db: AsyncSession = Depends(get_db),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    actor = _actor_from_creds(creds)
    module = await set_module_enabled(
        db,
        key,
        True,
        actor_type=actor[0] if actor else None,
        actor_id=actor[1] if actor else None,
    )
    if module is None:
        raise_api_error(404, "MODULE_NOT_FOUND", "module not found")
    return ModuleOut.model_validate(module)


@router.post("/{key}/disable", response_model=ModuleOut)
async def disable_module_endpoint(
    key: str,
    db: AsyncSession = Depends(get_db),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    actor = _actor_from_creds(creds)
    module = await set_module_enabled(
        db,
        key,
        False,
        actor_type=actor[0] if actor else None,
        actor_id=actor[1] if actor else None,
    )
    if module is None:
        raise_api_error(404, "MODULE_NOT_FOUND", "module not found")
    return ModuleOut.model_validate(module)
