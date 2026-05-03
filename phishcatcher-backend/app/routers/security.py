"""
Security Router for Risk-Based Authentication

This router handles security-related endpoints including:
- Risk assessment for actions
- Email verification codes
- OAuth re-authentication
- Security alerts
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import User
from app.services.security_service import security_service
from app.routers.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Security"])


@router.get(
    "/me/security/requirements",
    summary="Get security requirements",
    description="Returns the security requirements (e.g., MFA, email verification) needed for a specific action.",
)
async def get_security_requirements(
    action: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get security requirements for an action."""
    return security_service.get_security_requirements(current_user, action)


@router.post(
    "/me/security/verify/email",
    summary="Send email verification code",
    description="Sends a verification code to the user's email for sensitive operations. Returns expiry time.",
)
async def send_email_verification(
    action: str,
    current_user: User = Depends(get_current_active_user)
):
    """Send email verification code for sensitive operations."""
    security_reqs = security_service.get_security_requirements(current_user, action)
    
    if security_reqs["method"] == "email":
        code = await security_service.generate_email_code(current_user.id)
        success = await security_service.send_verification_email(
            current_user.email, code, action
        )
        
        if success:
            return {
                "message": "Verification code sent to your email",
                "expires_in": "10 minutes"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification code"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This action requires {security_reqs['method']} verification"
        )


@router.post(
    "/auth/reauth/google",
    summary="Google OAuth re-authentication",
    description="Endpoint for re-authenticating Google OAuth users before sensitive operations.",
)
async def reauth_google(
    current_user: User = Depends(get_current_active_user)
):
    """Re-authenticate Google OAuth user for sensitive operations."""
    return {
        "message": "OAuth re-authentication endpoint",
        "user_email": current_user.email
    }