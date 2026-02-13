"""merge execution worker defs heads

Revision ID: d9e8f7a6b5c4
Revises: 801faeb5bf4b, b7c9d1e2f3a4
Create Date: 2026-02-13 03:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9e8f7a6b5c4"
down_revision: Union[str, Sequence[str], None] = ("801faeb5bf4b", "b7c9d1e2f3a4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
