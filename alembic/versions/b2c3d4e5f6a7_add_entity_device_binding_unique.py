"""add unique constraint on entity_device_bindings(entity_id, device_id)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_entity_device_binding",
        "entity_device_bindings",
        ["entity_id", "device_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_entity_device_binding", "entity_device_bindings", type_="unique")
