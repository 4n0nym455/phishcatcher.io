"""Add MinIO storage fields to analysis_jobs

Revision ID: 20250223_0008_add_storage_fields
Revises: 20250223_0007_add_avatar_fields
Create Date: 2025-02-23 00:00:08.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '20250223_0008_add_storage_fields'
down_revision = '20250223_0007_add_avatar_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('analysis_jobs', sa.Column('storage_object_name', sa.String(500), nullable=True))
    op.add_column('analysis_jobs', sa.Column('storage_bucket', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis_jobs', 'storage_bucket')
    op.drop_column('analysis_jobs', 'storage_object_name')
