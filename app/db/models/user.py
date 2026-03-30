from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func, JSON
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    caps: Mapped[JSON] = mapped_column(JSON, nullable=True)
    preferences: Mapped[JSON] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
