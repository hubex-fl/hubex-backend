from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, String, DateTime, func, JSON
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Sprint 10 F9: optional display name shown instead of email in the UI
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    caps: Mapped[JSON] = mapped_column(JSON, nullable=True)
    preferences: Mapped[JSON] = mapped_column(JSON, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
