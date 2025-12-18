from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func, ForeignKey, Boolean, JSON

from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)

    # vom Gerät: stabiler Identifier (MAC/Chip-ID/Seriennr)
    device_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # vom User vergebener Name (unique pro User wäre später enforcebar)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Telemetrie / Fingerprint
    firmware_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Last-seen
    last_seen_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
