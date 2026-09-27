"""ai usage

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27 13:04:52.021462
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('ai_usage',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_ai_usage_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'day', name=op.f('pk_ai_usage'))
    )


def downgrade() -> None:
    op.drop_table('ai_usage')
