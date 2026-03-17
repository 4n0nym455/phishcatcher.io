from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON as PostgreSQLJSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import uuid

from app.database import Base

class NotificationType(str, Enum):
    SECURITY_ALERT = "security"
    PHISHING_DETECTION = "phishing"
    SYSTEM_UPDATE = "system"
    MARKETING = "marketing"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # Using string instead of enum for simplicity
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    data = Column(PostgreSQLJSON(astext_type=Text), nullable=True)  # Additional data for notification
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, title={self.title})>"
