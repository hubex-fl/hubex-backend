from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.config import ConfigV1

router = APIRouter(prefix="/config", tags=["config"])


class ConfigMetaOut(BaseModel):
    id: int
    namespace: str
    key: str
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[ConfigMetaOut])
async def list_config(
    namespace: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ConfigV1)
    if namespace:
        stmt = stmt.where(ConfigV1.namespace == namespace)
    res = await db.execute(stmt.order_by(ConfigV1.id))
    rows = res.scalars().all()
    return [
        ConfigMetaOut(
            id=row.id,
            namespace=row.namespace,
            key=row.key,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/{config_id}", response_model=ConfigMetaOut)
async def get_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(ConfigV1).where(ConfigV1.id == config_id))
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="config not found")
    return ConfigMetaOut(
        id=row.id,
        namespace=row.namespace,
        key=row.key,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
