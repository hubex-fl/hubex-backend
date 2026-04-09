"""System endpoints — health, demo data, edition limits."""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Edition & Soft Limits
# ---------------------------------------------------------------------------

@router.get("/system/limits")
async def get_system_limits(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return current edition and soft limit status for all tracked resources."""
    from app.db.models.user import User
    from app.db.models.device import Device
    from app.db.models.api_key import ApiKey
    from app.db.models.dashboard import Dashboard
    from app.db.models.automation import AutomationRule
    from app.db.models.custom_endpoint import CustomEndpoint

    users_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    devices_count = (await db.execute(select(func.count(Device.id)))).scalar_one()
    api_keys_count = (await db.execute(select(func.count(ApiKey.id)))).scalar_one()
    dashboards_count = (await db.execute(select(func.count(Dashboard.id)))).scalar_one()
    automations_count = (await db.execute(select(func.count(AutomationRule.id)))).scalar_one()
    custom_endpoints_count = (await db.execute(select(func.count(CustomEndpoint.id)))).scalar_one()

    def _limit_entry(current: int, max_val: int) -> dict:
        # 0 means unlimited (enterprise)
        exceeded = max_val > 0 and current > max_val
        return {"current": current, "max": max_val, "exceeded": exceeded}

    return {
        "edition": settings.edition,
        "upgrade_url": settings.upgrade_url,
        "limits": {
            "users": _limit_entry(users_count, settings.max_users),
            "devices": _limit_entry(devices_count, settings.max_devices),
            "api_keys": _limit_entry(api_keys_count, settings.max_api_keys),
            "dashboards": _limit_entry(dashboards_count, settings.max_dashboards),
            "automations": _limit_entry(automations_count, settings.max_automations),
            "custom_endpoints": _limit_entry(custom_endpoints_count, settings.max_custom_endpoints),
        },
    }


# ---------------------------------------------------------------------------
# Demo data management
# ---------------------------------------------------------------------------

@router.post("/system/demo-data")
async def load_demo_data(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Load demo data (devices, variables, automations, dashboard)."""
    from app.scripts.seed_demo_data import seed
    result = await seed(db)
    return {"status": "ok", "created": result}


@router.delete("/system/demo-data")
async def delete_demo_data(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Remove all demo data."""
    from app.scripts.seed_demo_data import remove_demo
    result = await remove_demo(db)
    return {"status": "ok", "deleted": result}
