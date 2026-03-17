"""
Security Service for Risk-Based Authentication

This service provides risk-based authentication for different user actions,
following enterprise security patterns used by Google, Microsoft, and GitHub.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import logging

from app.models.user import User
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.sendgrid_service import sendgrid_service

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class VerificationMethod(Enum):
    NONE = "none"
    SESSION = "session"
    EMAIL_CODE = "email_code"
    OAUTH_REAUTH = "oauth_reauth"
    PASSWORD = "password"
    MFA = "mfa"

class SecurityService:
    """Enterprise-grade security service with risk-based authentication."""
    
    # Risk level mappings for different actions
    ACTION_RISK_LEVELS = {
        "view_profile": RiskLevel.LOW,
        "update_profile": RiskLevel.MEDIUM,
        "change_email": RiskLevel.HIGH,
        "setup_mfa": RiskLevel.HIGH,
        "delete_account": RiskLevel.CRITICAL,
        "disable_mfa": RiskLevel.HIGH,
        "change_password": RiskLevel.HIGH,
        "export_data": RiskLevel.MEDIUM,
        "api_access": RiskLevel.MEDIUM,
    }
    
    # Verification methods by risk level and user type
    VERIFICATION_MATRIX = {
        RiskLevel.LOW: {
            "oauth_user": VerificationMethod.SESSION,
            "regular_user": VerificationMethod.SESSION,
        },
        RiskLevel.MEDIUM: {
            "oauth_user": VerificationMethod.EMAIL_CODE,
            "regular_user": VerificationMethod.PASSWORD,
        },
        RiskLevel.HIGH: {
            "oauth_user": VerificationMethod.OAUTH_REAUTH,
            "regular_user": VerificationMethod.PASSWORD,
        },
        RiskLevel.CRITICAL: {
            "oauth_user": VerificationMethod.OAUTH_REAUTH,
            "regular_user": VerificationMethod.PASSWORD,
        }
    }
    
    def __init__(self):
        self.verification_codes = {}  # In production, use Redis
        self.reauth_tokens = {}      # In production, use Redis
    
    def get_risk_level(self, action: str) -> RiskLevel:
        """Get risk level for an action."""
        return self.ACTION_RISK_LEVELS.get(action, RiskLevel.MEDIUM)
    
    def get_verification_method(self, user: User, action: str) -> VerificationMethod:
        """Determine required verification method based on user type and risk level."""
        risk_level = self.get_risk_level(action)
        user_type = "oauth_user" if user.gmail_credentials and user.gmail_email else "regular_user"
        
        # If user has MFA enabled, require it for HIGH and CRITICAL actions
        if user.mfa_enabled and risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return VerificationMethod.MFA
        
        return self.VERIFICATION_MATRIX[risk_level][user_type]
    
    def generate_email_code(self, user_id: str) -> str:
        """Generate email verification code."""
        code = f"{secrets.randbelow(1000000):06d}"
        expiry = datetime.utcnow() + timedelta(minutes=10)
        
        self.verification_codes[user_id] = {
            "code": code,
            "expiry": expiry,
            "type": "email"
        }
        
        logger.info(f"Generated email verification code for user {user_id}")
        return code
    
    async def send_verification_email(self, user_email: str, code: str, action: str = "security_action") -> bool:
        """Send verification email using SendGrid."""
        try:
            success = await sendgrid_service.send_verification_code(user_email, code, action)
            if success:
                logger.info(f"Verification email sent to {user_email}")
            else:
                logger.error(f"Failed to send verification email to {user_email}")
            return success
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False
    
    def verify_email_code(self, user_id: str, code: str) -> bool:
        """Verify email verification code."""
        if user_id not in self.verification_codes:
            return False
        
        stored = self.verification_codes[user_id]
        if stored["type"] != "email":
            return False
        
        if datetime.utcnow() > stored["expiry"]:
            del self.verification_codes[user_id]
            return False
        
        return stored["code"] == code
    
    def generate_reauth_token(self, user_id: str) -> str:
        """Generate OAuth re-authentication token."""
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(minutes=5)
        
        self.reauth_tokens[user_id] = {
            "token": token,
            "expiry": expiry,
            "type": "oauth_reauth"
        }
        
        logger.info(f"Generated OAuth re-auth token for user {user_id}")
        return token
    
    def verify_reauth_token(self, user_id: str, token: str) -> bool:
        """Verify OAuth re-authentication token."""
        if user_id not in self.reauth_tokens:
            return False
        
        stored = self.reauth_tokens[user_id]
        if stored["type"] != "oauth_reauth":
            return False
        
        if datetime.utcnow() > stored["expiry"]:
            del self.reauth_tokens[user_id]
            return False
        
        return stored["token"] == token
    
    def cleanup_expired_tokens(self):
        """Clean up expired verification codes and tokens."""
        now = datetime.utcnow()
        
        # Clean verification codes
        expired_codes = [
            user_id for user_id, data in self.verification_codes.items()
            if now > data["expiry"]
        ]
        for user_id in expired_codes:
            del self.verification_codes[user_id]
        
        # Clean reauth tokens
        expired_tokens = [
            user_id for user_id, data in self.reauth_tokens.items()
            if now > data["expiry"]
        ]
        for user_id in expired_tokens:
            del self.reauth_tokens[user_id]
        
        if expired_codes or expired_tokens:
            logger.info(f"Cleaned up {len(expired_codes)} expired codes and {len(expired_tokens)} expired tokens")
    
    def get_security_requirements(self, user: User, action: str) -> Dict[str, Any]:
        """Get security requirements for an action."""
        method = self.get_verification_method(user, action)
        risk_level = self.get_risk_level(action)
        
        requirements = {
            "method": method.value,
            "risk_level": risk_level.value,
            "user_type": "oauth_user" if user.gmail_credentials and user.gmail_email else "regular_user",
            "mfa_required": user.mfa_enabled and risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            "message": self._get_verification_message(method, action)
        }
        
        # Add specific requirements based on method
        if method == VerificationMethod.EMAIL_CODE:
            requirements["email"] = user.email
        elif method == VerificationMethod.OAUTH_REAUTH:
            requirements["reauth_url"] = f"/auth/google/reauth?user_id={user.id}"
        
        return requirements
    
    def _get_verification_message(self, method: VerificationMethod, action: str) -> str:
        """Get user-friendly verification message."""
        messages = {
            VerificationMethod.NONE: "No verification required",
            VerificationMethod.SESSION: "Verified by current session",
            VerificationMethod.EMAIL_CODE: "Please check your email for a verification code",
            VerificationMethod.OAUTH_REAUTH: "Please re-authenticate with Google",
            VerificationMethod.PASSWORD: "Please enter your password",
            VerificationMethod.MFA: "Please enter your MFA code"
        }
        return messages.get(method, "Verification required")

# Global instance
security_service = SecurityService()
