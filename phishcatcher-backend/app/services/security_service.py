"""
Security Service for Risk-Based Authentication

This service provides risk-based authentication for different user actions,
following enterprise security patterns used by Google, Microsoft, and GitHub.

Verification codes and reauth tokens are stored in Redis for multi-worker safety.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import secrets
import json
import logging

from app.models.user import User
from app.database import get_redis_client

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
    
    # Redis key prefixes
    _VERIFICATION_CODE_PREFIX = "security:verification_code:"
    _REAUTH_TOKEN_PREFIX = "security:reauth_token:"
    _CODE_TTL_SECONDS = 600    # 10 minutes
    _TOKEN_TTL_SECONDS = 300   # 5 minutes
    
    def __init__(self):
        self._redis: Optional[object] = None
    
    def _get_redis(self):
        """Lazy-load Redis client."""
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis
    
    def get_risk_level(self, action: str) -> RiskLevel:
        """Get risk level for an action."""
        return self.ACTION_RISK_LEVELS.get(action, RiskLevel.MEDIUM)
    
    def get_verification_method(self, user: User, action: str) -> VerificationMethod:
        """Determine required verification method based on user type and risk level."""
        risk_level = self.get_risk_level(action)
        user_type = "oauth_user" if user.gmail_credentials and user.gmail_email else "regular_user"
        
        if user.mfa_enabled and risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return VerificationMethod.MFA
        
        return self.VERIFICATION_MATRIX[risk_level][user_type]
    
    async def generate_email_code(self, user_id: str) -> str:
        """Generate email verification code stored in Redis."""
        code = f"{secrets.randbelow(1000000):06d}"
        expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        redis_client = self._get_redis()
        await redis_client.setex(
            f"{self._VERIFICATION_CODE_PREFIX}{user_id}",
            self._CODE_TTL_SECONDS,
            json.dumps({"code": code, "expiry": expiry.isoformat(), "type": "email"})
        )
        
        logger.info(f"Generated email verification code for user {user_id}")
        return code
    
    async def send_verification_email(self, user_email: str, code: str, action: str = "security_action") -> bool:
        """Send verification email using Brevo."""
        try:
            from app.services.brevo_service import brevo_service
            success = await brevo_service.send_verification_code(user_email, code, action)
            if success:
                logger.info(f"Verification email sent to {user_email}")
            else:
                logger.error(f"Failed to send verification email to {user_email}")
            return success
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False
    
    async def send_verification_sms(self, user_phone: str, code: str, action: str = "security_action") -> bool:
        """Send verification SMS using Brevo."""
        try:
            from app.services.sms_service import sms_service
            success = await sms_service.send_otp(user_phone, code)
            if success:
                logger.info(f"Verification SMS sent to {user_phone}")
            else:
                logger.error(f"Failed to send verification SMS to {user_phone}")
            return success
        except Exception as e:
            logger.error(f"Error sending verification SMS: {e}")
            return False
    
    async def verify_email_code(self, user_id: str, code: str) -> bool:
        """Verify email verification code from Redis."""
        redis_client = self._get_redis()
        raw = await redis_client.get(f"{self._VERIFICATION_CODE_PREFIX}{user_id}")
        
        if not raw:
            return False
        
        stored = json.loads(raw)
        if stored.get("type") != "email":
            return False
        
        if stored.get("code") != code:
            return False
        
        await redis_client.delete(f"{self._VERIFICATION_CODE_PREFIX}{user_id}")
        return True
    
    async def delete_email_code(self, user_id: str) -> None:
        """Delete email verification code from Redis."""
        redis_client = self._get_redis()
        await redis_client.delete(f"{self._VERIFICATION_CODE_PREFIX}{user_id}")
    
    async def generate_reauth_token(self, user_id: str) -> str:
        """Generate OAuth re-authentication token stored in Redis."""
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        redis_client = self._get_redis()
        await redis_client.setex(
            f"{self._REAUTH_TOKEN_PREFIX}{user_id}",
            self._TOKEN_TTL_SECONDS,
            json.dumps({"token": token, "expiry": expiry.isoformat(), "type": "oauth_reauth"})
        )
        
        logger.info(f"Generated OAuth re-auth token for user {user_id}")
        return token
    
    async def verify_reauth_token(self, user_id: str, token: str) -> bool:
        """Verify OAuth re-authentication token from Redis."""
        redis_client = self._get_redis()
        raw = await redis_client.get(f"{self._REAUTH_TOKEN_PREFIX}{user_id}")
        
        if not raw:
            return False
        
        stored = json.loads(raw)
        if stored.get("type") != "oauth_reauth":
            return False
        
        if stored.get("token") != token:
            return False
        
        await redis_client.delete(f"{self._REAUTH_TOKEN_PREFIX}{user_id}")
        return True
    
    async def delete_reauth_token(self, user_id: str) -> None:
        """Delete reauth token from Redis."""
        redis_client = self._get_redis()
        await redis_client.delete(f"{self._REAUTH_TOKEN_PREFIX}{user_id}")
    
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

security_service = SecurityService()
