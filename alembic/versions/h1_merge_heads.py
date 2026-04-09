"""merge multiple heads

Revision ID: h1_merge_heads
Revises: c4d5e6f7a8b9, g1a2b3c4d5e6
Create Date: 2026-04-09

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "h1_merge_heads"
down_revision = ("c4d5e6f7a8b9", "g1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
