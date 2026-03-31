from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sharing_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="private", server_default="private"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    widgets: Mapped[list["DashboardWidget"]] = relationship(
        "DashboardWidget",
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="DashboardWidget.sort_order",
    )


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # widget_type: sparkline, line_chart, gauge, bool, log, json, map, image,
    #              toggle_control, slider_control
    widget_type: Mapped[str] = mapped_column(String(32), nullable=False)
    variable_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    display_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Grid placement (column-based, 12-col grid)
    grid_col: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    grid_row: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    grid_span_w: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default="4")
    grid_span_h: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="widgets")
