"""add signals v1 stream/id index

Revision ID: d3e4f5a6b7c8
Revises: c8d1e4f6a7b2
Create Date: 2026-02-12 17:20:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c8d1e4f6a7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_signals_v1_stream_id", "signals_v1", ["stream", "id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_signals_v1_stream_id", table_name="signals_v1")

