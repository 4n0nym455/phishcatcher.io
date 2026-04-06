"""Create users table

Revision ID: 001_create_users
Revises: 
Create Date: 2025-02-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_create_users'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Core identity
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('normalized_email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        
        # Role & permissions
        sa.Column('role', sa.String(50), server_default='user', nullable=False),
        sa.Column('permissions', postgresql.ARRAY(sa.String()), server_default='{}', nullable=False),
        
        # Account state
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('account_status', sa.String(20), server_default='pending', nullable=False),
        
        # Security / lockout
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0'),
        sa.Column('failed_otp_attempts', sa.Integer(), server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Session tracking
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(45), nullable=True),
        
        # MFA
        sa.Column('mfa_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('mfa_secret', sa.String(255), nullable=True),
        sa.Column('mfa_session_created', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mfa_backup_codes', sa.Text(), nullable=True),
        sa.Column('mfa_backup_codes_used', postgresql.ARRAY(sa.String(8)), nullable=True),
        
        # Gmail integration
        sa.Column('gmail_credentials', sa.Text(), nullable=True),
        sa.Column('gmail_email', sa.String(255), nullable=True),
        sa.Column('gmail_connected_at', sa.DateTime(timezone=True), nullable=True),
        
        # Notification preferences
        sa.Column('notification_preferences', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Indexes
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_normalized_email', 'users', ['normalized_email'])
    op.create_index('idx_user_role', 'users', ['role'])
    op.create_index('idx_user_account_status', 'users', ['account_status'])
    op.create_index('idx_user_created', 'users', ['created_at'])


def downgrade() -> None:
    op.drop_table('users')
