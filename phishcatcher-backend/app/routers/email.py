"""
Email Router for Comprehensive Email Services

This router handles all email-related endpoints including:
- OTP verification
- Welcome/onboarding emails
- Password reset
- Account notifications
- Security alerts
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.config import get_settings
from app.models.audit_log import AuditLog, AuditAction
from app.services.email_service import email_service
from app.services.security_service import security_service
from app.services.password_history import check_password_reuse, save_password_to_history
from app.services.security import verify_password, get_password_hash, validate_password_strength
from app.database import get_db
from app.routers.auth import get_current_active_user
from app.routers.admin import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Email"])

# Pydantic models for requests
class OTPRequest(BaseModel):
    email: EmailStr
    action: Optional[str] = "verify your account"

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class WelcomeEmailRequest(BaseModel):
    email: EmailStr
    user_name: Optional[str] = "User"
    dashboard_url: Optional[str] = None

class SecurityAlertRequest(BaseModel):
    email: EmailStr
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class CustomEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    html_content: str


@router.post("/email/send-otp")
async def send_otp_verification(
    request: OTPRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Send OTP verification code to user email."""
    try:
        # Generate OTP code
        code = security_service.generate_email_code(request.email)
        
        # Send email
        success = await email_service.send_otp_verification(
            to_email=request.email,
            user_name="User",  # You might want to fetch user name from DB
            code=code,
            action=request.action or "verify your account"
        )
        
        if success:
            return {
                "message": "OTP code sent successfully",
                "email": request.email,
                "expires_in": "10 minutes"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP code"
            )
            
    except Exception as e:
        logger.error(f"Error sending OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP code"
        )


@router.post("/email/send-welcome")
async def send_welcome_email(
    request: WelcomeEmailRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Send welcome/onboarding email to new user."""
    try:
        success = await email_service.send_welcome_email(
            to_email=request.email,
            user_name=request.user_name,
            dashboard_url=request.dashboard_url
        )
        
        if success:
            return {
                "message": "Welcome email sent successfully",
                "email": request.email
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send welcome email"
            )
            
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send welcome email"
        )


@router.post("/email/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Request password reset email."""
    try:
        # Generate reset code
        settings = get_settings()
        code = security_service.generate_email_code(request.email)
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        reset_url = f"{frontend_url}/reset-password?email={request.email}&code={code}"
        
        # Send email
        success = await email_service.send_password_reset(
            to_email=request.email,
            user_name="User",
            reset_code=code,
            reset_url=reset_url
        )
        
        if success:
            return {
                "message": "Password reset email sent successfully",
                "email": request.email,
                "expires_in": "1 hour"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
            
    except Exception as e:
        logger.error(f"Error sending password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )


@router.post("/email/confirm-password-reset")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with code and update password."""
    try:
        is_valid = security_service.verify_email_code(request.email, request.code)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code"
            )
        
        result = await db.execute(
            select(User).where(User.email == request.email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        is_valid, err = validate_password_strength(request.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err
            )
        
        new_hash = get_password_hash(request.new_password)
        is_reused, reuse_err = await check_password_reuse(db, user, new_hash)
        if is_reused:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reuse_err
            )
        
        await save_password_to_history(db, user, user.password_hash)
        user.password_hash = new_hash
        user.password_changed_at = datetime.utcnow()
        user.failed_login_attempts = 0
        
        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            action=AuditAction.PASSWORD_RESET_COMPLETED,
            details={"ip_source": "password_reset_flow"}
        )
        db.add(audit_log)
        
        await db.commit()
        
        del security_service.verification_codes[request.email]
        
        return {
            "message": "Password reset successfully",
            "email": request.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm password reset"
        )


@router.post("/email/send-security-alert")
async def send_security_alert(
    request: SecurityAlertRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Send security alert email."""
    try:
        success = await email_service.send_security_alert(
            to_email=request.email,
            user_name="User",
            action=request.action,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )
        
        if success:
            return {
                "message": "Security alert sent successfully",
                "email": request.email,
                "action": request.action
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send security alert"
            )
            
    except Exception as e:
        logger.error(f"Error sending security alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send security alert"
        )


@router.post("/email/send-account-suspended")
async def send_account_suspended(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Send account suspension email (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    email = request.get("email")
    user_name = request.get("user_name", "User")
    status = request.get("status", "Suspended")
    reason = request.get("reason", "Account action required")
    actions = request.get("actions", [])
    
    success = await email_service.send_account_suspended(
        to_email=email,
        user_name=user_name,
        status=status,
        reason=reason,
        actions=actions
    )
    
    if success:
        return {
            "message": "Account notification sent successfully",
            "email": email,
            "status": status
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send account notification"
        )


@router.post("/email/send-custom")
async def send_custom_email(
    request: CustomEmailRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Send custom email content (admin/authorized users only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    success = await email_service.send_custom_email(
        to_email=request.to_email,
        subject=request.subject,
        html_content=request.html_content
    )
        
    if success:
        return {
            "message": "Custom email sent successfully",
            "to_email": request.to_email,
            "subject": request.subject
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send custom email"
        )


@router.get("/email/verify-otp/{email}/{code}")
async def verify_otp_code(email: str, code: str):
    """Verify OTP code (for testing purposes)."""
    try:
        is_valid = security_service.verify_email_code(email, code)
        
        return {
            "email": email,
            "code": code,
            "valid": is_valid,
            "message": "Code is valid" if is_valid else "Code is invalid or expired"
        }
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP code"
        )
