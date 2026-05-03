"""
Email Provider Schemas

Pydantic models for email provider integration requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from enum import Enum


class ProviderType(str, Enum):
    """Email provider type enum."""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    IMAP = "imap"


class EmailProviderBase(BaseModel):
    """Base email provider schema."""
    provider_type: ProviderType
    provider_name: Optional[str] = None
    email_address: EmailStr


class EmailProviderCreate(EmailProviderBase):
    """Email provider creation schema."""
    # IMAP settings (for IMAP provider type)
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: bool = True
    
    # Sync settings
    sync_enabled: bool = True
    sync_folder: str = "INBOX"
    sync_filter: Optional[str] = None
    max_emails_per_sync: int = 100


class EmailProviderUpdate(BaseModel):
    """Email provider update schema."""
    provider_name: Optional[str] = None
    sync_enabled: Optional[bool] = None
    sync_folder: Optional[str] = None
    sync_filter: Optional[str] = None
    max_emails_per_sync: Optional[int] = Field(None, ge=10, le=1000)
    sync_frequency_minutes: Optional[int] = Field(None, ge=5, le=1440)


class EmailProviderResponse(EmailProviderBase):
    """Email provider response schema."""
    id: str
    sync_enabled: bool
    last_sync_at: Optional[datetime] = None
    is_active: bool
    is_connected: bool
    is_default: bool = False
    sync_folder: str
    max_emails_per_sync: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EmailProviderList(BaseModel):
    """Email provider list response schema."""
    items: list[EmailProviderResponse]
    total: int


class GmailAuthUrl(BaseModel):
    """Gmail OAuth URL response schema."""
    auth_url: str
    state: str


class GmailCallback(BaseModel):
    """Gmail OAuth callback request schema."""
    code: str
    state: str


class GmailConnectRequest(BaseModel):
    """Gmail connect request schema."""
    provider_name: Optional[str] = None
    sync_enabled: bool = True
    sync_folder: str = "INBOX"
    max_emails_per_sync: int = 100


class IMAPConnectRequest(BaseModel):
    """IMAP connect request schema."""
    provider_name: str
    email_address: EmailStr
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str
    imap_use_ssl: bool = True
    sync_enabled: bool = True
    sync_folder: str = "INBOX"
    max_emails_per_sync: int = 100


class SyncStatus(BaseModel):
    """Sync status schema."""
    provider_id: str
    status: str  # idle, syncing, error
    last_sync_at: Optional[datetime] = None
    emails_synced: int = 0
    emails_analyzed: int = 0
    errors: list[str] = []


class SyncRequest(BaseModel):
    """Sync request schema."""
    max_emails: int = Field(100, ge=1, le=1000)
    folder: str = "INBOX"
    filter_query: Optional[str] = None


class SyncResponse(BaseModel):
    """Sync response schema."""
    provider_id: str
    sync_job_id: str
    status: str
    message: str
    emails_queued: int


class ProviderHealth(BaseModel):
    """Provider health check schema."""
    provider_id: str
    is_connected: bool
    is_token_valid: bool
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    quota_usage: Optional[dict] = None


class EmailSummary(BaseModel):
    """Email summary schema for synced emails."""
    id: str
    external_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[datetime] = None
    has_analysis: bool = False
    analysis_id: Optional[str] = None
    risk_score: Optional[int] = None
