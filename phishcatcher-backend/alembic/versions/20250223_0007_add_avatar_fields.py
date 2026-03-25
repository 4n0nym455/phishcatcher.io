"""Add avatar fields to users table

Revision ID: 20250223_0007_add_avatar_fields
Revises: 20250223_0006_create_notifications
Create Date: 2025-02-23 00:00:07.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20250223_0007_add_avatar_fields'
down_revision = '20250223_0006_create_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_object_name', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('avatar_bucket', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('avatar_content_type', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_content_type')
    op.drop_column('users', 'avatar_bucket')
    op.drop_column('users', 'avatar_object_name')
