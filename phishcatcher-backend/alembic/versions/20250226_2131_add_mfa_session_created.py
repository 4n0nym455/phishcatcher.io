"""Add mfa_session_created column to users table

Revision ID: 20250226_2131
Revises: 20250226_2130_norm_email
Create Date: 2026-02-28 12:14:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250226_2131'
down_revision = '20250226_2130_norm_email'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add mfa_session_created column to users table
    op.add_column('users', 'mfa_session_created', sa.DateTime(timezone=True), nullable=True)


def downgrade() -> None:
    # Remove mfa_session_created column from users table
    op.drop_column('users', 'mfa_session_created')
