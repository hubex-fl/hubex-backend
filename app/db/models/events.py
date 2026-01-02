from sqlalchemy import BigInteger, DateTime, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventV1(Base):
    __tablename__ = "events_v1"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stream: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    ts: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class EventV1Checkpoint(Base):
    __tablename__ = "events_v1_checkpoints"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stream: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subscriber_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    cursor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
