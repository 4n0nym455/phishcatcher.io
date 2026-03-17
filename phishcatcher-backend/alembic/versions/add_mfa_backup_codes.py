"""Add MFA backup codes

Revision ID: 20250301_1200_mfa_backup_codes
Revises: 20250227_0001_notifications
Create Date: 2026-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20250301_1200_mfa_backup_codes'
down_revision = '20250227_0001_notifications'
branch_labels = None
depends_on = None

def upgrade():
    """Add MFA backup codes columns to users table."""
    # Add backup codes columns
    op.add_column('users', sa.Column('mfa_backup_codes', sa.ARRAY(sa.String(8)), nullable=True))
    op.add_column('users', sa.Column('mfa_backup_codes_used', sa.ARRAY(sa.String(8)), nullable=True))

def downgrade():
    """Remove MFA backup codes columns from users table."""
    op.drop_column('users', 'mfa_backup_codes_used')
    op.drop_column('users', 'mfa_backup_codes')
