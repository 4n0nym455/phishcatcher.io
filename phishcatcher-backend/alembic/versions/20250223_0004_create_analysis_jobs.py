"""Create analysis_jobs table

Revision ID: 20250223_0004_create_analysis_jobs
Revises: 20250223_0003_create_email_providers
Create Date: 2025-02-23 00:00:03.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20250223_0004_create_analysis_jobs'
down_revision = '20250223_0003_create_email_providers'
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_table('analysis_jobs')
