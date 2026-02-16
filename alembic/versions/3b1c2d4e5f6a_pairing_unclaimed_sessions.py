"""pairing unclaimed sessions

Revision ID: 3b1c2d4e5f6a
Revises: d9e8f7a6b5c4
Create Date: 2026-02-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3b1c2d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "d9e8f7a6b5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("pairing_sessions", "user_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("pairing_sessions", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(
        "uq_pairing_sessions_pairing_code",
        "pairing_sessions",
        ["pairing_code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_pairing_sessions_pairing_code", "pairing_sessions", type_="unique")
    op.drop_column("pairing_sessions", "claimed_at")
    op.alter_column("pairing_sessions", "user_id", existing_type=sa.Integer(), nullable=False)
