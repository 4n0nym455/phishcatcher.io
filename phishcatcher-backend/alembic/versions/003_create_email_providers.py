"""Create email_providers table

Revision ID: 003_create_email_providers
Revises: 002_create_password_history
Create Date: 2025-02-23 00:00:02.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_create_email_providers'
down_revision = '002_create_password_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'email_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('provider_name', sa.String(100), nullable=True),
        sa.Column('email_address', sa.String(255), nullable=False),
        
        # OAuth tokens
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # IMAP fallback
        sa.Column('imap_host', sa.String(255), nullable=True),
        sa.Column('imap_port', sa.Integer(), server_default='993'),
        sa.Column('imap_username', sa.String(255), nullable=True),
        sa.Column('imap_password', sa.Text(), nullable=True),
        sa.Column('imap_use_ssl', sa.Boolean(), server_default='true'),
        
        # Sync config
        sa.Column('sync_enabled', sa.Boolean(), server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_history_id', sa.String(255), nullable=True),
        sa.Column('sync_frequency_minutes', sa.Integer(), server_default='15'),
        sa.Column('sync_folder', sa.String(100), server_default='INBOX'),
        sa.Column('sync_filter', sa.String(255), nullable=True),
        sa.Column('max_emails_per_sync', sa.Integer(), server_default='100'),
        
        # Webhook / push
        sa.Column('webhook_enabled', sa.Boolean(), server_default='false'),
        sa.Column('webhook_resource_id', sa.String(255), nullable=True),
        sa.Column('webhook_expiration', sa.DateTime(timezone=True), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_connected', sa.Boolean(), server_default='false'),
        sa.Column('connection_error', sa.Text(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index('idx_provider_user_type', 'email_providers', ['user_id', 'provider_type'])
    op.create_index('idx_provider_active', 'email_providers', ['is_active', 'sync_enabled'])
    op.create_index('idx_provider_sync', 'email_providers', ['last_sync_at'])


def downgrade() -> None:
    op.drop_table('email_providers')
