"""
Audit Log Model - fixed: added OTP_SENT to AuditAction
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(36), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    status = Column(String(50), default="success")
    status_code = Column(Integer, nullable=True)
    details = Column(JSONB, default=dict)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_created_at", "created_at"),
        Index("idx_audit_action_created", "action", "created_at"),
        Index("idx_audit_status_created", "status", "created_at"),
        Index("idx_audit_user_created", "user_id", "created_at"),
        Index("idx_audit_action_status_created", "action", "status", "created_at"),
        Index("idx_audit_user_action_created", "user_id", "action", "created_at"),
        Index("idx_audit_user_status_created", "user_id", "status", "created_at"),
        Index("idx_audit_user_action_status_created", "user_id", "action", "status", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_ip", "ip_address"),
        Index("idx_audit_ip_created", "ip_address", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user={self.user_email})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "user_email": self.user_email,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "status": self.status,
            "status_code": self.status_code,
            "details": self.details,
            "error_message": self.error_message,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditAction:
    # Authentication
    LOGIN = "login"
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"

    # OTP  — FIX: was missing, caused AttributeError in resend_otp endpoint
    OTP_SENT = "otp_sent"
    OTP_VERIFIED = "otp_verified"
    OTP_FAILED = "otp_failed"

    # MFA
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_SETUP_INITIATED = "mfa_setup_initiated"
    MFA_CHALLENGE = "mfa_challenge"
    MFA_SUCCESS = "mfa_success"
    MFA_FAILURE = "mfa_failure"
    MFA_REQUIRED = "mfa_required"
    MFA_BACKUP_CODE_USED = "mfa_backup_code_used"

    # User management
    USER_REGISTERED = "user_registered"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    EMAIL_VERIFIED = "email_verified"

    # Account security
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # Email providers
    PROVIDER_CONNECTED = "provider_connected"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    PROVIDER_SYNC_STARTED = "provider_sync_started"
    PROVIDER_SYNC_COMPLETED = "provider_sync_completed"
    PROVIDER_SYNC_FAILED = "provider_sync_failed"

    # Analysis
    ANALYSIS_CREATED = "analysis_created"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    ANALYSIS_DELETED = "analysis_deleted"
    REPORT_DOWNLOADED = "report_downloaded"

    # Admin
    ADMIN_USER_CREATED = "admin_user_created"
    ADMIN_USER_UPDATED = "admin_user_updated"
    ADMIN_USER_DELETED = "admin_user_deleted"
    SYSTEM_SETTING_CHANGED = "system_setting_changed"