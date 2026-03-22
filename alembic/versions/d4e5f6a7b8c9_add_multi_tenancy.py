"""add multi-tenancy: organizations, org_users, org_id FKs

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False, server_default="free"),
        sa.Column("max_devices", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # 2. Create organization_users junction table
    op.create_table(
        "organization_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_organization_users_org_id", "organization_users", ["org_id"])
    op.create_index("ix_organization_users_user_id", "organization_users", ["user_id"])

    # 3. Seed a "default" organization for existing data
    op.execute(
        """
        INSERT INTO organizations (name, slug, plan, max_devices, max_users)
        VALUES ('Default Organization', 'default', 'free', 10, 3)
        """
    )

    # 4. Add org_id FK columns (nullable) to existing tables
    op.add_column("devices", sa.Column("org_id", sa.Integer(), nullable=True))
    op.create_index("ix_devices_org_id", "devices", ["org_id"])
    op.create_foreign_key("fk_devices_org_id", "devices", "organizations", ["org_id"], ["id"])

    op.add_column("entities", sa.Column("org_id", sa.Integer(), nullable=True))
    op.create_index("ix_entities_org_id", "entities", ["org_id"])
    op.create_foreign_key("fk_entities_org_id", "entities", "organizations", ["org_id"], ["id"])

    op.add_column("alert_rules", sa.Column("org_id", sa.Integer(), nullable=True))
    op.create_index("ix_alert_rules_org_id", "alert_rules", ["org_id"])
    op.create_foreign_key("fk_alert_rules_org_id", "alert_rules", "organizations", ["org_id"], ["id"])

    op.add_column("webhook_subscriptions", sa.Column("org_id", sa.Integer(), nullable=True))
    op.create_index("ix_webhook_subscriptions_org_id", "webhook_subscriptions", ["org_id"])
    op.create_foreign_key(
        "fk_webhook_subscriptions_org_id",
        "webhook_subscriptions",
        "organizations",
        ["org_id"],
        ["id"],
    )

    # 5. Assign existing rows to the default org
    op.execute("UPDATE devices SET org_id = (SELECT id FROM organizations WHERE slug = 'default') WHERE org_id IS NULL")
    op.execute("UPDATE entities SET org_id = (SELECT id FROM organizations WHERE slug = 'default') WHERE org_id IS NULL")
    op.execute("UPDATE alert_rules SET org_id = (SELECT id FROM organizations WHERE slug = 'default') WHERE org_id IS NULL")
    op.execute("UPDATE webhook_subscriptions SET org_id = (SELECT id FROM organizations WHERE slug = 'default') WHERE org_id IS NULL")


def downgrade() -> None:
    op.drop_constraint("fk_webhook_subscriptions_org_id", "webhook_subscriptions", type_="foreignkey")
    op.drop_index("ix_webhook_subscriptions_org_id", table_name="webhook_subscriptions")
    op.drop_column("webhook_subscriptions", "org_id")

    op.drop_constraint("fk_alert_rules_org_id", "alert_rules", type_="foreignkey")
    op.drop_index("ix_alert_rules_org_id", table_name="alert_rules")
    op.drop_column("alert_rules", "org_id")

    op.drop_constraint("fk_entities_org_id", "entities", type_="foreignkey")
    op.drop_index("ix_entities_org_id", table_name="entities")
    op.drop_column("entities", "org_id")

    op.drop_constraint("fk_devices_org_id", "devices", type_="foreignkey")
    op.drop_index("ix_devices_org_id", table_name="devices")
    op.drop_column("devices", "org_id")

    op.drop_table("organization_users")
    op.drop_table("organizations")
