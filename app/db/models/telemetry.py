from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, DateTime, String, func, Index

from app.db.base import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB as _JSON_TYPE
except Exception:
    from sqlalchemy import JSON as _JSON_TYPE


class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"
    __table_args__ = (
        Index("ix_device_telemetry_device_received_at", "device_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True, nullable=False)

    received_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    event_type: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    payload: Mapped[dict] = mapped_column(_JSON_TYPE, nullable=False)
