from sqlalchemy import DateTime, String, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EffectV1(Base):
    __tablename__ = "effects_v1"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    effect_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
