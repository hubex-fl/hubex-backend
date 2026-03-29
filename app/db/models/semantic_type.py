"""Semantic type system models."""
from __future__ import annotations

from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SemanticType(Base):
    __tablename__ = "semantic_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_type: Mapped[str] = mapped_column(String(16), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit_symbol: Mapped[str | None] = mapped_column(String(8), nullable=True)
    value_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_viz_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TriggerTemplate(Base):
    __tablename__ = "trigger_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    semantic_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("semantic_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_name: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    config_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UnitConversion(Base):
    __tablename__ = "unit_conversions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    semantic_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("semantic_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    to_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    formula: Mapped[str] = mapped_column(String(128), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
