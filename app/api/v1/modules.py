from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.error_utils import raise_api_error
from app.core.modules import get_module, list_modules, set_module_enabled

router = APIRouter(prefix="/modules", tags=["modules"])


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
async def enable_module_endpoint(key: str, db: AsyncSession = Depends(get_db)):
    module = await set_module_enabled(db, key, True)
    if module is None:
        raise_api_error(404, "MODULE_NOT_FOUND", "module not found")
    return ModuleOut.model_validate(module)


@router.post("/{key}/disable", response_model=ModuleOut)
async def disable_module_endpoint(key: str, db: AsyncSession = Depends(get_db)):
    module = await set_module_enabled(db, key, False)
    if module is None:
        raise_api_error(404, "MODULE_NOT_FOUND", "module not found")
    return ModuleOut.model_validate(module)
