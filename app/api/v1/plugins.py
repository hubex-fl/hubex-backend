"""Plugin Framework — install, configure, enable/disable, execute."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.features import is_feature_enabled
from app.core.plugin_catalog import CatalogEntry, get_catalog_entry, list_catalog
from app.core.portainer_client import PortainerError, get_portainer_client
from app.core.system_events import emit_system_event
from app.db.models.plugin import Plugin
from app.db.models.secrets import SecretV1
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
    # Sprint 3 — Service vs Connector + runtime lifecycle state
    kind: str = "connector"
    runtime_status: str | None = None
    container_name: str | None = None


class PluginConfigIn(BaseModel):
    config: dict
    enabled: bool | None = None


class PluginCredentialsIn(BaseModel):
    """Body for PUT /plugins/{key}/credentials — maps schema field keys to values."""
    credentials: dict[str, str]


@router.get("", response_model=list[PluginOut])
async def list_plugins(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plugin).order_by(Plugin.name))
    return [_to_out(p) for p in result.scalars().all()]


@router.get("/catalog")
async def get_plugin_catalog(user: User = Depends(get_current_user)) -> list[dict]:
    """List all built-in plugins available for one-click install.

    Returns the full manifest for each entry so the UI can render kind-
    specific install wizards without a second round-trip.
    """
    return [entry.to_public_dict() for entry in list_catalog()]


@router.post("/install-from-catalog/{catalog_key}", response_model=PluginOut, status_code=201)
async def install_from_catalog(
    catalog_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Install a ship-with plugin by its catalog key.

    Dispatches on ``entry.kind``:

    * **connector** — just creates a Plugin row with ``runtime_status=NULL``.
      The caller then sets credentials via ``PUT /plugins/{key}/credentials``.
    * **service** — gated by the ``orchestrator`` feature flag. When enabled,
      the handler spawns (or adopts) a Docker container via Portainer. Sprint
      3h is connector-only; service path is filled in Sprint 3j.
    """
    entry = get_catalog_entry(catalog_key)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CATALOG_ENTRY_NOT_FOUND",
                "message": f"no catalog entry with key '{catalog_key}'",
            },
        )

    # Guard against double-install (same Plugin.key unique constraint)
    existing = await db.execute(select(Plugin).where(Plugin.key == entry.key))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PLUGIN_ALREADY_INSTALLED",
                "message": f"plugin '{entry.key}' is already installed",
            },
        )

    # Service plugins require the orchestrator feature flag to be ON.
    # The check lives here (not in ROUTE_FEATURES) because the decision
    # depends on the catalog entry's kind, not on the route path.
    if entry.kind == "service":
        if not await is_feature_enabled(db, "orchestrator"):
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "FEATURE_DISABLED",
                    "message": (
                        "feature 'orchestrator' is disabled — enable it in "
                        "Settings → Features to install service plugins"
                    ),
                },
            )
        return await _install_service_plugin(entry, db, user)

    # ── Connector install path ──────────────────────────────────────────────
    plugin = Plugin(
        key=entry.key,
        name=entry.name,
        version="1.0.0",
        description=entry.description,
        author=None,
        manifest=entry.manifest,
        required_caps=[],
        sandbox_mode="restricted",
        config=None,
        enabled=True,  # connectors are "on" as soon as installed; creds come next
        installed_by=user.id,
        kind="connector",
        runtime_status=None,
        container_name=None,
    )
    db.add(plugin)
    await emit_system_event(
        db,
        "plugin.installed",
        {
            "key": entry.key,
            "kind": "connector",
            "source": "catalog",
            "user_id": user.id,
        },
    )
    await db.commit()
    await db.refresh(plugin)
    logger.info("plugin installed from catalog: key=%s kind=connector user=%s", entry.key, user.id)
    return _to_out(plugin)


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


@router.post("/{plugin_key}/start", response_model=PluginOut)
async def start_service_plugin(
    plugin_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a service plugin's container via Portainer."""
    plugin = await _get_service_plugin_or_fail(db, plugin_key)
    try:
        await get_portainer_client().start_container(plugin.container_name)
    except PortainerError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.message},
        )
    plugin.runtime_status = "running"
    await emit_system_event(db, "plugin.started", {"key": plugin_key, "user_id": user.id})
    await db.commit()
    await db.refresh(plugin)
    return _to_out(plugin)


