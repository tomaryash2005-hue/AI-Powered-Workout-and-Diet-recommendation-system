"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-27 02:01:53.035453
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('meal_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('meal_type', sa.String(length=20), nullable=False),
    sa.Column('food_id', sa.String(length=50), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('servings', sa.Float(), nullable=False),
    sa.Column('calories', sa.Float(), nullable=False),
    sa.Column('protein_g', sa.Float(), nullable=False),
    sa.Column('carbs_g', sa.Float(), nullable=False),
    sa.Column('fat_g', sa.Float(), nullable=False),
    sa.Column('allergens', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_meal_logs_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_meal_logs'))
    )
    with op.batch_alter_table('meal_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_meal_logs_date'), ['date'], unique=False)
        batch_op.create_index(batch_op.f('ix_meal_logs_user_id'), ['user_id'], unique=False)

    op.create_table('plan_swaps',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('meal_type', sa.String(length=20), nullable=False),
    sa.Column('slot', sa.Integer(), nullable=False),
    sa.Column('food_id', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_plan_swaps_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'date', 'meal_type', 'slot', name=op.f('pk_plan_swaps'))
    )
    op.create_table('profiles',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('age', sa.Integer(), nullable=False),
    sa.Column('sex', sa.String(length=10), nullable=False),
    sa.Column('height_cm', sa.Float(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.Column('activity_level', sa.String(length=20), nullable=False),
    sa.Column('goal', sa.String(length=20), nullable=False),
    sa.Column('allergies', sa.JSON(), nullable=False),
    sa.Column('diet_type', sa.String(length=20), nullable=False),
    sa.Column('bmi_standard', sa.String(length=10), nullable=False),
    sa.Column('equipment', sa.String(length=20), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_profiles_user_id_users')),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_profiles'))
    )
    op.create_table('weight_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_weight_logs_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_weight_logs')),
    sa.UniqueConstraint('user_id', 'date', name=op.f('uq_weight_logs_user_id_date'))
    )
    with op.batch_alter_table('weight_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_weight_logs_user_id'), ['user_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('weight_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_weight_logs_user_id'))

    op.drop_table('weight_logs')
    op.drop_table('profiles')
    op.drop_table('plan_swaps')
    with op.batch_alter_table('meal_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_meal_logs_user_id'))
        batch_op.drop_index(batch_op.f('ix_meal_logs_date'))

    op.drop_table('meal_logs')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
