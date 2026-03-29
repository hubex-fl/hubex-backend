"""Semantic Types CRUD API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_db
from app.db.models.semantic_type import SemanticType, TriggerTemplate, UnitConversion
from app.schemas.semantic_type import (
    SemanticTypeCreate,
    SemanticTypePatch,
    SemanticTypeOut,
    SemanticTypeDetailOut,
    TriggerTemplateOut,
    UnitConversionOut,
)

router = APIRouter()


@router.get("/types/semantic", response_model=list[SemanticTypeOut])
async def list_semantic_types(
    builtin: Optional[bool] = Query(default=None),
    base_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SemanticType).order_by(SemanticType.name)
    if builtin is not None:
        stmt = stmt.where(SemanticType.is_builtin == builtin)
    if base_type:
        stmt = stmt.where(SemanticType.base_type == base_type)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.post("/types/semantic", response_model=SemanticTypeOut, status_code=201)
async def create_semantic_type(
    payload: SemanticTypeCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        select(SemanticType).where(SemanticType.name == payload.name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(422, f"Semantic type '{payload.name}' already exists")
    obj = SemanticType(**payload.model_dump(), is_builtin=False)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/types/semantic/{type_id}", response_model=SemanticTypeDetailOut)
async def get_semantic_type(type_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(
        select(SemanticType).where(SemanticType.id == type_id)
    )).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Semantic type not found")
    triggers = (await db.execute(
        select(TriggerTemplate).where(TriggerTemplate.semantic_type_id == type_id)
    )).scalars().all()
    conversions = (await db.execute(
        select(UnitConversion).where(UnitConversion.semantic_type_id == type_id)
    )).scalars().all()
    return SemanticTypeDetailOut(
        **SemanticTypeOut.model_validate(obj).model_dump(),
        triggers=[TriggerTemplateOut.model_validate(t) for t in triggers],
        conversions=[UnitConversionOut.model_validate(c) for c in conversions],
    )


@router.patch("/types/semantic/{type_id}", response_model=SemanticTypeOut)
async def update_semantic_type(
    type_id: int,
    payload: SemanticTypePatch,
    db: AsyncSession = Depends(get_db),
):
    obj = (await db.execute(
        select(SemanticType).where(SemanticType.id == type_id)
    )).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Semantic type not found")
    if obj.is_builtin:
        raise HTTPException(403, "Cannot modify built-in types")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/types/semantic/{type_id}", status_code=204)
async def delete_semantic_type(type_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(
        select(SemanticType).where(SemanticType.id == type_id)
    )).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Semantic type not found")
    if obj.is_builtin:
        raise HTTPException(403, "Cannot delete built-in types")
    await db.delete(obj)
    await db.commit()


@router.get("/types/semantic/{type_id}/triggers", response_model=list[TriggerTemplateOut])
async def list_triggers(type_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(TriggerTemplate).where(TriggerTemplate.semantic_type_id == type_id)
    )).scalars().all()
    return rows


@router.get("/types/semantic/{type_id}/conversions", response_model=list[UnitConversionOut])
async def list_conversions(type_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(UnitConversion).where(UnitConversion.semantic_type_id == type_id)
    )).scalars().all()
    return rows
