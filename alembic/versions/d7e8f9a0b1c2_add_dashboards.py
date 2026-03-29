"""add dashboards and dashboard_widgets tables

Revision ID: d7e8f9a0b1c2
Revises: 54b50ffdaa88
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa

revision = "d7e8f9a0b1c2"
down_revision = "54b50ffdaa88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("sharing_mode", sa.String(length=16), nullable=False, server_default="private"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboards_owner_id", "dashboards", ["owner_id"])

    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("widget_type", sa.String(length=32), nullable=False),
        sa.Column("variable_key", sa.String(length=128), nullable=False),
        sa.Column("device_uid", sa.String(length=128), nullable=True),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("display_config", sa.JSON(), nullable=True),
        sa.Column("grid_col", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grid_row", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grid_span_w", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("grid_span_h", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_widgets_dashboard_id", "dashboard_widgets", ["dashboard_id"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_widgets_dashboard_id", table_name="dashboard_widgets")
    op.drop_table("dashboard_widgets")
    op.drop_index("ix_dashboards_owner_id", table_name="dashboards")
    op.drop_table("dashboards")
