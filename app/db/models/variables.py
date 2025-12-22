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
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    min_value: Mapped[float | None] = mapped_column(nullable=True)
    max_value: Mapped[float | None] = mapped_column(nullable=True)
    enum_values: Mapped[list | None] = mapped_column(_JSON_TYPE, nullable=True)
    regex: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    user_writable: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    device_writable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    allow_device_override: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
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
            "user_id",
            name="uq_variable_values_key_device_scope",
        ),
        Index("ix_variable_values_variable_key", "variable_key"),
        Index("ix_variable_values_device_id", "device_id"),
        Index("ix_variable_values_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    variable_key: Mapped[str] = mapped_column(
        ForeignKey("variable_definitions.key"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
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


class VariableSnapshot(Base):
    __tablename__ = "variable_snapshots"
    __table_args__ = (
        Index("ix_variable_snapshots_device_id", "device_id"),
        Index("ix_variable_snapshots_resolved_at", "resolved_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_version: Mapped[str] = mapped_column(String(64), nullable=False)


class VariableSnapshotItem(Base):
    __tablename__ = "variable_snapshot_items"
    __table_args__ = (
        Index("ix_variable_snapshot_items_snapshot_id", "snapshot_id"),
        Index("ix_variable_snapshot_items_key", "variable_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("variable_snapshots.id"), nullable=False
    )
    variable_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        _JSON_TYPE, nullable=True
    )
    masked: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    precedence: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    resolved_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    constraints: Mapped[dict | None] = mapped_column(_JSON_TYPE, nullable=True)


class VariableAppliedAck(Base):
    __tablename__ = "variable_applied_acks"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "device_id",
            "variable_key",
            "version",
            name="uq_variable_applied_ack",
        ),
        Index("ix_variable_applied_snapshot", "snapshot_id"),
        Index("ix_variable_applied_device", "device_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("variable_snapshots.id"), nullable=False
    )
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    variable_key: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
