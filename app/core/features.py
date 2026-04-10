"""Feature flag runtime for HubEx.

Provides a global, single-tenant feature-flag registry. Features are togglable
subsystems (CMS, MCP, Reports, Flow Editor, ...) that can be disabled at runtime
via ``PUT /api/v1/config/features/{key}``. The ``capability_guard`` in
``app/api/deps_caps.py`` uses ``ROUTE_FEATURES`` + ``is_feature_enabled`` to
return 404 ``FEATURE_DISABLED`` for routes belonging to disabled features.

Design decisions:
    * Opt-out migration: new flags default to ``enabled=True`` so upgrades
      never break existing installations.
    * Global scope: no per-org or per-user flags. Single ``feature_flags``
      table keyed by ``key``.
    * In-process cache with 10s TTL keeps the hot-path cheap and still allows
      live-toggle without restart.
    * Core features (auth, devices, variables, dashboards, alerts, health,
      config, features itself) are intentionally NOT in the registry — they
      cannot be disabled.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditV1Entry
from app.db.models.feature_flag import FeatureFlag

logger = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureDef:
    key: str
    name: str
    description: str
    category: str  # "content" | "ai" | "advanced" | "hardware" | "security"
                   # | "compliance" | "integration" | "core" | "ux" | "dev" | "ui"
    default: bool = True
    requires: tuple[str, ...] = field(default_factory=tuple)


def _f(
    key: str,
    name: str,
    description: str,
    category: str,
    requires: tuple[str, ...] = (),
    default: bool = True,
) -> FeatureDef:
    return FeatureDef(
        key=key,
        name=name,
        description=description,
        category=category,
        default=default,
        requires=requires,
    )


FEATURES: dict[str, FeatureDef] = {
    # Content / marketing
    "cms": _f(
        "cms",
        "CMS Pages",
        "Public pages with blocks, forms, menus, media library and SEO.",
        "content",
    ),
    "reports": _f(
        "reports",
        "Reports",
        "Scheduled report generation and templates.",
        "content",
    ),
    "email_templates": _f(
        "email_templates",
        "Email Templates",
        "Customizable email templates for alerts and notifications.",
        "integration",
    ),
    # AI
    "mcp": _f(
        "mcp",
        "MCP Server",
        "Model Context Protocol server for AI assistants (Claude, Cursor, etc.).",
        "ai",
    ),
    "ai_coop": _f(
        "ai_coop",
        "AI Coop Mode",
        "AI copilot that can navigate the UI and assist with tasks.",
        "ai",
        requires=("mcp",),
    ),
    # Advanced tooling
    "flow_editor": _f(
        "flow_editor",
        "Flow Editor / System Map",
        "Interactive 3D visualization of the device/variable/automation graph.",
        "advanced",
    ),
    "custom_api": _f(
        "custom_api",
        "Custom API Builder",
        "Create custom REST endpoints from variable/device queries.",
        "advanced",
    ),
    "semantic_types": _f(
        "semantic_types",
        "Semantic Types",
        "Rich semantic metadata for variables (temperature, humidity, GPS, ...).",
        "advanced",
    ),
    "observability": _f(
        "observability",
        "Observability",
        "Traces, metrics and distributed-call timeline.",
        "advanced",
    ),
    "orchestrator": _f(
        "orchestrator",
        "Plugin Orchestrator",
        "Spawn and manage Docker containers for service plugins (n8n, Frigate, "
        "Ollama, ...). Uses Portainer as the Docker backend. Keep OFF for a "
        "lightweight install that only allows connector-style plugins.",
        "advanced",
        default=False,
    ),
    "sandbox": _f(
        "sandbox",
        "Sandbox",
        "Developer scratchpad for experimenting with variables and devices.",
        "dev",
    ),
    # Hardware
    "ota": _f(
        "ota",
        "OTA Updates",
        "Over-the-air firmware updates with rollouts and rollback.",
        "hardware",
    ),
    "hardware": _f(
        "hardware",
        "Hardware Boards",
        "Board profiles, shields, pin configurations and code generator.",
        "hardware",
    ),
    "simulator": _f(
        "simulator",
        "Device Simulator",
        "Simulated devices emitting synthetic telemetry for demos and testing.",
        "dev",
    ),
    # Security / compliance
    "mfa": _f(
        "mfa",
        "Multi-Factor Authentication",
        "TOTP-based 2FA for user accounts.",
        "security",
    ),
    "audit_log": _f(
        "audit_log",
        "Audit Log",
        "Persistent audit trail of all administrative actions.",
        "compliance",
    ),
    "api_keys": _f(
        "api_keys",
        "API Keys",
        "Long-lived API keys for programmatic access.",
        "security",
    ),
    # Integrations
    "webhooks": _f(
        "webhooks",
        "Webhooks",
        "Outgoing webhook subscriptions to external systems.",
        "integration",
    ),
    "integrations": _f(
        "integrations",
        "Integrations Catalog",
        "Pre-built integration templates (Slack, Discord, Teams, ...).",
        "integration",
    ),
    # Core UX
    "plugins": _f(
        "plugins",
        "Plugin Manager",
        "Install and manage plugins (coming: container orchestration).",
        "core",
    ),
    "modules": _f(
        "modules",
        "Modules",
        "Filesystem-scanned Python modules with runtime enable/disable.",
        "core",
    ),
    "tours": _f(
        "tours",
        "Tour Builder",
        "Guided tours for onboarding and feature discovery.",
        "ux",
    ),
    "notifications": _f(
        "notifications",
        "Notifications",
        "In-app notification inbox and delivery channels.",
        "core",
    ),
    "pairing": _f(
        "pairing",
        "Device Pairing",
        "QR-code based device pairing flow.",
        "core",
    ),
    "automations": _f(
        "automations",
        "Automations",
        "IF-THEN automation rules engine.",
        "core",
    ),
    "kiosk": _f(
        "kiosk",
        "Kiosk Mode",
        "Fullscreen dashboard rotation for public displays.",
        "ui",
    ),
}


# ---------------------------------------------------------------------------
# Route → Feature mapping (used by capability_guard for gating)
# ---------------------------------------------------------------------------

# Each entry maps (HTTP method, path template) → feature_key. Path must match
# the FastAPI route template exactly (same style as CAPABILITY_MAP).
ROUTE_FEATURES: dict[tuple[str, str], str] = {}


def _gate(feature: str, entries: Iterable[tuple[str, str]]) -> None:
    for method, path in entries:
        ROUTE_FEATURES[(method, path)] = feature


# --- CMS (+ sub-features) ---------------------------------------------------
_gate("cms", [
    ("GET",    "/api/v1/cms/pages"),
    ("POST",   "/api/v1/cms/pages"),
    ("GET",    "/api/v1/cms/pages/{page_id}"),
    ("PUT",    "/api/v1/cms/pages/{page_id}"),
    ("DELETE", "/api/v1/cms/pages/{page_id}"),
    ("POST",   "/api/v1/cms/pages/{page_id}/publish"),
    ("POST",   "/api/v1/cms/pages/{page_id}/unpublish"),
    ("POST",   "/api/v1/cms/pages/{page_id}/share"),
    ("DELETE", "/api/v1/cms/pages/{page_id}/share"),
    ("POST",   "/api/v1/cms/pages/{page_id}/pin"),
    ("DELETE", "/api/v1/cms/pages/{page_id}/pin"),
    ("POST",   "/api/v1/cms/pages/{page_id}/clone"),
    ("GET",    "/api/v1/cms/pages/{page_id}/render"),
    ("GET",    "/api/v1/cms/pages/tree"),
    ("PUT",    "/api/v1/cms/pages/{page_id}/move"),
    ("GET",    "/api/v1/cms/menus"),
    ("POST",   "/api/v1/cms/menus"),
    ("GET",    "/api/v1/cms/menus/{menu_id}"),
    ("PUT",    "/api/v1/cms/menus/{menu_id}"),
    ("DELETE", "/api/v1/cms/menus/{menu_id}"),
    ("GET",    "/api/v1/cms/templates"),
    ("GET",    "/api/v1/cms/templates/{template_id}"),
    ("POST",   "/api/v1/cms/pages/from-template/{template_id}"),
    ("GET",    "/api/v1/cms/forms"),
    ("POST",   "/api/v1/cms/forms"),
    ("GET",    "/api/v1/cms/forms/{form_id}"),
    ("PUT",    "/api/v1/cms/forms/{form_id}"),
    ("DELETE", "/api/v1/cms/forms/{form_id}"),
    ("GET",    "/api/v1/cms/forms/{form_id}/submissions"),
    ("GET",    "/api/v1/cms/forms/{form_id}/submissions/{submission_id}"),
    ("DELETE", "/api/v1/cms/forms/{form_id}/submissions/{submission_id}"),
    ("GET",    "/api/v1/cms/pages/{page_id}/versions"),
    ("GET",    "/api/v1/cms/pages/{page_id}/versions/{ver}"),
    ("POST",   "/api/v1/cms/pages/{page_id}/versions/{ver}/restore"),
    ("GET",    "/api/v1/cms/search"),
    ("GET",    "/api/v1/cms/pages/{page_id}/export"),
    ("POST",   "/api/v1/cms/pages/import"),
    ("POST",   "/api/v1/cms/pages/{page_id}/schedule"),
    ("POST",   "/api/v1/cms/pages/{page_id}/archive"),
    ("POST",   "/api/v1/cms/pages/{page_id}/unarchive"),
    ("GET",    "/api/v1/cms/pages/{page_id}/stats"),
    ("GET",    "/api/v1/cms/redirects"),
    ("POST",   "/api/v1/cms/redirects"),
    ("PUT",    "/api/v1/cms/redirects/{redirect_id}"),
    ("DELETE", "/api/v1/cms/redirects/{redirect_id}"),
    ("GET",    "/api/v1/media"),
    ("POST",   "/api/v1/media/upload"),
    ("GET",    "/api/v1/media/{asset_id}"),
])

# --- MCP --------------------------------------------------------------------
_gate("mcp", [
    ("POST", "/api/v1/mcp/call"),
    ("GET",  "/api/v1/mcp/tools"),
    ("GET",  "/api/v1/mcp/resources"),
    ("POST", "/api/v1/mcp/sse"),
])

# --- Custom API -------------------------------------------------------------
_gate("custom_api", [
    ("GET",    "/api/v1/custom-api"),
    ("POST",   "/api/v1/custom-api"),
    ("GET",    "/api/v1/custom-api/{endpoint_id}"),
    ("PUT",    "/api/v1/custom-api/{endpoint_id}"),
    ("DELETE", "/api/v1/custom-api/{endpoint_id}"),
])

# --- OTA --------------------------------------------------------------------
_gate("ota", [
    ("GET",    "/api/v1/ota/firmware"),
    ("POST",   "/api/v1/ota/firmware"),
    ("GET",    "/api/v1/ota/rollouts"),
    ("POST",   "/api/v1/ota/rollouts"),
    ("POST",   "/api/v1/ota/rollouts/{rollout_id}/start"),
    ("POST",   "/api/v1/ota/rollouts/{rollout_id}/abort"),
])

# --- MFA --------------------------------------------------------------------
_gate("mfa", [
    ("POST",   "/api/v1/mfa/enroll"),
    ("POST",   "/api/v1/mfa/verify"),
    ("POST",   "/api/v1/mfa/disable"),
    ("GET",    "/api/v1/mfa/status"),
])

# --- Audit ------------------------------------------------------------------
_gate("audit_log", [
    ("GET", "/api/v1/audit"),
    ("GET", "/api/v1/audit/{entry_id}"),
])

# --- Reports ----------------------------------------------------------------
_gate("reports", [
    ("GET",    "/api/v1/reports"),
    ("POST",   "/api/v1/reports"),
    ("GET",    "/api/v1/reports/{report_id}"),
    ("PUT",    "/api/v1/reports/{report_id}"),
    ("DELETE", "/api/v1/reports/{report_id}"),
    ("POST",   "/api/v1/reports/{report_id}/generate"),
    ("GET",    "/api/v1/reports/templates"),
])

# --- Webhooks ---------------------------------------------------------------
_gate("webhooks", [
    ("GET",    "/api/v1/webhooks"),
    ("POST",   "/api/v1/webhooks"),
    ("GET",    "/api/v1/webhooks/{webhook_id}"),
    ("PUT",    "/api/v1/webhooks/{webhook_id}"),
    ("DELETE", "/api/v1/webhooks/{webhook_id}"),
])

# --- Email templates --------------------------------------------------------
_gate("email_templates", [
    ("GET",    "/api/v1/email-templates"),
    ("POST",   "/api/v1/email-templates"),
    ("GET",    "/api/v1/email-templates/{template_id}"),
    ("PUT",    "/api/v1/email-templates/{template_id}"),
    ("DELETE", "/api/v1/email-templates/{template_id}"),
])

# --- Plugins ----------------------------------------------------------------
_gate("plugins", [
    ("GET",    "/api/v1/plugins"),
    ("POST",   "/api/v1/plugins"),
    ("GET",    "/api/v1/plugins/{key}"),
    ("PATCH",  "/api/v1/plugins/{key}"),
    ("DELETE", "/api/v1/plugins/{key}"),
    ("POST",   "/api/v1/plugins/{key}/execute"),
])

# --- Modules ----------------------------------------------------------------
_gate("modules", [
    ("GET",  "/api/v1/modules"),
    ("GET",  "/api/v1/modules/{key}"),
    ("POST", "/api/v1/modules/{key}/enable"),
    ("POST", "/api/v1/modules/{key}/disable"),
])

# --- Tours ------------------------------------------------------------------
_gate("tours", [
    ("GET",    "/api/v1/tours"),
    ("POST",   "/api/v1/tours"),
    ("GET",    "/api/v1/tours/{tour_id}"),
    ("PUT",    "/api/v1/tours/{tour_id}"),
    ("DELETE", "/api/v1/tours/{tour_id}"),
])

# --- Hardware / components / codegen ---------------------------------------
_gate("hardware", [
    ("GET",  "/api/v1/hardware/boards"),
    ("GET",  "/api/v1/hardware/shields"),
    ("PUT",  "/api/v1/devices/{device_id}/pins"),
    ("GET",  "/api/v1/components"),
    ("GET",  "/api/v1/components/{key}"),
    ("POST", "/api/v1/codegen/generate"),
    ("GET",  "/api/v1/codegen/preview/{device_id}"),
    ("POST", "/api/v1/codegen/project"),
])

# --- Simulator --------------------------------------------------------------
_gate("simulator", [
    ("GET",    "/api/v1/simulator"),
    ("POST",   "/api/v1/simulator"),
    ("PUT",    "/api/v1/simulator/{sim_id}"),
    ("DELETE", "/api/v1/simulator/{sim_id}"),
    ("POST",   "/api/v1/simulator/{sim_id}/start"),
    ("POST",   "/api/v1/simulator/{sim_id}/stop"),
])

# --- Observability ----------------------------------------------------------
_gate("observability", [
    ("GET", "/api/v1/observability/traces"),
    ("GET", "/api/v1/observability/metrics"),
])

# --- Semantic types ---------------------------------------------------------
_gate("semantic_types", [
    ("GET",    "/api/v1/semantic-types"),
    ("POST",   "/api/v1/semantic-types"),
    ("GET",    "/api/v1/semantic-types/{type_id}"),
    ("PUT",    "/api/v1/semantic-types/{type_id}"),
    ("DELETE", "/api/v1/semantic-types/{type_id}"),
])

# --- Notifications ----------------------------------------------------------
_gate("notifications", [
    ("GET",    "/api/v1/notifications"),
    ("POST",   "/api/v1/notifications/{notification_id}/ack"),
    ("DELETE", "/api/v1/notifications/{notification_id}"),
])

# --- API Keys ---------------------------------------------------------------
_gate("api_keys", [
    ("GET",    "/api/v1/api-keys"),
    ("POST",   "/api/v1/api-keys"),
    ("GET",    "/api/v1/api-keys/{key_id}"),
    ("DELETE", "/api/v1/api-keys/{key_id}"),
])


def resolve_feature_for_route(method: str, path: str) -> str | None:
    """Return the feature key that gates this route, or ``None`` if ungated."""
    return ROUTE_FEATURES.get((method.upper(), path))


# ---------------------------------------------------------------------------
# Cached state access
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 10.0
_cache: dict[str, tuple[float, bool]] = {}  # key -> (expires_at, enabled)


def _cache_get(key: str) -> bool | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, enabled = entry
    if expires_at < time.time():
        _cache.pop(key, None)
        return None
    return enabled


def _cache_set(key: str, enabled: bool) -> None:
    _cache[key] = (time.time() + _CACHE_TTL_SECONDS, enabled)


def _cache_invalidate(key: str | None = None) -> None:
    if key is None:
        _cache.clear()
    else:
        _cache.pop(key, None)


async def is_feature_enabled(db: AsyncSession, key: str) -> bool:
    """Return whether a feature is enabled.

    Reads from in-process cache (TTL 10s) to avoid hitting the DB on every
    request. Unknown keys (not in the registry) always return ``True`` — they
    don't correspond to togglable features and should never block.
    """
    feat = FEATURES.get(key)
    if feat is None:
        return True  # ungated / unknown key

    cached = _cache_get(key)
    if cached is not None:
        return cached

    row = await db.get(FeatureFlag, key)
    if row is None:
        # Not yet synced — fall back to registry default
        enabled = feat.default
    else:
        enabled = bool(row.enabled)
    _cache_set(key, enabled)
    return enabled


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------


async def sync_feature_flags(db: AsyncSession) -> int:
    """Ensure every feature in the registry has a row. Opt-out migration.

    Returns the number of currently enabled features. Called at startup from
    ``app/main.py`` right after ``sync_module_registry``.
    """
    existing_res = await db.execute(select(FeatureFlag))
    existing = {row.key: row for row in existing_res.scalars().all()}

    created = 0
    for key, feat in FEATURES.items():
        if key in existing:
            continue
        db.add(
            FeatureFlag(
                key=key,
                enabled=feat.default,
                updated_at=datetime.now(timezone.utc),
                updated_by="system",
            )
        )
        created += 1

    if created:
        await db.commit()
        _cache_invalidate()

    # Count enabled for log line
    enabled_count = sum(
        1
        for key, feat in FEATURES.items()
        if (existing.get(key).enabled if key in existing else feat.default)
    )
    return enabled_count


async def set_feature_enabled(
    db: AsyncSession,
    key: str,
    enabled: bool,
    *,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> FeatureFlag | None:
    """Toggle a feature flag. Audit-logs the change."""
    if key not in FEATURES:
        return None

    row = await db.get(FeatureFlag, key)
    if row is None:
        row = FeatureFlag(
            key=key,
            enabled=enabled,
            updated_at=datetime.now(timezone.utc),
            updated_by=f"{actor_type}:{actor_id}" if actor_type and actor_id else None,
        )
        db.add(row)
    else:
        row.enabled = enabled
        row.updated_at = datetime.now(timezone.utc)
        row.updated_by = f"{actor_type}:{actor_id}" if actor_type and actor_id else None

    if actor_type and actor_id:
        db.add(
            AuditV1Entry(
                actor_type=actor_type,
                actor_id=actor_id,
                action="feature.enable" if enabled else "feature.disable",
                resource=f"feature:{key}",
                audit_metadata={"key": key, "enabled": enabled},
            )
        )

    await db.commit()
    await db.refresh(row)
    _cache_invalidate(key)
    return row
