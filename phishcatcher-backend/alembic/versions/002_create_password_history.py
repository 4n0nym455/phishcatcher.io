"""Create password_history table

Revision ID: 002_create_password_history
Revises: 001_create_users
Create Date: 2025-02-23 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_create_password_history'
down_revision = '001_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'password_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('idx_password_history_user_id', 'password_history', ['user_id'])
    op.create_index('idx_password_history_created_at', 'password_history', ['created_at'])


def downgrade() -> None:
    op.drop_table('password_history')
