"""add device_type column

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f7
Create Date: 2026-03-28 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5g6"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "devices",
        sa.Column("device_type", sa.String(32), nullable=True, server_default="unknown"),
    )


def downgrade():
    op.drop_column("devices", "device_type")
