"""
User Model

This module defines the User model with security features including:
- Password hashing with bcrypt
- Role-based access control
- Email verification
- Account status tracking
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index, Integer, Boolean, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, JSON as PostgreSQLJSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base
from .password_history import PasswordHistory

class User(Base):
    """User model with security features."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    normalized_email = Column(String(255), nullable=False, index=True)  # For alias detection
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    full_name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    avatar_object_name = Column(String(500), nullable=True)
    avatar_bucket = Column(String(100), nullable=True)
    avatar_content_type = Column(String(100), nullable=True)
    
    # Role and permissions
    role = Column(String(50), default="user", nullable=False)  # user, admin
    permissions = Column(ARRAY(String), default=list, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    account_status = Column(String(20), default="pending", nullable=False)  # pending, active, suspended
    
    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    failed_otp_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 compatible
    
    # MFA settings
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    mfa_session_created = Column(DateTime(timezone=True), nullable=True)  # When MFA session was created
    
    # MFA backup codes for account recovery (stored encrypted)
    mfa_backup_codes = Column(Text, nullable=True)  # Encrypted JSON string of backup codes
    mfa_backup_codes_used = Column(ARRAY(String(8)), nullable=True)  # Track used backup codes (plaintext for easy lookup)
    
    # Gmail integration
    gmail_credentials = Column(Text, nullable=True)  # Encrypted Gmail OAuth credentials
    gmail_email = Column(String(255), nullable=True)  # Connected Gmail email
    gmail_connected_at = Column(DateTime(timezone=True), nullable=True)  # When Gmail was connected
    gmail_auto_scan = Column(Boolean, default=False, nullable=False)  # Auto-scan new emails
    
    # Notification preferences
    notification_preferences = Column(PostgreSQLJSON(astext_type=Text()), default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    email_providers = relationship("EmailProvider", back_populates="user", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisJob", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_role", "role"),
        Index("idx_user_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary."""
        data = {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "company": self.company,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "email_verified": self.email_verified,
            "mfa_enabled": self.mfa_enabled,
            "has_avatar": bool(self.avatar_object_name),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
                "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
            })
        
        return data
