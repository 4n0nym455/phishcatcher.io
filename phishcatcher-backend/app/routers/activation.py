"""
Account Activation Router

Fixed:
  - complete_activation now creates a Redis session after issuing tokens,
    so the session middleware accepts subsequent requests from newly activated users.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.database import get_db, get_redis
from app.services.activation_service import activation_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["activation"])


class ActivationRequest(BaseModel):
    token: str
    email: EmailStr


class ActivationVerifyRequest(BaseModel):
    token: str
    email: EmailStr
    code: str
    terms_accepted: bool
    privacy_accepted: bool


@router.post("/activate/verify-token")
async def verify_activation_token(
    request: ActivationRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.account_status == "active":
            return {"valid": True, "message": "Account is already activated", "already_activated": True}

        token_valid = activation_service.verify_activation_token(str(user.id), request.token)
        if not token_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token")

        return {
            "valid": True,
            "message": "Activation token is valid",
            "user": {"email": user.email, "full_name": user.full_name}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying activation token: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify activation token")


@router.post("/activate/complete")
async def complete_activation(
    request: ActivationVerifyRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
):
    try:
        if not request.terms_accepted or not request.privacy_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept both Terms & Conditions and Privacy Policy"
            )

        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.account_status == "active":
            return {"success": True, "message": "Account is already activated", "already_activated": True}

        token_valid = activation_service.verify_activation_token(str(user.id), request.token)
        if not token_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token")

        code_valid = activation_service.verify_activation_code(str(user.id), request.code)
        if not code_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation code")

        # Activate user
        user.account_status = "active"
        user.is_verified = True
        user.email_verified = True
        user.updated_at = datetime.utcnow()
        await db.commit()

        logger.info(f"User account activated: {user.email}")

        # Send welcome email (non-blocking)
        from app.services.email_service import email_service
        try:
            await email_service.send_welcome_email(
                to_email=user.email,
                user_name=user.full_name or user.email.split('@')[0]
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email: {e}")

        # Generate tokens
        from app.services.security import create_access_token, create_refresh_token
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # FIX: create Redis session so session middleware accepts subsequent requests.
        # Without this, the middleware rejects the returned token on the very next request.
        from app.core.session_manager import get_session_manager
        session_manager = get_session_manager(redis)
        await session_manager.create_session(
            user_id=str(user.id),
            user_email=user.email,
            ip_address="activation",
            user_agent="account-activation"
        )

        return {
            "success": True,
            "message": "Account activated successfully! Redirecting to dashboard...",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "account_status": user.account_status
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing activation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete activation")


@router.post("/activate/resend")
async def resend_activation_email(
    email: EmailStr,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.account_status == "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is already activated")

        activation_token = activation_service.generate_activation_token(str(user.id))
        activation_code = activation_service.generate_activation_code(str(user.id))

        email_sent = await activation_service.send_activation_email(
            user_email=user.email,
            user_name=user.full_name or user.email.split('@')[0],
            user_id=str(user.id),
            activation_token=activation_token,
            activation_code=activation_code
        )

        if not email_sent:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send activation email")

        return {"success": True, "message": "Activation email sent successfully", "email": user.email}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending activation email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to resend activation email")


@router.get("/activate/status/{email}")
async def check_activation_status(email: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return {"exists": False, "message": "User not found"}

        return {
            "exists": True,
            "account_status": user.account_status,
            "email_verified": user.email_verified,
            "is_active": user.is_active,
            "message": "User found"
        }
    except Exception as e:
        logger.error(f"Error checking activation status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check activation status")