"""
activation.py  (router)

Handles:
  POST /activate/verify-token   – validate URL token (pre-flight)
  POST /activate/complete        – validate code + T&C → issue tokens + session
  POST /activate/resend          – resend email
  GET  /activate/status/{email}  – check account_status (used by frontend polling)

Tokens are issued exactly once here after successful activation so the user
lands directly on the dashboard.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, get_redis
from app.models.user import User
from app.services.activation_service import activation_service
from app.services.security import create_access_token, create_refresh_token
from app.core.session_manager import get_session_manager
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Activation"])


# ── Schema ─────────────────────────────────────────────────────────────────────

class VerifyTokenRequest(BaseModel):
    token: str
    email: EmailStr


class CompleteActivationRequest(BaseModel):
    token:           str
    email:           EmailStr
    code:            str
    terms_accepted:  bool
    privacy_accepted:bool


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/activate/verify-token",
    summary="Verify activation token",
    description="Pre-flight check: validates whether an activation URL token is still valid.",
)
async def verify_activation_token(
    body: VerifyTokenRequest,
    db:   AsyncSession = Depends(get_db),
):
    """Pre-flight check: is the token still valid?"""
    user = await _get_user_by_email(db, body.email)

    if user.account_status == "active":
        return {"valid": True, "already_activated": True,
                "message": "Account is already activated."}

    ok = await activation_service.verify_activation_token(str(user.id), body.token)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired activation link.")

    return {
        "valid":   True,
        "message": "Token is valid.",
        "user":    {"email": user.email, "full_name": user.full_name},
    }


@router.post(
    "/activate/complete",
    summary="Complete account activation",
    description="Validates token + activation code + T&C acceptance, activates the account, and returns JWT tokens.",
)
async def complete_activation(
    body:  CompleteActivationRequest,
    db:    AsyncSession = Depends(get_db),
    redis  = Depends(get_redis),
):
    """Validate token + code + T&C, activate account, return tokens."""
    if not body.terms_accepted or not body.privacy_accepted:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You must accept both Terms & Conditions and Privacy Policy.",
        )

    user = await _get_user_by_email(db, body.email)

    if user.account_status == "active":
        return {"success": True, "already_activated": True}

    # Validate token (URL parameter)
    token_ok = await activation_service.verify_activation_token(str(user.id), body.token)
    if not token_ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired activation link.")

    # Validate code (emailed 6-digit code)
    code_ok = await activation_service.verify_activation_code(str(user.id), body.code)
    if not code_ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired activation code.")

    # Activate
    user.account_status = "active"
    user.is_verified    = True
    user.email_verified = True
    user.updated_at     = datetime.now(timezone.utc)
    await db.commit()

    # Clean up Redis keys immediately
    await activation_service.delete_activation_keys(str(user.id))

    # Send welcome email (non-blocking)
    try:
        await email_service.send_welcome_email(
            to_email=user.email,
            user_name=user.full_name or user.email.split("@")[0],
        )
    except Exception as exc:
        logger.warning("Welcome email failed for %s: %s", user.email, exc)

    # Issue tokens
    access_token  = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Create Redis session
    session_mgr = get_session_manager(redis)
    await session_mgr.create_session(
        user_id=str(user.id),
        user_email=user.email,
        ip_address="activation",
        user_agent="account-activation",
    )

    logger.info("User %s activated successfully", user.email)
    return {
        "success":       True,
        "message":       "Account activated! Welcome to PhishCatcher.",
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user": {
            "id":             str(user.id),
            "email":          user.email,
            "full_name":      user.full_name,
            "role":           user.role,
            "account_status": user.account_status,
        },
    }


@router.post(
    "/activate/resend",
    summary="Resend activation email",
    description="Regenerates and resends the activation email with new token and code.",
)
async def resend_activation_email(
    body: VerifyTokenRequest,          # reuses {email, token} – token ignored here
    db:   AsyncSession = Depends(get_db),
):
    user = await _get_user_by_email(db, body.email)

    if user.account_status == "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Account is already activated.")

    token = await activation_service.generate_activation_token(str(user.id))
    code  = await activation_service.generate_activation_code(str(user.id))

    sent = await activation_service.send_activation_email(
        user_email=user.email,
        user_name=user.full_name or user.email.split("@")[0],
        user_id=str(user.id),
        activation_token=token,
        activation_code=code,
    )
    if not sent:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Failed to send activation email.")

    return {"success": True, "email": user.email}


@router.get(
    "/activate/status/{email}",
    summary="Check activation status",
    description="Returns the account status for a given email address (used by frontend polling).",
)
async def check_activation_status(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalar_one_or_none()
    if not user:
        return {"exists": False}
    return {
        "exists":         True,
        "account_status": user.account_status,
        "email_verified": user.email_verified,
        "is_active":      user.is_active,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_user_by_email(db: AsyncSession, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return user