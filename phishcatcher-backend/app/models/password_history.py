"""
Password History Model

This module defines the PasswordHistory model for tracking user password changes
and preventing password reuse.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class PasswordHistory(Base):
    """Model for tracking password history to prevent reuse."""
    
    __tablename__ = "password_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_password_history_user_created", "user_id", "created_at"),
    )
    
    # Relationship
    user = relationship("User", back_populates="password_history")
    
    def __repr__(self):
        return f"<PasswordHistory(user_id={self.user_id}, created_at={self.created_at})>"
