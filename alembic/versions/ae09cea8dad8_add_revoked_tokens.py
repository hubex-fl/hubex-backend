"""add revoked tokens

Revision ID: ae09cea8dad8
Revises: 9d2f1a7c6b34
Create Date: 2026-01-02 19:16:59.530266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ae09cea8dad8'
down_revision: Union[str, Sequence[str], None] = '9d2f1a7c6b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('revoked_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jti', sa.String(length=64), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_revoked_tokens_jti'), 'revoked_tokens', ['jti'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_revoked_tokens_jti'), table_name='revoked_tokens')
    op.drop_table('revoked_tokens')
