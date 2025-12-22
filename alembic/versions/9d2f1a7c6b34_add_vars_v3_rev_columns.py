"""add vars v3 effective_rev and runtime rev tracking

Revision ID: 9d2f1a7c6b34
Revises: 6b8b7c4c1d2a
Create Date: 2025-12-23 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d2f1a7c6b34"
down_revision: Union[str, Sequence[str], None] = "6b8b7c4c1d2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "variable_snapshots",
        sa.Column("effective_rev", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "device_runtime_settings",
        sa.Column("last_effective_rev", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "device_runtime_settings",
        sa.Column("last_applied_rev", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "device_runtime_settings",
        sa.Column("last_acked_rev", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("device_runtime_settings", "last_acked_rev")
    op.drop_column("device_runtime_settings", "last_applied_rev")
    op.drop_column("device_runtime_settings", "last_effective_rev")
    op.drop_column("variable_snapshots", "effective_rev")
