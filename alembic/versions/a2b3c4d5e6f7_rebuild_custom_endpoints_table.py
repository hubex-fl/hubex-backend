"""Rebuild custom_endpoints table with full Custom API Builder schema.

Revision ID: a2b3c4d5e6f7
Revises: f7a8b9c0d1e2
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old table if it exists (stub from earlier scaffold)
    op.drop_table("custom_endpoints")

    op.create_table(
        "custom_endpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("path", sa.String(length=200), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False, server_default="GET"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_config", sa.JSON(), nullable=False),
        sa.Column("auth_type", sa.String(length=20), nullable=False, server_default="api_key"),
        sa.Column("api_key", sa.String(length=64), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("write_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custom_endpoints_org_id", "custom_endpoints", ["org_id"])
    op.create_index(
        "ix_custom_endpoints_path", "custom_endpoints", ["path"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_custom_endpoints_path", table_name="custom_endpoints")
    op.drop_index("ix_custom_endpoints_org_id", table_name="custom_endpoints")
    op.drop_table("custom_endpoints")
