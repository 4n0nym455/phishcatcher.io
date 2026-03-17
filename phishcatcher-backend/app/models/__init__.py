"""
PhishCatcher Database Models

This module contains all SQLAlchemy models for PostgreSQL.
"""

from app.models.user import User
from app.models.email_provider import EmailProvider
from app.models.analysis_job import AnalysisJob
from app.models.audit_log import AuditLog, AuditAction
from app.models.notification import Notification, NotificationType

__all__ = ["User", "EmailProvider", "AnalysisJob", "AuditLog", "AuditAction", "Notification", "NotificationType"]
