"""CMS Form model — user-defined web forms with submissions."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CmsForm(Base):
    __tablename__ = "cms_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # fields = [{id, type, label, required, options, placeholder, validation}]
    fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    submit_button_text: Mapped[str] = mapped_column(
        String(128), nullable=False, default="Submit", server_default="Submit"
    )
    success_message: Mapped[str] = mapped_column(
        Text, nullable=False, default="Thank you!", server_default="Thank you!"
    )

    # "store" | "email" | "webhook" | "both"
    action: Mapped[str] = mapped_column(
        String(16), nullable=False, default="store", server_default="store"
    )
    email_to: Mapped[str | None] = mapped_column(String(256), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CmsFormSubmission(Base):
    __tablename__ = "cms_form_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(
        ForeignKey("cms_forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
