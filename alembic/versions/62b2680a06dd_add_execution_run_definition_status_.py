"""add execution run definition status index

Revision ID: 62b2680a06dd
Revises: e8f13c318a91
Create Date: 2026-02-13 15:28:10.847932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62b2680a06dd'
down_revision: Union[str, Sequence[str], None] = 'e8f13c318a91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_execution_runs_definition_status_id",
        "execution_runs",
        ["definition_id", "status", "id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_execution_runs_definition_status_id", table_name="execution_runs")
