from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func

from app.db.base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    revoked_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
