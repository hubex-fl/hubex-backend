"""add device_telemetry

Revision ID: 9f8c2b3f1a2d
Revises: 7b9f1e2a3c4d
Create Date: 2025-12-19 03:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9f8c2b3f1a2d"
down_revision: Union[str, Sequence[str], None] = "7b9f1e2a3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "device_telemetry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_device_telemetry_device_id", "device_telemetry", ["device_id"], unique=False)
    op.create_index("ix_device_telemetry_received_at", "device_telemetry", ["received_at"], unique=False)
    op.create_index("ix_device_telemetry_event_type", "device_telemetry", ["event_type"], unique=False)
    op.create_index(
        "ix_device_telemetry_device_received_at",
        "device_telemetry",
        ["device_id", "received_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_device_telemetry_device_received_at", table_name="device_telemetry")
    op.drop_index("ix_device_telemetry_event_type", table_name="device_telemetry")
    op.drop_index("ix_device_telemetry_received_at", table_name="device_telemetry")
    op.drop_index("ix_device_telemetry_device_id", table_name="device_telemetry")
    op.drop_table("device_telemetry")
