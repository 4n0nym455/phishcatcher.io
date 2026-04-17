"""User field additions - Avatar fields, Storage fields, Signing key

Revision ID: 003
Revises: 002
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add avatar fields to users
    op.add_column('users', sa.Column('avatar_object_name', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('avatar_bucket', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('avatar_content_type', sa.String(100), nullable=True))

    # Add storage fields to analysis_jobs
    op.add_column('analysis_jobs', sa.Column('storage_object_name', sa.String(500), nullable=True))
    op.add_column('analysis_jobs', sa.Column('storage_bucket', sa.String(255), nullable=True))

    # Add signing_key_hash to users
    op.add_column('users', sa.Column('signing_key_hash', sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'signing_key_hash')
    op.drop_column('analysis_jobs', 'storage_bucket')
    op.drop_column('analysis_jobs', 'storage_object_name')
    op.drop_column('users', 'avatar_content_type')
    op.drop_column('users', 'avatar_bucket')
    op.drop_column('users', 'avatar_object_name')
