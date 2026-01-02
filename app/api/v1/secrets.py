from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.secrets import SecretV1

router = APIRouter(prefix="/secrets", tags=["secrets"])


class SecretMetaOut(BaseModel):
    id: int
    namespace: str
    key: str
    created_at: datetime
    updated_at: datetime
    value_present: bool


@router.get("", response_model=list[SecretMetaOut])
async def list_secrets(
    namespace: str | None = Query(default=None),
    key_prefix: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SecretV1)
    if namespace:
        stmt = stmt.where(SecretV1.namespace == namespace)
    if key_prefix:
        stmt = stmt.where(SecretV1.key.like(f"{key_prefix}%"))
    res = await db.execute(stmt.order_by(SecretV1.id))
    rows = res.scalars().all()
    return [
        SecretMetaOut(
            id=row.id,
            namespace=row.namespace,
            key=row.key,
            created_at=row.created_at,
            updated_at=row.updated_at,
            value_present=True,
        )
        for row in rows
    ]


@router.get("/{secret_id}", response_model=SecretMetaOut)
async def get_secret(
    secret_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(SecretV1).where(SecretV1.id == secret_id))
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="secret not found")
    return SecretMetaOut(
        id=row.id,
        namespace=row.namespace,
        key=row.key,
        created_at=row.created_at,
        updated_at=row.updated_at,
        value_present=True,
    )