@router.post("/{plugin_key}/stop", response_model=PluginOut)
async def stop_service_plugin(
    plugin_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stop a service plugin's container via Portainer."""
    plugin = await _get_service_plugin_or_fail(db, plugin_key)
    try:
        await get_portainer_client().stop_container(plugin.container_name)
    except PortainerError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.message},
        )
    plugin.runtime_status = "stopped"
    await emit_system_event(db, "plugin.stopped", {"key": plugin_key, "user_id": user.id})
    await db.commit()
    await db.refresh(plugin)
    return _to_out(plugin)


@router.get("/{plugin_key}/status")
async def get_plugin_status(
    plugin_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return live status for a plugin.

    * **service** — re-inspects the container via Portainer, updates
      ``runtime_status`` in the DB to reflect reality, and returns the full
      container state. Drift between the DB and the actual container is
      corrected here.
    * **connector** — returns whether credentials are stored (via a lookup
      against SecretV1 with namespace ``plugin:<key>``) so the UI can show
      "Configured" vs "Needs setup" without leaking the values.
    """
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if plugin is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLUGIN_NOT_FOUND", "message": f"plugin '{plugin_key}' not found"},
        )

    if plugin.kind == "connector":
        res = await db.execute(
            select(SecretV1.key).where(SecretV1.namespace == f"plugin:{plugin_key}")
        )
        set_fields = sorted(row[0] for row in res.all())
        return {
            "kind": "connector",
            "key": plugin_key,
            "configured": len(set_fields) > 0,
            "set_fields": set_fields,
        }

    # service
    if not plugin.container_name:
        raise HTTPException(
            status_code=500,
            detail={"code": "SERVICE_MISSING_CONTAINER", "message": "service plugin row has no container_name"},
        )
    try:
        status = await get_portainer_client().get_container_status(plugin.container_name)
    except PortainerError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": exc.code, "message": exc.message},
        )
    new_runtime = _map_portainer_status_to_runtime(status)
    if new_runtime != plugin.runtime_status:
        logger.info(
            "plugin status drift: key=%s db=%s actual=%s",
            plugin_key, plugin.runtime_status, new_runtime,
        )
        plugin.runtime_status = new_runtime
        await db.commit()
    return {
        "kind": "service",
        "key": plugin_key,
        "runtime_status": new_runtime,
        "container_name": plugin.container_name,
        "container": status,  # raw portainer state for debugging/UX
    }


async def _get_service_plugin_or_fail(db: AsyncSession, plugin_key: str) -> Plugin:
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if plugin is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLUGIN_NOT_FOUND", "message": f"plugin '{plugin_key}' not found"},
        )
    if plugin.kind != "service":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "NOT_A_SERVICE",
                "message": f"plugin '{plugin_key}' is a '{plugin.kind}' plugin, not a service",
            },
        )
    if not plugin.container_name:
        raise HTTPException(
            status_code=500,
            detail={"code": "SERVICE_MISSING_CONTAINER", "message": "service plugin row has no container_name"},
        )
    return plugin


@router.put("/{plugin_key}/credentials")
async def set_plugin_credentials(
    plugin_key: str,
    data: PluginCredentialsIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Store credentials for a connector plugin in SecretV1.

    Plaintext values are NEVER returned — only the list of updated field
    keys. Unknown fields (not in the plugin's ``credential_schema``) are
    rejected with 400 so typos surface early. Missing required fields are
    allowed here (partial update); completeness is enforced by the
    consuming subsystem when it reads the secrets.
    """
    result = await db.execute(select(Plugin).where(Plugin.key == plugin_key))
    plugin = result.scalar_one_or_none()
    if plugin is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "PLUGIN_NOT_FOUND", "message": f"plugin '{plugin_key}' not found"},
        )
    if plugin.kind != "connector":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "NOT_A_CONNECTOR",
                "message": f"plugin '{plugin_key}' is a '{plugin.kind}' plugin, not a connector",
            },
        )

    schema_fields = (plugin.manifest or {}).get("credential_schema") or []
    valid_keys = {f.get("key") for f in schema_fields if f.get("key")}
    unknown = sorted(set(data.credentials.keys()) - valid_keys)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNKNOWN_CREDENTIAL_FIELDS",
                "message": f"unknown credential fields: {unknown}",
                "allowed": sorted(valid_keys),
            },
        )

    namespace = f"plugin:{plugin_key}"
    updated: list[str] = []
    for field_key, field_value in data.credentials.items():
        row_res = await db.execute(
            select(SecretV1).where(
                SecretV1.namespace == namespace,
                SecretV1.key == field_key,
            )
        )
        existing = row_res.scalar_one_or_none()
        if existing is not None:
            existing.value = str(field_value)
        else:
            db.add(SecretV1(namespace=namespace, key=field_key, value=str(field_value)))
        updated.append(field_key)

    await emit_system_event(
        db,
        "plugin.credentials_set",
        {"key": plugin_key, "fields": updated, "user_id": user.id},
    )
    await db.commit()
    logger.info("plugin credentials updated: key=%s fields=%s user=%s", plugin_key, updated, user.id)
    return {"ok": True, "updated_fields": sorted(updated)}


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

    # Wipe stored credentials for connector plugins so secrets never outlive
    # the plugin row. Service plugins currently store nothing in SecretV1 but
    # the same cleanup is safe for them too.
    secrets_namespace = f"plugin:{plugin_key}"
    await db.execute(delete(SecretV1).where(SecretV1.namespace == secrets_namespace))

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


