from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Index, func, text

from app.db.base import Base


class DeviceRuntimeSetting(Base):
    __tablename__ = "device_runtime_settings"
    __table_args__ = (
        Index("ix_device_runtime_settings_device_id", "device_id"),
    )

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    telemetry_interval_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_effective_rev: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_applied_rev: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_acked_rev: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
