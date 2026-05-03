"""
Analysis Job Model

This module defines the AnalysisJob model for tracking email analysis jobs.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class AnalysisJob(Base):
    """Analysis job tracking model."""
    
    __tablename__ = "analysis_jobs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Source information
    source_type = Column(String(50), default="upload")  # upload, gmail, outlook, imap
    provider_id = Column(UUID(as_uuid=True), ForeignKey("email_providers.id", ondelete="SET NULL"), nullable=True)
    external_message_id = Column(String(500), nullable=True)  # Gmail/Outlook message ID
    
    # File information
    file_name = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # in bytes
    file_type = Column(String(50), nullable=True)  # eml, msg, txt
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash
    s3_key = Column(String(500), nullable=True)  # Legacy S3 key
    
    # MinIO storage fields
    storage_object_name = Column(String(500), nullable=True)  # MinIO object name
    storage_bucket = Column(String(100), nullable=True)  # MinIO bucket name
    
    # Job status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed, cancelled
    status_message = Column(Text, nullable=True)
    
    # Progress tracking
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)
    
    # Analysis results (summary stored in PostgreSQL, details in MongoDB)
    risk_score = Column(Integer, nullable=True)  # 0-100
    threat_category = Column(String(100), nullable=True)  # phishing, malware, spoofing, safe
    confidence = Column(Float, nullable=True)  # 0.0-1.0
    findings_count = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    high_findings = Column(Integer, default=0)
    medium_findings = Column(Integer, default=0)
    low_findings = Column(Integer, default=0)
    
    # ML and TI scores
    ml_score = Column(Float, nullable=True)  # ML model phishing probability (0.0-1.0)
    ti_score = Column(Float, nullable=True)  # Threat Intel score (0.0-1.0)
    
    # MongoDB reference
    mongodb_result_id = Column(String(64), nullable=True)  # MongoDB ObjectId or custom hex ID
    
    # Report generation
    report_generated = Column(Boolean, default=False)
    report_s3_key = Column(String(500), nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="analysis_jobs")
    provider = relationship("EmailProvider")
    
    # Indexes
    __table_args__ = (
        Index("idx_job_user_status", "user_id", "status"),
        Index("idx_job_status_created", "status", "created_at"),
        Index("idx_job_risk_score", "risk_score"),
        Index("idx_job_threat_category", "threat_category"),
        Index("idx_job_file_hash", "file_hash"),
        Index("idx_job_user_created", "user_id", "created_at"),
        Index("idx_job_completed_at", "completed_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AnalysisJob(id={self.id}, status={self.status}, risk_score={self.risk_score})>"
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if job is completed."""
        return self.status in ["completed", "failed", "cancelled"]
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert job to dictionary."""
        data = {
            "id": str(self.id),
            "source_type": self.source_type,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "risk_score": self.risk_score,
            "threat_category": self.threat_category,
            "confidence": self.confidence,
            "findings_count": self.findings_count,
            "critical_findings": self.critical_findings,
            "high_findings": self.high_findings,
            "medium_findings": self.medium_findings,
            "low_findings": self.low_findings,
            "ml_score": self.ml_score,
            "ti_score": self.ti_score,
            "report_generated": self.report_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
        
        if include_details:
            data.update({
                "file_name": self.file_name,
                "file_size": self.file_size,
                "file_type": self.file_type,
                "duration_seconds": self.duration_seconds,
                "error_message": self.error_message,
                "retry_count": self.retry_count,
            })
        
        return data