def _derive_container_name(entry: CatalogEntry) -> str:
    """Generate a unique container name for fresh-spawn service plugins."""
    import secrets as _secrets
    short_id = _secrets.token_hex(3)
    return f"hubex-plugin-{entry.key}-{short_id}"


def _map_portainer_status_to_runtime(container_status: dict | None) -> str:
    """Translate a Portainer container state into our runtime_status enum."""
    if container_status is None:
        return "error"
    if not container_status.get("running"):
        return "stopped"
    health = container_status.get("health")
    if health in ("unhealthy",):
        return "unhealthy"
    # "healthy", "starting", None -> treat as running (healthchecks are optional)
    return "running"


async def _install_service_plugin(
    entry: CatalogEntry,
    db: AsyncSession,
    user: User,
) -> PluginOut:
    """Service plugin install path: adopt existing container or create a new one.

    Flow:
    1. If ``entry.adopt_container_name`` is set and that container exists on
       the Docker host, **adopt** it — link the Plugin row to the existing
       container without spawning a second one. (Used for n8n which ships in
       docker-compose.full.yml.)
    2. Otherwise generate a unique container name, call Portainer to
       ``create_container`` from the manifest ``docker`` block, then
       ``start_container``.
    3. Any ``PortainerError`` surfaces as HTTP 503 with the structured code
       so the frontend can show an actionable message.
    """
    portainer = get_portainer_client()
    container_name: str
    runtime_status: str

    try:
        # ── Adopt path ──────────────────────────────────────────────────────
        if entry.adopt_container_name:
            if await portainer.container_exists(entry.adopt_container_name):
                container_name = entry.adopt_container_name
                status = await portainer.get_container_status(container_name)
                runtime_status = _map_portainer_status_to_runtime(status)
                logger.info(
                    "plugin adopt: key=%s container=%s runtime=%s",
                    entry.key, container_name, runtime_status,
                )
            else:
                # Catalog declared an adopt target but it doesn't exist —
                # fall through to fresh spawn with the same name so a second
                # install attempt after cleanup still works.
                container_name = entry.adopt_container_name
                await portainer.create_container(container_name, entry.manifest["docker"])
                await portainer.start_container(container_name)
                runtime_status = "running"
                logger.info(
                    "plugin fresh-spawn (adopt miss): key=%s container=%s",
                    entry.key, container_name,
                )
        # ── Fresh spawn path ────────────────────────────────────────────────
        else:
            container_name = _derive_container_name(entry)
            await portainer.create_container(container_name, entry.manifest["docker"])
            await portainer.start_container(container_name)
            runtime_status = "running"
            logger.info(
                "plugin fresh-spawn: key=%s container=%s",
                entry.key, container_name,
            )
    except PortainerError as exc:
        logger.warning(
            "service plugin install failed: key=%s code=%s msg=%s",
            entry.key, exc.code, exc.message,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": exc.code,
                "message": exc.message,
                "hint": "check HUBEX_PORTAINER_PASS and that Portainer is reachable",
            },
        )

    plugin = Plugin(
        key=entry.key,
        name=entry.name,
        version="1.0.0",
        description=entry.description,
        author=None,
        manifest=entry.manifest,
        required_caps=[],
        sandbox_mode="restricted",
        config=None,
        enabled=True,
        installed_by=user.id,
        kind="service",
        runtime_status=runtime_status,
        container_name=container_name,
    )
    db.add(plugin)
    await emit_system_event(
        db,
        "plugin.installed",
        {
            "key": entry.key,
            "kind": "service",
            "source": "catalog",
            "container_name": container_name,
            "runtime_status": runtime_status,
            "user_id": user.id,
        },
    )
    await db.commit()
    await db.refresh(plugin)
    return _to_out(plugin)


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
        kind=p.kind,
        runtime_status=p.runtime_status,
        container_name=p.container_name,
    )
