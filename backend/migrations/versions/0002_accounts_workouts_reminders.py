"""accounts workouts reminders

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27 02:39:17.868132
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_reset_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_password_reset_tokens')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_password_reset_tokens_token_hash'))
    )
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_password_reset_tokens_user_id'), ['user_id'], unique=False)

    op.create_table('push_subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('endpoint', sa.String(length=1000), nullable=False),
    sa.Column('p256dh', sa.String(length=200), nullable=False),
    sa.Column('auth', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_push_subscriptions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_push_subscriptions')),
    sa.UniqueConstraint('endpoint', name=op.f('uq_push_subscriptions_endpoint'))
    )
    with op.batch_alter_table('push_subscriptions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_push_subscriptions_user_id'), ['user_id'], unique=False)

    op.create_table('reminder_deliveries',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('local_date', sa.Date(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reminder_deliveries_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'kind', 'local_date', name=op.f('pk_reminder_deliveries'))
    )
    op.create_table('reminder_settings',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('meals_enabled', sa.Boolean(), nullable=False),
    sa.Column('breakfast_time', sa.String(length=5), nullable=False),
    sa.Column('lunch_time', sa.String(length=5), nullable=False),
    sa.Column('dinner_time', sa.String(length=5), nullable=False),
    sa.Column('weigh_in_enabled', sa.Boolean(), nullable=False),
    sa.Column('weigh_in_weekday', sa.Integer(), nullable=False),
    sa.Column('weigh_in_time', sa.String(length=5), nullable=False),
    sa.Column('workout_enabled', sa.Boolean(), nullable=False),
    sa.Column('workout_time', sa.String(length=5), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reminder_settings_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_reminder_settings'))
    )
    op.create_table('workout_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('duration_min', sa.Integer(), nullable=True),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_workout_logs_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workout_logs'))
    )
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_logs_date'), ['date'], unique=False)
        batch_op.create_index(batch_op.f('ix_workout_logs_user_id'), ['user_id'], unique=False)

    op.create_table('workout_sets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workout_id', sa.Integer(), nullable=False),
    sa.Column('exercise', sa.String(length=120), nullable=False),
    sa.Column('set_number', sa.Integer(), nullable=False),
    sa.Column('reps', sa.Integer(), nullable=True),
    sa.Column('weight_kg', sa.Float(), nullable=True),
    sa.Column('duration_s', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['workout_id'], ['workout_logs.id'], name=op.f('fk_workout_sets_workout_id_workout_logs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workout_sets'))
    )
    with op.batch_alter_table('workout_sets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_sets_workout_id'), ['workout_id'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('token_version', sa.Integer(), server_default='0', nullable=False))



def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('token_version')

    with op.batch_alter_table('workout_sets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_sets_workout_id'))

    op.drop_table('workout_sets')
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_logs_user_id'))
        batch_op.drop_index(batch_op.f('ix_workout_logs_date'))

    op.drop_table('workout_logs')
    op.drop_table('reminder_settings')
    op.drop_table('reminder_deliveries')
    with op.batch_alter_table('push_subscriptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_push_subscriptions_user_id'))

    op.drop_table('push_subscriptions')
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_password_reset_tokens_user_id'))

    op.drop_table('password_reset_tokens')
