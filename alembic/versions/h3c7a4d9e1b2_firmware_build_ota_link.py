"""Sprint 7 — link firmware_builds to ota_rollouts

Adds ``ota_rollout_id`` column to ``firmware_builds`` so the Sprint 4
Firmware Builder can push a successful build into the existing Sprint 3
(M14b) OTA rollout infrastructure in one click. The column is nullable
because unpromoted builds exist (e.g. "just download the .bin"), and
builds that never get promoted never get a rollout id.

Revision ID: h3c7a4d9e1b2
Revises: h2a1b2c3d4e5
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

revision = "h3c7a4d9e1b2"
down_revision = "h2a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "firmware_builds",
        sa.Column(
            "ota_rollout_id",
            sa.Integer(),
            sa.ForeignKey("ota_rollouts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_firmware_builds_ota_rollout_id",
        "firmware_builds",
        ["ota_rollout_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_firmware_builds_ota_rollout_id", "firmware_builds")
    op.drop_column("firmware_builds", "ota_rollout_id")
