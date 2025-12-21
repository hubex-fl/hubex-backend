"""merge heads (pairing + variables v2)

Revision ID: af7caca26c62
Revises: 2f3a1b9c7d10, f1b2c3d4e5f6
Create Date: 2025-12-21 13:00:46.548666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af7caca26c62'
down_revision: Union[str, Sequence[str], None] = ('2f3a1b9c7d10', 'f1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
