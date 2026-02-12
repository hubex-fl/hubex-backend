from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base


RUN_STATUS_REQUESTED = "requested"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELED = "canceled"

RUN_STATUS_ALLOWED: set[str] = {
    RUN_STATUS_REQUESTED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_CANCELED,
}
RUN_STATUS_FINAL: set[str] = {RUN_STATUS_COMPLETED, RUN_STATUS_FAILED, RUN_STATUS_CANCELED}


class ExecutionDefinition(Base):
    __tablename__ = "execution_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    runs: Mapped[list["ExecutionRun"]] = relationship(
        "ExecutionRun", back_populates="definition", lazy="selectin"
    )


class ExecutionRun(Base):
    __tablename__ = "execution_runs"
    __table_args__ = (
        UniqueConstraint(
            "definition_id",
            "idempotency_key",
            name="uq_execution_runs_definition_id_idempotency_key",
        ),
        Index("ix_execution_runs_definition_id_id", "definition_id", "id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    definition_id: Mapped[int] = mapped_column(ForeignKey("execution_definitions.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    definition: Mapped[ExecutionDefinition] = relationship("ExecutionDefinition", back_populates="runs", lazy="joined")

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        if value not in RUN_STATUS_ALLOWED:
            raise ValueError("invalid status")
        cur = getattr(self, "status", None)
        if cur in RUN_STATUS_FINAL and value != cur:
            raise ValueError("final status is immutable")
        return value

    @validates("input_json")
    def _validate_input_json(self, _key: str, value: dict) -> dict:
        cur = getattr(self, "input_json", None)
        if cur is not None and value != cur:
            raise ValueError("input_json is write-once")
        return value

    @validates("output_json")
    def _validate_output_json(self, _key: str, value: dict | None) -> dict | None:
        cur = getattr(self, "output_json", None)
        if cur is not None and value != cur:
            raise ValueError("output_json is write-once")
        if value is not None and getattr(self, "error_json", None) is not None:
            raise ValueError("cannot set output_json when error_json is set")
        return value

    @validates("error_json")
    def _validate_error_json(self, _key: str, value: dict | None) -> dict | None:
        cur = getattr(self, "error_json", None)
        if cur is not None and value != cur:
            raise ValueError("error_json is write-once")
        if value is not None and getattr(self, "output_json", None) is not None:
            raise ValueError("cannot set error_json when output_json is set")
        return value
