"""add embed_config and kiosk_config to dashboards

Revision ID: c4d5e6f7a8b9
Revises: a2b3c4d5e6f7
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dashboards", sa.Column("embed_config", sa.JSON(), nullable=True))
    op.add_column("dashboards", sa.Column("kiosk_config", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("dashboards", "kiosk_config")
    op.drop_column("dashboards", "embed_config")
