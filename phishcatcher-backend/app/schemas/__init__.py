"""
PhishCatcher Pydantic Schemas

This module contains all Pydantic models for request/response validation.
"""

from app.schemas.auth import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserLogin,
    Token,
    TokenRefresh,
    OTPVerify,
    PasswordResetRequest,
    PasswordReset,
    PasswordChange,
    DeleteAccountRequest,
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MFAEnableRequest,
    MFADisableRequest,
    MFAStatusResponse,
    MFAVerification,
    OTPVerificationResponse,
    GoogleAuthUrl,
    GoogleCallback,
)
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisStatus,
    AnalysisList,
    FindingResponse,
    LinkAnalysisResponse,
    AttachmentAnalysisResponse,
)
from app.schemas.email_provider import (
    EmailProviderCreate,
    EmailProviderResponse,
    EmailProviderUpdate,
    GmailAuthUrl,
    GmailCallback,
)

__all__ = [
    # Auth schemas
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "UserLogin",
    "Token",
    "TokenRefresh",
    "OTPVerify",
    "PasswordResetRequest",
    "PasswordReset",
    "PasswordChange",
    "DeleteAccountRequest",
    "MFASetupRequest",
    "MFASetupResponse",
    "MFAVerifyRequest",
    "MFAEnableRequest",
    "MFADisableRequest",
    "MFAStatusResponse",
    "MFAVerification",
    "OTPVerificationResponse",
    "GoogleAuthUrl",
    "GoogleCallback",
    # Analysis schemas
    "AnalysisCreate",
    "AnalysisResponse",
    "AnalysisStatus",
    "AnalysisList",
    "FindingResponse",
    "LinkAnalysisResponse",
    "AttachmentAnalysisResponse",
    # Email provider schemas
    "EmailProviderCreate",
    "EmailProviderResponse",
    "EmailProviderUpdate",
    "GmailAuthUrl",
    "GmailCallback",
]
