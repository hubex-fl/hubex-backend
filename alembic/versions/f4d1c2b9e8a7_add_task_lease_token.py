"""add task lease_token

Revision ID: f4d1c2b9e8a7
Revises: c3b0f8d9a1e2
Create Date: 2025-12-19 04:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4d1c2b9e8a7"
down_revision: Union[str, Sequence[str], None] = "c3b0f8d9a1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tasks", sa.Column("lease_token", sa.String(length=128), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tasks", "lease_token")
