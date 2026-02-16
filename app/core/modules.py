from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditV1Entry
from app.db.models.modules import ModuleRegistry


MODULES_DIR = Path(__file__).resolve().parents[2] / "modules"


@dataclass(frozen=True)
class ModuleMeta:
    key: str
    name: str
    version: str
    description: str | None
    capabilities: list[str]
    source_hash: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _read_module_json(path: Path) -> ModuleMeta:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    key = str(data.get("key", "")).strip()
    name = str(data.get("name", "")).strip()
    version = str(data.get("version", "")).strip()
    if not key or not name or not version:
        raise ValueError(f"invalid module.json at {path}")
    description = data.get("description")
    if description is not None:
        description = str(description).strip()
    capabilities = data.get("capabilities") or []
    if not isinstance(capabilities, list):
        raise ValueError(f"invalid capabilities in {path}")
    caps = [str(c).strip() for c in capabilities if str(c).strip()]
    source_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return ModuleMeta(
        key=key,
        name=name,
        version=version,
        description=description,
        capabilities=caps,
        source_hash=source_hash,
    )


def scan_module_metadata() -> list[ModuleMeta]:
    if not MODULES_DIR.exists():
        return []
    items: list[ModuleMeta] = []
    for entry in sorted(MODULES_DIR.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_"):
            continue
        module_json = entry / "module.json"
        if not module_json.exists():
            continue
        items.append(_read_module_json(module_json))
    return items


async def sync_module_registry(db: AsyncSession) -> None:
    metas = scan_module_metadata()
    if not metas:
        return
    now = _now_utc()
    for meta in metas:
        existing = await db.get(ModuleRegistry, meta.key)
        if existing is None:
            db.add(
                ModuleRegistry(
                    key=meta.key,
                    name=meta.name,
                    version=meta.version,
                    description=meta.description,
                    capabilities=meta.capabilities,
                    installed_at=now,
                    enabled=False,
                    source_hash=meta.source_hash,
                    last_seen_at=now,
                )
            )
        else:
            existing.name = meta.name
            existing.version = meta.version
            existing.description = meta.description
            existing.capabilities = meta.capabilities
            existing.source_hash = meta.source_hash
            existing.last_seen_at = now
    await db.commit()


async def list_modules(db: AsyncSession) -> list[ModuleRegistry]:
    await sync_module_registry(db)
    res = await db.execute(select(ModuleRegistry).order_by(ModuleRegistry.key.asc()))
    return list(res.scalars().all())


async def get_module(db: AsyncSession, key: str) -> ModuleRegistry | None:
    await sync_module_registry(db)
    return await db.get(ModuleRegistry, key)


async def set_module_enabled(
    db: AsyncSession,
    key: str,
    enabled: bool,
    *,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> ModuleRegistry | None:
    await sync_module_registry(db)
    module = await db.get(ModuleRegistry, key)
    if module is None:
        return None
    module.enabled = enabled
    if actor_type and actor_id:
        db.add(
            AuditV1Entry(
                actor_type=actor_type,
                actor_id=actor_id,
                action="module.enable" if enabled else "module.disable",
                resource=module.key,
                audit_metadata={"enabled": enabled},
            )
        )
    await db.commit()
    await db.refresh(module)
    return module
