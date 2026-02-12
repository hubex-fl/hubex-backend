"""scope signal idempotency to stream

Revision ID: e4f1a2b3c4d5
Revises: d3e4f5a6b7c8
Create Date: 2026-02-12 17:10:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_signals_v1_idempotency_key", "signals_v1", type_="unique")
    op.create_unique_constraint(
        "uq_signals_v1_stream_idempotency_key",
        "signals_v1",
        ["stream", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_signals_v1_stream_idempotency_key", "signals_v1", type_="unique")
    op.create_unique_constraint(
        "uq_signals_v1_idempotency_key",
        "signals_v1",
        ["idempotency_key"],
    )

