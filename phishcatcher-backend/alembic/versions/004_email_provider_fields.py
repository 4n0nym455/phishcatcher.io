"""Email provider field additions - is_default for multi-account support

Revision ID: 004
Revises: 003
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('email_providers', sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('email_providers', 'is_default')
