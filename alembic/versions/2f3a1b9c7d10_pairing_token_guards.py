"""pairing token guards

Revision ID: 2f3a1b9c7d10
Revises: f4d1c2b9e8a7
Create Date: 2025-12-20 14:25:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2f3a1b9c7d10"
down_revision = "f4d1c2b9e8a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_pairing_sessions_device_uid_pairing_code",
        "pairing_sessions",
        ["device_uid", "pairing_code"],
    )
    op.create_index(
        "uq_device_tokens_active_device_id",
        "device_tokens",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_device_tokens_active_device_id", table_name="device_tokens")
    op.drop_constraint(
        "uq_pairing_sessions_device_uid_pairing_code",
        "pairing_sessions",
        type_="unique",
    )
