"""
Analysis Schemas

Pydantic models for email analysis requests and responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ThreatCategory(str, Enum):
    """Threat category enum."""
    PHISHING = "phishing"
    MALWARE = "malware"
    SPOOFING = "spoofing"
    SPAM = "spam"
    SAFE = "safe"
    SUSPICIOUS = "suspicious"


class SeverityLevel(str, Enum):
    """Severity level enum."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class JobStatus(str, Enum):
    """Analysis job status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisCreate(BaseModel):
    """Analysis creation schema."""
    source_type: str = "upload"  # upload, gmail, outlook, imap
    provider_id: Optional[str] = None
    external_message_id: Optional[str] = None


class EmailMetadata(BaseModel):
    """Email metadata schema."""
    subject: Optional[str] = None
    sender: Optional[str] = None
    sender_name: Optional[str] = None
    recipient: List[str] = []
    cc: List[str] = []
    bcc: List[str] = []
    date: Optional[datetime] = None
    message_id: Optional[str] = None
    reply_to: Optional[str] = None
    return_path: Optional[str] = None


class AuthenticationResults(BaseModel):
    """Email authentication results schema."""
    spf: Optional[str] = None
    dkim: Optional[str] = None
    dmarc: Optional[str] = None
    spf_details: Optional[str] = None
    dkim_details: Optional[str] = None
    dmarc_details: Optional[str] = None


class FindingResponse(BaseModel):
    """Analysis finding schema."""
    id: str
    type: str  # domain, link, attachment, content, sender, authentication
    severity: SeverityLevel
    title: str
    description: str
    recommendation: str
    evidence: Dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)


class LinkAnalysisResponse(BaseModel):
    """Link analysis result schema."""
    url: str
    display_text: Optional[str] = None
    domain: str
    ip_address: Optional[str] = None
    status: str  # safe, suspicious, malicious, unknown
    reputation_score: Optional[int] = Field(None, ge=0, le=100)
    category: Optional[str] = None
    redirects_to: Optional[str] = None
    is_shortened: bool = False
    is_ip_based: bool = False
    threat_intelligence: Dict[str, Any] = {}


class AttachmentAnalysisResponse(BaseModel):
    """Attachment analysis result schema."""
    filename: str
    content_type: str
    size: int
    hash_md5: Optional[str] = None
    hash_sha1: Optional[str] = None
    hash_sha256: Optional[str] = None
    status: str  # safe, suspicious, malicious, unknown
    threat_intelligence: Dict[str, Any] = {}
    is_executable: bool = False
    is_script: bool = False


class RiskFactors(BaseModel):
    """Risk factors breakdown schema."""
    sender_reputation: int = Field(..., ge=0, le=100)
    content_risk: int = Field(..., ge=0, le=100)
    link_risk: int = Field(..., ge=0, le=100)
    attachment_risk: int = Field(..., ge=0, le=100)
    authentication_risk: int = Field(..., ge=0, le=100)


class MLFeatures(BaseModel):
    """ML features used for analysis schema."""
    header_features: Dict[str, Any]
    content_features: Dict[str, Any]
    link_features: Dict[str, Any]
    attachment_features: Dict[str, Any]


class AnalysisResult(BaseModel):
    """Complete analysis result schema."""
    risk_score: int = Field(..., ge=0, le=100)
    threat_category: ThreatCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    findings: List[FindingResponse]
    risk_factors: RiskFactors
    links_analyzed: List[LinkAnalysisResponse]
    attachments_analyzed: List[AttachmentAnalysisResponse]
    ml_features: Optional[MLFeatures] = None


class AnalysisResponse(BaseModel):
    """Analysis response schema."""
    id: str
    source_type: str
    status: JobStatus
    progress_percent: int = Field(..., ge=0, le=100)
    current_step: Optional[str] = None
    
    # Email info
    email_metadata: Optional[EmailMetadata] = None
    authentication_results: Optional[AuthenticationResults] = None
    
    # Results
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    threat_category: Optional[ThreatCategory] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    findings: List[FindingResponse] = []
    findings_count: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    
    # Analysis details
    links_analyzed: List[LinkAnalysisResponse] = []
    attachments_analyzed: List[AttachmentAnalysisResponse] = []
    risk_factors: Optional[RiskFactors] = None
    
    # ML Analysis details
    ml_analysis: Optional[Dict[str, Any]] = None
    
    # Threat Intelligence
    threat_intelligence: Optional[Dict[str, Any]] = None
    
    # Report
    report_generated: bool = False
    report_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    class Config:
        from_attributes = True


class AnalysisStatus(BaseModel):
    """Analysis status schema."""
    id: str
    status: JobStatus
    progress_percent: int
    current_step: Optional[str] = None
    risk_score: Optional[int] = None
    threat_category: Optional[str] = None


class AnalysisListItem(BaseModel):
    """Analysis list item schema."""
    id: str
    analysis_id: Optional[str] = None
    source_type: str
    file_name: Optional[str] = None
    subject: Optional[str] = None
    status: JobStatus
    risk_score: Optional[int] = None
    threat_category: Optional[str] = None
    findings_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None


class AnalysisList(BaseModel):
    """Analysis list response schema."""
    items: List[AnalysisListItem]
    total: int
    page: int
    page_size: int
    pages: int


class AnalysisFilters(BaseModel):
    """Analysis filters schema."""
    status: Optional[JobStatus] = None
    threat_category: Optional[ThreatCategory] = None
    min_risk_score: Optional[int] = Field(None, ge=0, le=100)
    max_risk_score: Optional[int] = Field(None, ge=0, le=100)
    source_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class ReportFormat(str, Enum):
    """Report format enum."""
    PDF = "pdf"
    TXT = "txt"
    JSON = "json"
    CSV = "csv"


class ReportDownloadRequest(BaseModel):
    """Report download request schema."""
    format: ReportFormat = ReportFormat.PDF
    include_sensitive: bool = False


class WeeklyReport(BaseModel):
    """Weekly report schema."""
    week_start: datetime
    week_end: datetime
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    total_analyses: int
    total_emails: int
    phishing_detected: int
    malware_detected: int
    suspicious_detected: int
    safe_emails: int
    average_risk_score: float
    top_threats: List[Dict[str, Any]]
    daily_breakdown: List[Dict[str, Any]]


class SimilarThreat(BaseModel):
    """Similar threat schema."""
    id: str
    similarity_score: float
    threat_category: str
    risk_score: int
    date: datetime
    indicators: List[str]
