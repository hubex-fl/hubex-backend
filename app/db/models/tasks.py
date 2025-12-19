from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    ForeignKey,
    DateTime,
    String,
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


class ExecutionContext(Base):
    __tablename__ = "execution_contexts"
    __table_args__ = (
        UniqueConstraint("client_id", "context_key", name="uq_execution_context_client_key"),
        Index("ix_execution_contexts_client_last_seen", "client_id", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    context_key: Mapped[str] = mapped_column(String(128), nullable=False)
    capabilities: Mapped[dict] = mapped_column(
        _JSON_TYPE, nullable=False, server_default=text("'{}'::jsonb")
    )
    meta: Mapped[dict] = mapped_column(
        _JSON_TYPE, nullable=False, server_default=text("'{}'::jsonb")
    )
    last_seen_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_client_status_priority_created", "client_id", "status", "priority", "created_at"),
        Index("ix_tasks_lease_expires_at", "lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    execution_context_id: Mapped[int | None] = mapped_column(
        ForeignKey("execution_contexts.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(_JSON_TYPE, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    claimed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(_JSON_TYPE, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
