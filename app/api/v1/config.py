from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.features import (
    FEATURES,
    is_feature_enabled,
    set_feature_enabled,
)
from app.db.models.config import ConfigV1
from app.db.models.feature_flag import FeatureFlag

router = APIRouter(prefix="/config", tags=["config"])


class ConfigMetaOut(BaseModel):
    id: int
    namespace: str
    key: str
    created_at: datetime
    updated_at: datetime


class FeatureFlagOut(BaseModel):
    key: str
    name: str
    description: str
    category: str
    default: bool
    requires: list[str]
    enabled: bool
    updated_at: datetime | None = None
    updated_by: str | None = None


class FeatureFlagsListOut(BaseModel):
    features: list[FeatureFlagOut]
    categories: list[str]
    total: int
    enabled_count: int


class FeatureFlagPatch(BaseModel):
    enabled: bool


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


# NOTE: the /features routes MUST come before /{config_id} below,
# otherwise FastAPI's path matching treats "features" as an integer id.
@router.get("/features", response_model=FeatureFlagsListOut)
async def list_feature_flags(db: AsyncSession = Depends(get_db)):
    """List every togglable feature with its current runtime state."""
    rows_res = await db.execute(select(FeatureFlag))
    rows = {row.key: row for row in rows_res.scalars().all()}

    out: list[FeatureFlagOut] = []
    categories: set[str] = set()
    enabled_count = 0
    for key, feat in FEATURES.items():
        categories.add(feat.category)
        row = rows.get(key)
        enabled = bool(row.enabled) if row is not None else feat.default
        if enabled:
            enabled_count += 1
        out.append(
            FeatureFlagOut(
                key=feat.key,
                name=feat.name,
                description=feat.description,
                category=feat.category,
                default=feat.default,
                requires=list(feat.requires),
                enabled=enabled,
                updated_at=row.updated_at if row is not None else None,
                updated_by=row.updated_by if row is not None else None,
            )
        )

    out.sort(key=lambda x: (x.category, x.key))
    return FeatureFlagsListOut(
        features=out,
        categories=sorted(categories),
        total=len(out),
        enabled_count=enabled_count,
    )


@router.put("/features/{key}", response_model=FeatureFlagOut)
async def update_feature_flag(
    key: str,
    body: FeatureFlagPatch,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a feature at runtime.

    When enabling, also verifies that all ``requires`` dependencies are enabled.
    """
    feat = FEATURES.get(key)
    if feat is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "FEATURE_UNKNOWN", "message": f"unknown feature '{key}'"},
        )

    if body.enabled:
        for dep in feat.requires:
            if not await is_feature_enabled(db, dep):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "FEATURE_DEPENDENCY_DISABLED",
                        "message": f"cannot enable '{key}' — dependency '{dep}' is disabled",
                        "dependency": dep,
                    },
                )

    actor_id = getattr(request.state, "user_id", None)
    actor_type = "user" if actor_id else None

    row = await set_feature_enabled(
        db,
        key,
        body.enabled,
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id else None,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "FEATURE_UNKNOWN", "message": f"unknown feature '{key}'"},
        )

    return FeatureFlagOut(
        key=feat.key,
        name=feat.name,
        description=feat.description,
        category=feat.category,
        default=feat.default,
        requires=list(feat.requires),
        enabled=row.enabled,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


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
