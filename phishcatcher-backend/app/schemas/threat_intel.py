"""
Threat Intelligence Pydantic Models

This module defines data models for threat intelligence API responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AbuseIPDBResponse(BaseModel):
    """AbuseIPDB IP/Domain reputation response model."""
    ip_address: str = Field(..., description="The IP address checked")
    abuse_confidence_score: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    is_whitelisted: bool = Field(default=False, description="Whether IP is whitelisted")
    is_blacklisted: bool = Field(default=False, description="Whether IP is blacklisted")
    num_reports: int = Field(default=0, description="Number of abuse reports")
    num_distinct_users: int = Field(default=0, description="Number of distinct reporters")
    country_code: Optional[str] = Field(default=None, description="Country code")
    country_name: Optional[str] = Field(default=None, description="Country name")
    ip_version: int = Field(default=4, description="IP version (4 or 6)")
    isp: Optional[str] = Field(default=None, description="ISP name")
    domain: Optional[str] = Field(default=None, description="Domain name")
    usage_type: Optional[str] = Field(default=None, description="Usage type")
    categories: List[int] = Field(default_factory=list, description="Abuse categories")
    reported_at: Optional[str] = Field(default=None, description="Last report timestamp")
    risk_level: str = Field(..., description="low/medium/high/critical")
    is_public: bool = Field(default=True, description="Whether IP is public")


class WhoisJSONResponse(BaseModel):
    """WhoisJSON domain age response model."""
    domain: str = Field(..., description="Domain name checked")
    created_date: Optional[str] = Field(default=None, description="Domain creation date")
    created_date_in_unix: Optional[int] = Field(default=None, description="Creation date as unix timestamp")
    updated_date: Optional[str] = Field(default=None, description="Last update date")
    expires_date: Optional[str] = Field(default=None, description="Expiration date")
    age_in_days: Optional[int] = Field(default=None, description="Domain age in days")
    age_in_years: Optional[float] = Field(default=None, description="Domain age in years")
    registrar: Optional[str] = Field(default=None, description="Registrar name")
    registrant_name: Optional[str] = Field(default=None, description="Registrant name")
    registrant_country: Optional[str] = Field(default=None, description="Registrant country")
    name_servers: List[str] = Field(default_factory=list, description="Name servers")
    status: Optional[str] = Field(default=None, description="Registration status")
    domain_age_risk: str = Field(..., description="low/medium/high based on age")


class PhishTankResponse(BaseModel):
    """PhishTank URL phishing check response model."""
    url: str = Field(..., description="URL checked")
    in_database: bool = Field(..., description="Whether URL is in PhishTank database")
    phish_detail_url: Optional[str] = Field(default=None, description="PhishTank detail URL")
    verified: bool = Field(default=False, description="Whether phishing is verified")
    verified_at: Optional[str] = Field(default=None, description="Verification timestamp")
    online: bool = Field(default=True, description="Whether phishing site is online")
    phish_id: Optional[int] = Field(default=None, description="PhishTank ID")
    phish_detail_page: Optional[str] = Field(default=None, description="PhishTank detail page")
    risk_level: str = Field(default="none", description="none/low/medium/high")


class VirusTotalURLResponse(BaseModel):
    """VirusTotal URL analysis response model."""
    url: str = Field(..., description="URL analyzed")
    threat_category: Optional[str] = Field(default=None, description="Threat category")
    threat_name: Optional[str] = Field(default=None, description="Threat name")
    malicious_votes: int = Field(default=0, description="Number of malicious votes")
    suspicious_votes: int = Field(default=0, description="Number of suspicious votes")
    harmless_votes: int = Field(default=0, description="Number of harmless votes")
    undetected_votes: int = Field(default=0, description="Number of undetected votes")
    last_analysis_stats: Dict[str, int] = Field(default_factory=dict, description="Analysis stats")
    last_analysis_date: Optional[str] = Field(default=None, description="Last analysis timestamp")
    risk_level: str = Field(..., description="none/low/medium/high/critical")
    permalink: Optional[str] = Field(default=None, description="VirusTotal permalink")


class VirusTotalHashResponse(BaseModel):
    """VirusTotal file hash analysis response model."""
    hash: str = Field(..., description="File hash (MD5/SHA1/SHA256)")
    meaningful_name: Optional[str] = Field(default=None, description="File name")
    malicious_votes: int = Field(default=0, description="Number of malicious votes")
    suspicious_votes: int = Field(default=0, description="Number of suspicious votes")
    harmless_votes: int = Field(default=0, description="Number of harmless votes")
    last_analysis_stats: Dict[str, int] = Field(default_factory=dict, description="Analysis stats")
    first_submission_date: Optional[str] = Field(default=None, description="First submission date")
    last_submission_date: Optional[str] = Field(default=None, description="Last submission date")
    names: List[str] = Field(default_factory=list, description="Known file names")
    file_type: Optional[str] = Field(default=None, description="File type")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    risk_level: str = Field(..., description="none/low/medium/high/critical")


class URLScanResponse(BaseModel):
    """URLScan.io URL analysis response model."""
    url: str = Field(..., description="URL analyzed")
    status: str = Field(..., description="Analysis status (success/error)")
    score: Optional[float] = Field(default=None, ge=0, le=100, description="Security score (0-100)")
    categories: List[str] = Field(default_factory=list, description="Security categories")
    compromises: List[str] = Field(default_factory=list, description="Known compromises")
    domain: Optional[str] = Field(default=None, description="Domain name")
    server: Optional[str] = Field(default=None, description="Server info")
    content_type: Optional[str] = Field(default=None, description="Content type")
    resp_hash: Optional[str] = Field(default=None, description="Response hash")
    risk_level: str = Field(..., description="none/low/medium/high/critical")
    permalink: Optional[str] = Field(default=None, description="URLScan permalink")


class ThreatIntelResult(BaseModel):
    """Combined threat intelligence result for an email."""
    overall_risk_score: float = Field(..., ge=0, le=1, description="Combined risk score 0-1")
    risk_category: str = Field(..., description="safe/low_risk/suspicious/likely_phishing/phishing")
    confidence: float = Field(..., ge=0, le=1, description="Confidence of the assessment")
    
    abuseipdb: Optional[AbuseIPDBResponse] = Field(default=None, description="AbuseIPDB result")
    whoisjson: Optional[WhoisJSONResponse] = Field(default=None, description="WhoisJSON result")
    phishtank: Optional[PhishTankResponse] = Field(default=None, description="PhishTank result")
    virustotal_url: Optional[VirusTotalURLResponse] = Field(default=None, description="VirusTotal URL result")
    virustotal_hash: Optional[VirusTotalHashResponse] = Field(default=None, description="VirusTotal hash result")
    urlscan: Optional[URLScanResponse] = Field(default=None, description="URLScan result (backup)")
    
    indicators: List[str] = Field(default_factory=list, description="List of detected indicators")
    warnings: List[str] = Field(default_factory=list, description="Warnings (e.g., API failures)")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    cache_hit: bool = Field(default=False, description="Whether result was from cache")


class TIAPICheckResult(BaseModel):
    """Result for a single TI API check."""
    api_name: str = Field(..., description="Name of the API (e.g., abuseipdb, phishtank)")
    success: bool = Field(..., description="Whether the API call succeeded")
    score: float = Field(..., ge=0, le=1, description="Risk score from this API (0-1)")
    risk_level: str = Field(..., description="Risk level from this API")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Raw response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    cached: bool = Field(default=False, description="Whether result was cached")
    response_time_ms: Optional[int] = Field(default=None, description="API response time in ms")