"""Initial migration - complete schema

Revision ID: 20250223_0001_initial_migration
Revises:
Create Date: 2025-02-23 00:00:00.000000

All prior migrations merged into this single file:
  - users (all 31 columns: core, gmail, mfa, notifications, account_status, failed_otp_attempts)
  - password_history
  - email_providers
  - analysis_jobs
  - audit_logs
  - notifications
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20250223_0001_initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
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
        sa.Column('mfa_backup_codes', sa.Text(), nullable=True),                          # encrypted JSON string
        sa.Column('mfa_backup_codes_used', postgresql.ARRAY(sa.String(8)), nullable=True),

        # Gmail integration
        sa.Column('gmail_credentials', sa.Text(), nullable=True),
        sa.Column('gmail_email', sa.String(255), nullable=True),
        sa.Column('gmail_connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gmail_auto_scan', sa.Boolean(), server_default='false', nullable=False),

        # Notification preferences
        sa.Column('notification_preferences', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_normalized_email', 'users', ['normalized_email'])
    op.create_index('idx_user_role', 'users', ['role'])
    op.create_index('idx_user_account_status', 'users', ['account_status'])
    op.create_index('idx_user_created', 'users', ['created_at'])

    # ------------------------------------------------------------------
    # password_history
    # ------------------------------------------------------------------
    op.create_table(
        'password_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_password_history_user_id', 'password_history', ['user_id'])
    op.create_index('idx_password_history_created_at', 'password_history', ['created_at'])

    # ------------------------------------------------------------------
    # email_providers
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # analysis_jobs
    # ------------------------------------------------------------------
    op.create_table(
        'analysis_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(50), server_default='upload'),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('email_providers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('external_message_id', sa.String(500), nullable=True),

        # File metadata
        sa.Column('file_name', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('s3_key', sa.String(500), nullable=True),

        # Job state
        sa.Column('status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('progress_percent', sa.Integer(), server_default='0'),
        sa.Column('current_step', sa.String(100), nullable=True),

        # Results
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('threat_category', sa.String(100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('findings_count', sa.Integer(), server_default='0'),
        sa.Column('critical_findings', sa.Integer(), server_default='0'),
        sa.Column('high_findings', sa.Integer(), server_default='0'),
        sa.Column('medium_findings', sa.Integer(), server_default='0'),
        sa.Column('low_findings', sa.Integer(), server_default='0'),
        sa.Column('mongodb_result_id', sa.String(24), nullable=True),

        # Report
        sa.Column('report_generated', sa.Boolean(), server_default='false'),
        sa.Column('report_s3_key', sa.String(500), nullable=True),

        # Errors / retries
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_job_user_status', 'analysis_jobs', ['user_id', 'status'])
    op.create_index('idx_job_status_created', 'analysis_jobs', ['status', 'created_at'])
    op.create_index('idx_job_risk_score', 'analysis_jobs', ['risk_score'])
    op.create_index('idx_job_threat_category', 'analysis_jobs', ['threat_category'])
    op.create_index('idx_job_file_hash', 'analysis_jobs', ['file_hash'])

    # ------------------------------------------------------------------
    # audit_logs
    # ------------------------------------------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=True),
        sa.Column('request_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(50), server_default='success'),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('details', postgresql.JSONB(), server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_correlation_id', 'audit_logs', ['correlation_id'])
    op.create_index('idx_audit_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_action_created', 'audit_logs', ['action', 'created_at'])
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_ip', 'audit_logs', ['ip_address'])

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('analysis_jobs')
    op.drop_table('email_providers')
    op.drop_table('password_history')
    op.drop_table('users')