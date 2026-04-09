"""Edition soft-limit helpers.

Provides `check_soft_limit()` that counts existing rows and, if the
configured maximum is exceeded, logs a warning and returns the resource
name so callers can add an `X-HubEx-Limit-Warning` response header.

These are *soft* limits — creation is never blocked, only signalled.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger("hubex.limits")

# Map resource names to (model_getter, settings_attr) so we can lazily
# import heavy models only when needed.
_LIMIT_MAP: dict[str, tuple[str, str]] = {
    "users":            ("app.db.models.user.User",                "max_users"),
    "devices":          ("app.db.models.device.Device",            "max_devices"),
    "api_keys":         ("app.db.models.api_key.ApiKey",           "max_api_keys"),
    "dashboards":       ("app.db.models.dashboard.Dashboard",      "max_dashboards"),
    "automations":      ("app.db.models.automation.AutomationRule", "max_automations"),
    "custom_endpoints": ("app.db.models.custom_endpoint.CustomEndpoint", "max_custom_endpoints"),
}


def _import_model(dotted: str) -> Any:
    """Dynamically import a model class from a dotted path."""
    module_path, cls_name = dotted.rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


async def check_soft_limit(
    db: AsyncSession,
    resource: str,
) -> str | None:
    """Check if a resource is over its soft limit.

    Returns the resource name (e.g. ``"devices"``) if exceeded, or ``None``.
    The creation should still proceed — this is advisory only.
    """
    if settings.edition != "community":
        return None

    entry = _LIMIT_MAP.get(resource)
    if entry is None:
        return None

    model_path, settings_attr = entry
    max_val: int = getattr(settings, settings_attr, 0)
    if max_val <= 0:
        return None  # unlimited

    model = _import_model(model_path)
    current = (await db.execute(select(func.count(model.id)))).scalar_one()

    if current >= max_val:
        logger.warning(
            "Soft limit exceeded for %s: %d/%d (edition=%s)",
            resource, current, max_val, settings.edition,
        )
        return resource
    return None


def add_limit_warning_header(response: Response, resource: str | None) -> None:
    """Attach ``X-HubEx-Limit-Warning`` header if a soft limit was exceeded."""
    if resource:
        response.headers["X-HubEx-Limit-Warning"] = resource
