"""System endpoints — health, demo data."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


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
