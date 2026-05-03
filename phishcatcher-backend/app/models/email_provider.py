"""
Email Provider Model

This module defines the EmailProvider model for storing OAuth credentials
and sync settings for Gmail, Outlook, and IMAP providers.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class EmailProvider(Base):
    """Email provider connection model."""
    
    __tablename__ = "email_providers"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Provider information
    provider_type = Column(String(50), nullable=False)  # gmail, outlook, imap
    provider_name = Column(String(100), nullable=True)  # Display name (e.g., "Work Gmail")
    email_address = Column(String(255), nullable=False)
    
    # OAuth credentials (encrypted at application level)
    access_token = Column(Text, nullable=True)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # IMAP settings (for non-OAuth providers)
    imap_host = Column(String(255), nullable=True)
    imap_port = Column(Integer, default=993)
    imap_username = Column(String(255), nullable=True)  # Encrypted
    imap_password = Column(Text, nullable=True)  # Encrypted
    imap_use_ssl = Column(Boolean, default=True)
    
    # Sync settings
    sync_enabled = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_history_id = Column(String(255), nullable=True)  # Gmail history ID
    sync_frequency_minutes = Column(Integer, default=15)
    
    # Email filtering
    sync_folder = Column(String(100), default="INBOX")
    sync_filter = Column(String(255), nullable=True)  # e.g., "is:unread"
    max_emails_per_sync = Column(Integer, default=100)
    
    # Webhook settings (for Gmail push notifications)
    webhook_enabled = Column(Boolean, default=False)
    webhook_resource_id = Column(String(255), nullable=True)
    webhook_expiration = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)  # For multi-account support
    connection_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="email_providers")
    
    # Indexes
    __table_args__ = (
        Index("idx_provider_user_type", "user_id", "provider_type"),
        Index("idx_provider_active", "is_active", "sync_enabled"),
        Index("idx_provider_sync", "last_sync_at"),
        Index("idx_provider_user_email", "user_id", "email_address"),
        Index("idx_provider_connected_active", "provider_type", "is_connected", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<EmailProvider(id={self.id}, type={self.provider_type}, email={self.email_address})>"
    
    @property
    def is_token_expired(self) -> bool:
        """Check if OAuth token is expired."""
        if self.token_expires_at is None:
            return True
        return datetime.now(timezone.utc) >= self.token_expires_at
    
    @property
    def needs_sync(self) -> bool:
        """Check if provider needs to be synced."""
        if not self.sync_enabled or not self.is_active:
            return False
        
        if self.last_sync_at is None:
            return True
        
        minutes_since_sync = (datetime.now(timezone.utc) - self.last_sync_at).total_seconds() / 60
        return minutes_since_sync >= self.sync_frequency_minutes
    
    def to_dict(self, include_tokens: bool = False) -> dict:
        """Convert provider to dictionary."""
        data = {
            "id": str(self.id),
            "provider_type": self.provider_type,
            "provider_name": self.provider_name,
            "email_address": self.email_address,
            "sync_enabled": self.sync_enabled,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "is_active": self.is_active,
            "is_connected": self.is_connected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_tokens:
            data.update({
                "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "is_token_expired": self.is_token_expired,
            })
        
        return data
