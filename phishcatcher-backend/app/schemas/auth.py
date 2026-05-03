"""
Authentication Schemas

Pydantic models for authentication-related requests and responses.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator, AliasChoices


def validate_password_strength(v: str) -> str:
    """Shared password validator — delegates to security service for policy compliance."""
    from app.services.security import validate_password_strength as _svc_validate
    is_valid, error = _svc_validate(v)
    if not is_valid:
        raise ValueError(error)
    return v


class UserBase(BaseModel):
    """Base user schema."""
    email: str = Field(..., min_length=5, max_length=254)
    full_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    """User registration schema."""
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str
    accept_terms_and_privacy: bool = Field(..., description="Must accept Terms & Conditions and Privacy Policy")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        return validate_password_strength(v)
    
    @model_validator(mode="before")
    @classmethod
    def validate_cross_fields(cls, data):
        """Ensure passwords match and terms are accepted."""
        if isinstance(data, dict):
            if data.get("password") and data.get("confirm_password"):
                if data["confirm_password"] != data["password"]:
                    raise ValueError("Passwords do not match")
            if not data.get("accept_terms_and_privacy"):
                raise ValueError("Must accept Terms & Conditions and Privacy Policy")
        return data


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """User response schema."""
    id: str
    role: str
    is_active: bool
    is_verified: bool
    email_verified: bool
    phone_verified: bool = False
    mfa_enabled: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    avatar_updated_at: Optional[datetime] = None
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string if needed."""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    refresh_token: str
    signing_key: Optional[str] = None  # Optional HMAC signing key from client


class OTPVerify(BaseModel):
    """OTP verification schema."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-character alphanumeric OTP code")


class ResendOTP(BaseModel):
    """Resend OTP schema."""
    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Password reset schema."""
    model_config = ConfigDict(populate_by_name=True)
    
    token: str
    new_password: str = Field(..., min_length=12, max_length=128, validation_alias=AliasChoices("new_password", "newPassword"))
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        return validate_password_strength(v)


class PasswordResetVerify(BaseModel):
    """Password reset verification schema."""
    model_config = ConfigDict(populate_by_name=True)
    
    token: str
    new_password: str = Field(..., min_length=12, max_length=128, validation_alias=AliasChoices("new_password", "newPassword"))
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        return validate_password_strength(v)


class PasswordChange(BaseModel):
    """Password change schema."""
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)
    confirm_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        return validate_password_strength(v)
    
    @model_validator(mode="before")
    @classmethod
    def validate_passwords_match(cls, data):
        """Ensure passwords match."""
        if isinstance(data, dict):
            if data.get("new_password") and data.get("confirm_password"):
                if data["confirm_password"] != data["new_password"]:
                    raise ValueError("Passwords do not match")
        return data


class DeleteAccountRequest(BaseModel):
    """Delete account request schema."""
    password: str


class MFASetup(BaseModel):
    """MFA setup schema."""
    secret: str
    qr_code: str  # Base64 encoded QR code
    backup_codes: list[str]


class MFAVerify(BaseModel):
    """MFA verification schema."""
    code: str = Field(..., min_length=6, max_length=6)


class MFAEnable(BaseModel):
    """MFA enable schema."""
    code: str = Field(..., min_length=6, max_length=6)
    secret: str


class MFADisable(BaseModel):
    """MFA disable schema."""
    code: str = Field(..., min_length=6, max_length=6)
    password: str


class LoginResponse(BaseModel):
    """Login response (before OTP verification)."""
    message: str
    email: str
    mfa_required: bool
    mfa_session_token: Optional[str] = None


class OTPVerificationResponse(BaseModel):
    """OTP verification response."""
    mfa_required: bool
    mfa_session_token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class GoogleAuthUrl(BaseModel):
    """Google OAuth URL response."""
    auth_url: str
    state: str


class GoogleCallback(BaseModel):
    """Google OAuth callback schema."""
    code: str
    state: str


# MFA Schemas
class MFASetupRequest(BaseModel):
    """MFA setup request schema."""
    # No password required - all users can set up MFA without password verification
    # Security is maintained through the MFA verification process
    pass


class MFASetupResponse(BaseModel):
    """MFA setup response schema."""
    secret: str = Field(..., description="TOTP secret for manual entry")
    qr_code: str = Field(..., description="Base64 encoded QR code image")
    backup_codes: List[str] = Field(..., description="Backup codes for account recovery")
    mfa_session_token: str = Field(..., description="MFA setup session token for validation")
    instructions: str = Field(..., description="Setup instructions")


class MFAVerifyRequest(BaseModel):
    """MFA verification request schema."""
    token: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP token")
    secret: str = Field(..., description="TOTP secret to verify")
    backup_codes: List[str] = Field(..., description="Backup codes for account recovery")
    mfa_session_token: str = Field(..., description="MFA setup session token for validation")


class MFAEnableRequest(BaseModel):
    """MFA enable request schema."""
    token: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP token")


class MFADisableRequest(BaseModel):
    """MFA disable request schema."""
    password: str = Field(..., description="User password to confirm identity")
    token: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP token")


class PhoneUpdateRequest(BaseModel):
    """Phone number update request schema."""
    phone: str = Field(..., description="Phone number in E.164 format (e.g., +1234567890)")


class PhoneVerifyRequest(BaseModel):
    """Phone number verification request schema."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class MFAStatusResponse(BaseModel):
    """MFA status response schema."""
    enabled: bool = Field(..., description="Whether MFA is enabled")
    setup_completed: bool = Field(..., description="Whether MFA setup is completed")
    has_backup_codes: bool = Field(..., description="Whether backup codes are available")


class MFAVerification(BaseModel):
    """MFA verification schema for login flow."""
    mfa_session_token: str = Field(..., description="MFA session token from initial auth")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit MFA code")


__all__ = [
    "UserCreate", "UserResponse", "PasswordChange",
    "PasswordReset", "PasswordResetRequest", "PasswordResetVerify",
    "UserLogin", "LoginResponse", "OTPVerify", "TokenRefresh", "ResendOTP",
    "DeleteAccountRequest",
    "MFASetupRequest", "MFASetupResponse", "MFAVerifyRequest",
    "MFAEnableRequest", "MFADisableRequest", "MFAStatusResponse",
    "MFAVerification", "OTPVerificationResponse", "GoogleAuthUrl",
    "GoogleCallback",
    "PhoneUpdateRequest", "PhoneVerifyRequest",
    "validate_password_strength",
]
