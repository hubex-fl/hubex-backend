from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
    Text,
    Index,
    UniqueConstraint,
    func,
    text,
)

from app.db.base import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB as _JSON_TYPE
except Exception:
    from sqlalchemy import JSON as _JSON_TYPE


class VariableDefinition(Base):
    __tablename__ = "variable_definitions"
    __table_args__ = (
        Index("ix_variable_definitions_scope", "scope"),
    )

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    default_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        _JSON_TYPE, nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class VariableValue(Base):
    __tablename__ = "variable_values"
    __table_args__ = (
        UniqueConstraint(
            "variable_key",
            "device_id",
            "scope",
            name="uq_variable_values_key_device_scope",
        ),
        Index("ix_variable_values_variable_key", "variable_key"),
        Index("ix_variable_values_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    variable_key: Mapped[str] = mapped_column(
        ForeignKey("variable_definitions.key"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        _JSON_TYPE, nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)


class VariableAudit(Base):
    __tablename__ = "variable_audits"
    __table_args__ = (
        Index("ix_variable_audits_key_created", "variable_key", "created_at"),
        Index("ix_variable_audits_device", "device_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    variable_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    old_value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        _JSON_TYPE, nullable=True
    )
    new_value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        _JSON_TYPE, nullable=True
    )
    old_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
