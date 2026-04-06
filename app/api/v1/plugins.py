"""Plugin Framework — install, configure, enable/disable, execute."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.system_events import emit_system_event
from app.db.models.plugin import Plugin
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/plugins", tags=["Plugins"])


class PluginInstallIn(BaseModel):
    key: str
    name: str
    version: str = "0.1.0"
    description: str | None = None
    author: str | None = None
    manifest: dict = {}
    required_caps: list[str] = []
    sandbox_mode: str = "restricted"
    config: dict | None = None


class PluginOut(BaseModel):
    id: int
    key: str
    name: str
    version: str
    description: str | None
    author: str | None
    manifest: dict
    required_caps: list[str]
    sandbox_mode: str
    enabled: bool
    execution_count: int
    error_count: int
    last_executed_at: str | None
    installed_at: str
    config: dict | None


class PluginConfigIn(BaseModel):
    config: dict
    enabled: bool | None = None


@router.get("", response_model=list[PluginOut])
async def list_plugins(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plugin).order_by(Plugin.name))
    return [_to_out(p) for p in result.scalars().all()]


@router.post("", response_model=PluginOut, status_code=201)
async def install_plugin(
    data: PluginInstallIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Plugin).where(Plugin.key == data.key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"plugin '{data.key}' already installed")

    plugin = Plugin(
        key=data.key,
        name=data.name,
        version=data.version,
        description=data.description,
        author=data.author,
        manifest=data.manifest,
        required_caps=data.required_caps,
        sandbox_mode=data.sandbox_mode,
        config=data.config,
        installed_by=user.id,
    )
    db.add(plugin)
    await emit_system_event(db, "plugin.installed", {
        "key": data.key, "version": data.version, "user_id": user.id,
    })
    await db.commit()
    await db.refresh(plugin)
    return _to_out(plugin)


@router.get("/{plugin_key}", response_model=PluginOut)
async def get_plugin(plugin_key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")
    return _to_out(plugin)


@router.patch("/{plugin_key}", response_model=PluginOut)
async def configure_plugin(
    plugin_key: str,
    data: PluginConfigIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")

    plugin.config = data.config
    if data.enabled is not None:
        plugin.enabled = data.enabled
        await emit_system_event(db, f"plugin.{'enabled' if data.enabled else 'disabled'}", {
            "key": plugin_key, "user_id": user.id,
        })

    await db.commit()
    await db.refresh(plugin)
    return _to_out(plugin)


@router.delete("/{plugin_key}", status_code=204)
async def uninstall_plugin(
    plugin_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")

    await db.delete(plugin)
    await emit_system_event(db, "plugin.uninstalled", {
        "key": plugin_key, "user_id": user.id,
    })
    await db.commit()


@router.post("/{plugin_key}/execute")
async def execute_plugin(
    plugin_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Execute a plugin's main hook (sandboxed)."""
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")
    if not plugin.enabled:
        raise HTTPException(status_code=400, detail="plugin is disabled")

    # Sandboxed execution placeholder
    # In production: load plugin code, validate caps, run in sandbox
    plugin.execution_count += 1
    plugin.last_executed_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "status": "executed",
        "plugin": plugin_key,
        "execution_count": plugin.execution_count,
        "sandbox_mode": plugin.sandbox_mode,
    }


def _to_out(p: Plugin) -> PluginOut:
    return PluginOut(
        id=p.id, key=p.key, name=p.name, version=p.version,
        description=p.description, author=p.author,
        manifest=p.manifest, required_caps=p.required_caps or [],
        sandbox_mode=p.sandbox_mode, enabled=p.enabled,
        execution_count=p.execution_count, error_count=p.error_count,
        last_executed_at=p.last_executed_at.isoformat() if p.last_executed_at else None,
        installed_at=p.installed_at.isoformat(),
        config=p.config,
    )
