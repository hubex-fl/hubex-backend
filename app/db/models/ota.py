from __future__ import annotations
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FirmwareVersion(Base):
    __tablename__ = "firmware_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    binary_url: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_hw_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OtaRollout(Base):
    __tablename__ = "ota_rollouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    firmware_id: Mapped[int] = mapped_column(
        ForeignKey("firmware_versions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # immediate / staged / canary
    strategy: Mapped[str] = mapped_column(String(16), nullable=False)
    target_filter: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # pending / active / paused / completed / failed
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DeviceOtaStatus(Base):
    __tablename__ = "device_ota_status"

    __table_args__ = (
        UniqueConstraint("device_id", "rollout_id", name="uq_device_rollout"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id"), nullable=False, index=True
    )
    rollout_id: Mapped[int] = mapped_column(
        ForeignKey("ota_rollouts.id"), nullable=False, index=True
    )
    firmware_id: Mapped[int] = mapped_column(
        ForeignKey("firmware_versions.id"), nullable=False
    )
    # pending / downloading / flashing / done / failed / skipped
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
