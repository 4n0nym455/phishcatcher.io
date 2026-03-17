"""
Authentication Router

This module handles all authentication-related endpoints including:
- User registration
- Login with OTP
- Token refresh
- Password reset
- Google OAuth
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response, Body, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_redis, get_db_session
from app.models.user import User
from app.models.audit_log import AuditLog, AuditAction
from app.services.email import send_password_reset_email, send_password_change_notification
from app.services.email_service import EmailService
from app.services.sendgrid_service import sendgrid_service
from app.services.password_history import check_password_reuse, save_password_to_history
from app.services.gmail_service import GmailService
from app.routers.security import router as security_router
from app.services.google_oauth import google_oauth_service
from app.services.security import (
    verify_password, get_password_hash, generate_totp_secret, generate_totp_uri,
    generate_qr_code, verify_totp_token, encrypt_mfa_secret, decrypt_mfa_secret,
    create_access_token, create_refresh_token, verify_token, get_token_expiry,
    generate_otp, verify_otp, check_mfa_rate_limit, clear_mfa_rate_limit,
    encrypt_backup_codes, decrypt_backup_codes, should_lock_account,
    should_lock_otp_account, calculate_lock_time, is_account_locked
)
from app.schemas.auth import (  # ✅ Fixed: correct class names
    UserCreate, UserResponse, PasswordChange,
    PasswordReset, PasswordResetRequest, PasswordResetVerify,
    UserLogin, LoginResponse, OTPVerify, TokenRefresh, ResendOTP, Token,  # ✅ Use Token not TokenResponse
    DeleteAccountRequest,
    MFASetupRequest, MFASetupResponse, MFAVerifyRequest,
    MFAEnableRequest, MFADisableRequest, MFAStatusResponse,
    MFAVerification, OTPVerificationResponse, GoogleAuthUrl,
    GoogleCallback
)

logger = logging.getLogger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def get_gmail_base_email(email: str) -> str:
    """
    Get the base Gmail email by removing dots and aliases.
    This is used for alias detection, not for storage.
    """
    if not email:
        return email
        
    email = email.strip().lower()
    
    try:
        local_part, domain = email.split('@', 1)
    except ValueError:
        return email
    
    gmail_domains = ['gmail.com', 'googlemail.com']
    
    if domain in gmail_domains:
        # Remove aliases
        if '+' in local_part:
            local_part = local_part.split('+')[0]
        # Remove all dots for comparison
        local_part = local_part.replace('.', '')
    
    return f"{local_part}@{domain}"


def normalize_email(email: str) -> str:
    """
    Normalize email address to prevent alias abuse.
    
    Handles:
    - Gmail aliases (test+alias@gmail.com -> test@gmail.com)
    - Google Workspace aliases
    - Dots in Gmail addresses (test.test@gmail.com -> test@gmail.com)
    - Case insensitivity
    - Leading/trailing whitespace
    
    Args:
        email: Original email address
        
    Returns:
        Normalized email address
    """
    if not email:
        return email
        
    # Remove whitespace and convert to lowercase
    email = email.strip().lower()
    
    # Split local part and domain
    try:
        local_part, domain = email.split('@', 1)
    except ValueError:
        return email  # Invalid email format, return as-is
    
    # List of domains that support alias removal and dot removal
    gmail_domains = ['gmail.com', 'googlemail.com']
    
    # Normalize Gmail addresses
    if domain in gmail_domains:
        # Remove everything after + (aliases)
        if '+' in local_part:
            local_part = local_part.split('+')[0]
        
        # Remove all dots
        local_part = local_part.replace('.', '')
    
    # For other common providers, you can add specific rules
    # Outlook/Hotmail: Remove aliases after +
    elif domain in ['outlook.com', 'hotmail.com', 'live.com']:
        if '+' in local_part:
            local_part = local_part.split('+')[0]
    
    # Yahoo: Remove aliases after -
    elif domain in ['yahoo.com', 'ymail.com']:
        if '-' in local_part:
            local_part = local_part.split('-')[0]
    
    return f"{local_part}@{domain}"


def is_email_alias(original_email: str, stored_email: str) -> bool:
    """
    Check if an email is an alias of a stored email.
    
    Args:
        original_email: The email being checked
        stored_email: The email stored in database
        
    Returns:
        True if original_email is an alias of stored_email
    """
    return get_gmail_base_email(original_email) == get_gmail_base_email(stored_email)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if current_user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked"
        )
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Normalize the email for checking
    normalized_email = normalize_email(user_data.email)
    
    # Check if user already exists (exact match)
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check for email aliases (prevent abuse) - use proper alias detection
    existing_users = await db.execute(select(User).where(User.deleted_at.is_(None)))
    for existing_user in existing_users.scalars().all():
        if is_email_alias(user_data.email, existing_user.email):
            logger.warning(f"Email alias registration attempt: {user_data.email} -> {existing_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address or an alias of it is already registered. Please use a different email address."
            )
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Create user
    user = User(
        email=user_data.email,
        normalized_email=normalized_email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        company=user_data.company
    )
    
    db.add(user)
    await db.flush()
    
    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action=AuditAction.USER_REGISTERED,
        resource_type="user",
        resource_id=str(user.id),  # Convert UUID to string
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"User registered: {user.email}")
    
    return user


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Login and receive OTP for verification."""
    # Find user - try exact match first
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # If not found, try to find by alias detection
    if not user:
        all_users = await db.execute(select(User))
        for potential_user in all_users.scalars().all():
            if is_email_alias(form_data.username, potential_user.email):
                user = potential_user
                break
    
    # Check credentials
    if not user or not verify_password(form_data.password, user.password_hash):
        # Handle failed login attempt
        if user:
            user.failed_login_attempts += 1
            
            # Check if account should be locked
            if should_lock_account(user.failed_login_attempts):
                user.locked_until = calculate_lock_time(5)  # Lock for 5 minutes
                
                # Log account lockout
                audit_log = AuditLog(
                    user_id=user.id,
                    user_email=user.email,
                    action=AuditAction.LOGIN,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    status="failure",
                    details={
                        "reason": "account_locked",
                        "failed_attempts": user.failed_login_attempts,
                        "locked_until": user.locked_until.isoformat()
                    }
                )
                db.add(audit_log)
                await db.commit()
                
                logger.warning(f"Account locked due to failed login attempts: {user.email}")
                
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account temporarily locked due to multiple failed login attempts. Please try again in 5 minutes."
                )
            else:
                # Log failed attempt with remaining attempts
                remaining_attempts = 5 - user.failed_login_attempts
                audit_log = AuditLog(
                    user_id=user.id,
                    user_email=user.email,
                    action=AuditAction.LOGIN,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    status="failure",
                    details={
                        "reason": "invalid_credentials",
                        "failed_attempts": user.failed_login_attempts,
                        "remaining_attempts": remaining_attempts
                    }
                )
                db.add(audit_log)
        else:
            # Log failed attempt for unknown user
            audit_log = AuditLog(
                user_id=None,
                user_email=form_data.username,
                action=AuditAction.LOGIN,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                status="failure",
                details={"reason": "user_not_found"}
            )
            db.add(audit_log)
        
        await db.commit()
        
        error_message = "Invalid email or password"
        if user and user.failed_login_attempts > 0:
            remaining_attempts = 5 - user.failed_login_attempts
            if remaining_attempts > 0:
                error_message += f". {remaining_attempts} attempts remaining before account lockout."
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is temporarily locked due to multiple failed attempts. Please try again after {user.locked_until.strftime('%H:%M:%S')}."
        )
    
    # Reset failed login attempts on successful credential verification
    user.failed_login_attempts = 0
    user.locked_until = None
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Generate OTP
    otp = generate_otp()
    settings = get_settings()
    
    # Store OTP in Redis
    otp_key = f"otp:{user.email}"
    await redis.setex(otp_key, settings.OTP_EXPIRE_MINUTES * 60, otp)
    
    # Store login attempt
    attempt_key = f"login_attempt:{user.email}"
    await redis.setex(attempt_key, settings.OTP_EXPIRE_MINUTES * 60, "pending")
    
    # Log login attempt
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action=AuditAction.LOGIN,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
        details={"step": "credentials_verified", "otp_sent": True}
    )
    db.add(audit_log)
    await db.commit()
    
    # Send OTP via email
    email_service = EmailService()
    try:
        await email_service.send_otp_verification(
            to_email=user.email,
            user_name=user.full_name or user.email,
            code=otp,
            action="verify your login"
        )
        logger.info(f"OTP sent to {user.email}: {otp}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {e}")
        # Continue with login process even if email fails (OTP is still stored in Redis)
    
    # Check if user has MFA enabled and create MFA session token
    if user.mfa_enabled:
        mfa_session_token = create_mfa_session_token(
            data={"sub": str(user.id), "type": "mfa_session"}, 
            expires_delta=timedelta(minutes=15)
        )
        
        return LoginResponse(
            message="OTP sent to your email",
            email=user.email,
            mfa_required=True,
            mfa_session_token=mfa_session_token
        )
    
    return LoginResponse(
        message="OTP sent to your email",
        email=user.email,
        mfa_required=False
    )


@router.post("/verify-otp", response_model=OTPVerificationResponse)
async def verify_otp(
    otp_data: OTPVerify,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Verify OTP and issue tokens."""
    # Get user
    result = await db.execute(select(User).where(User.email == otp_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is temporarily locked due to multiple failed attempts. Please try again after {user.locked_until.strftime('%H:%M:%S')}."
        )
    
    # Get stored OTP
    otp_key = f"otp:{otp_data.email}"
    stored_otp = await redis.get(otp_key)
    
    if not stored_otp or stored_otp != otp_data.otp:
        # Handle failed OTP attempt
        user.failed_otp_attempts += 1
        
        # Check if account should be locked due to OTP failures
        if should_lock_otp_account(user.failed_otp_attempts):
            user.locked_until = calculate_lock_time(5)  # Lock for 5 minutes
            
            # Log OTP lockout
            audit_log = AuditLog(
                user_id=user.id,
                user_email=user.email,
                action=AuditAction.MFA_FAILURE,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                status="failure",
                details={
                    "reason": "otp_account_locked",
                    "failed_otp_attempts": user.failed_otp_attempts,
                    "locked_until": user.locked_until.isoformat()
                }
            )
            db.add(audit_log)
            await db.commit()
            
            logger.warning(f"Account locked due to failed OTP attempts: {user.email}")
            
            # Clear OTP from Redis
            await redis.delete(otp_key)
            await redis.delete(f"login_attempt:{user.email}")
            
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to multiple failed OTP attempts. Please try again in 5 minutes."
            )
        else:
            # Log failed OTP attempt with remaining attempts
            remaining_attempts = 3 - user.failed_otp_attempts
            audit_log = AuditLog(
                user_id=user.id,
                user_email=user.email,
                action=AuditAction.MFA_FAILURE,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                status="failure",
                details={
                    "reason": "invalid_otp",
                    "failed_otp_attempts": user.failed_otp_attempts,
                    "remaining_attempts": remaining_attempts
                }
            )
            db.add(audit_log)
            await db.commit()
        
        error_message = "Invalid OTP"
        if user.failed_otp_attempts > 0:
            remaining_attempts = 3 - user.failed_otp_attempts
            if remaining_attempts > 0:
                error_message += f". {remaining_attempts} attempts remaining before account lockout."
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Clear OTP
    await redis.delete(otp_key)
    
    # Reset failed OTP attempts on successful verification
    user.failed_otp_attempts = 0
    
    # Update user
    user.last_login = datetime.utcnow()
    user.last_login_ip = request.client.host if request.client else None
    user.failed_login_attempts = 0
    
    # Check if user has MFA enabled
    if user.mfa_enabled:
        # Generate MFA session token (short-lived)
        mfa_session_token = create_mfa_session_token(
            data={"sub": str(user.id)}, 
            expires_delta=timedelta(minutes=10)
        )
        
        # Clear OTP
        await redis.delete(otp_key)
        
        # Log MFA required
        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            action=AuditAction.MFA_REQUIRED,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            status="success"
        )
        db.add(audit_log)
        await db.commit()
        
        # Update user to show MFA in progress
        user.mfa_session_created = datetime.utcnow()
        await db.commit()
        
        return OTPVerificationResponse(
            mfa_required=True,
            mfa_session_token=mfa_session_token,
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        )
    
    # Generate tokens (non-MFA users)
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store session with pure Redis TTL management
    from app.core.session_manager import get_session_manager
    session_manager = get_session_manager(redis)
    
    await session_manager.create_session(
        user_id=str(user.id),
        user_email=user.email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")
    )
    
    # Log successful login
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action=AuditAction.LOGIN,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
        details={"step": "otp_verified", "login_completed": True}
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"User logged in: {user.email}")
    
    return OTPVerificationResponse(
            mfa_required=False,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        )


@router.post("/resend-otp", response_model=dict)
async def resend_otp(
    otp_data: ResendOTP,  # ✅ Use ResendOTP schema instead of OTPVerify
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Resend OTP for login verification."""
    # Get user
    result = await db.execute(select(User).where(User.email == otp_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is temporarily locked due to multiple failed attempts. Please try again after {user.locked_until.strftime('%H:%M:%S')}."
        )
    
    # Check if there's an existing login attempt
    attempt_key = f"login_attempt:{user.email}"
    existing_attempt = await redis.get(attempt_key)
    
    if not existing_attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active login session found. Please login again."
        )
    
    # Generate new OTP
    otp = generate_otp()
    settings = get_settings()
    
    # Store new OTP in Redis
    otp_key = f"otp:{user.email}"
    await redis.setex(otp_key, settings.OTP_EXPIRE_MINUTES * 60, otp)
    
    # Extend login attempt session
    await redis.setex(attempt_key, settings.OTP_EXPIRE_MINUTES * 60, "pending")
    
    # Send OTP via email
    try:
        from app.services.email import send_otp_email
        await send_otp_email(user.email, otp)
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email"
        )
    
    # Log OTP resend
    audit_log = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action=AuditAction.OTP_SENT,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
        details={"action": "resend"}
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"OTP resent to: {user.email}")
    
    return {
        "message": "OTP resent successfully",
        "email": user.email
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Generate new tokens
    access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """Logout user and invalidate session."""
    # Remove session from Redis
    session_key = f"session:{current_user.id}"
    await redis.delete(session_key)
    
    # Log logout
    async with get_db_session() as db:
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            action=AuditAction.LOGOUT,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            status="success"
        )
        db.add(audit_log)
        await db.commit()
    
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Request password reset."""
    result = await db.execute(select(User).where(User.email == reset_request.email))
    user = result.scalar_one_or_none()
    
    if user:
        # Generate reset token
        reset_token = create_access_token(
            {"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Store in Redis
        reset_key = f"password_reset:{user.id}"
        await redis.setex(reset_key, 3600, reset_token)
        
        # Send email
        settings = get_settings()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        await send_password_reset_email(user.email, reset_url)
        
        logger.info(f"Password reset requested for {user.email}")
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Reset password using reset token."""
    payload = verify_token(reset_data.token)
    
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if reset token was used
    reset_key = f"password_reset:{user.id}"
    stored_token = await redis.get(reset_key)
    
    if not stored_token or stored_token != reset_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token already used or expired"
        )
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(reset_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Hash the new password to check against history
    new_password_hash = get_password_hash(reset_data.new_password)
    
    # Check password reuse
    is_reused, reuse_error = await check_password_reuse(db, user, new_password_hash)
    if is_reused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reuse_error
        )
    
    # Save old password to history
    await save_password_to_history(db, user, user.password_hash)
    
    # Update password
    user.password_hash = new_password_hash
    user.password_changed_at = datetime.utcnow()
    
    # Clear reset token
    await redis.delete(reset_key)
    
    await db.commit()
    
    # Send password change notification
    await send_password_change_notification(user.email)
    


@router.get("/google/url")
async def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    try:
        result = google_oauth_service.get_auth_url()
        return GoogleAuthUrl(auth_url=result["auth_url"], state=result["state"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google OAuth URL generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Google OAuth URL"
        )


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Handle Google OAuth callback - redirects to frontend."""
    try:
        token_data = await google_oauth_service.handle_oauth_callback(code, state)
        
        if not token_data.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Google"
            )
        
        # Check if user exists
        result = await db.execute(select(User).where(User.email == token_data['email']))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                email=token_data['email'],
                normalized_email=normalize_email(token_data['email']),  # Add normalized email
                password_hash=get_password_hash(secrets.token_urlsafe(32)),  # Random password
                full_name=token_data.get('name'),
                email_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Create access tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Store session with Redis TTL management
        from app.core.session_manager import get_session_manager
        session_manager = get_session_manager(redis)
        
        await session_manager.create_session(
            user_id=str(user.id),
            user_email=user.email,
            ip_address="127.0.0.1",  # OAuth callback doesn't have request object
            user_agent="Google OAuth"
        )
        
        # Redirect to frontend with tokens
        settings = get_settings()
        redirect_url = f"{settings.FRONTEND_URL}/google/callback?success=true&access_token={access_token}&refresh_token={refresh_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        settings = get_settings()
        redirect_url = f"{settings.FRONTEND_URL}/google/callback?error=true&message={str(e)}"
        return RedirectResponse(url=redirect_url)


@router.post("/google/callback")
async def google_callback_post(
    request: GoogleCallback,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Handle Google OAuth callback - API endpoint for popup."""
    try:
        token_data = await google_oauth_service.handle_oauth_callback(request.code, request.state)
        
        if not token_data.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=token_data.get('error', 'Failed to authenticate with Google')
            )
        
        # Check if user exists
        result = await db.execute(select(User).where(User.email == token_data['email']))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user with pending status
            user = User(
                email=token_data['email'],
                normalized_email=normalize_email(token_data['email']),
                password_hash=get_password_hash(secrets.token_urlsafe(32)),
                full_name=token_data.get('name'),
                email_verified=True,
                account_status="pending"  # New OAuth users start as pending
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Generate activation token and code
            from app.services.activation_service import activation_service
            activation_token = activation_service.generate_activation_token(str(user.id))
            activation_code = activation_service.generate_activation_code(str(user.id))
            
            # Send activation email
            email_sent = await activation_service.send_activation_email(
                user_email=user.email,
                user_name=user.full_name or user.email.split('@')[0],
                user_id=str(user.id),
                activation_token=activation_token,
                activation_code=activation_code
            )
            
            if not email_sent:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send activation email"
                )
            
            return {
                "activation_required": True,
                "message": "Please check your email for activation instructions",
                "email": user.email,
                "full_name": user.full_name
            }
        
        # Handle existing users
        if user.account_status == "pending":
            # User exists but not activated - resend activation
            from app.services.activation_service import activation_service
            activation_token = activation_service.generate_activation_token(str(user.id))
            activation_code = activation_service.generate_activation_code(str(user.id))
            
            email_sent = await activation_service.send_activation_email(
                user_email=user.email,
                user_name=user.full_name or user.email.split('@')[0],
                user_id=str(user.id),
                activation_token=activation_token,
                activation_code=activation_code
            )
            
            return {
                "activation_required": True,
                "message": "Your account is still pending activation. Please check your email.",
                "email": user.email,
                "full_name": user.full_name
            }
        
        # Check if user has MFA enabled
        if user.mfa_enabled:
            # Generate MFA session token (short-lived)
            mfa_session_token = create_mfa_session_token(
                data={"sub": str(user.id), "type": "mfa_session"}, 
                expires_delta=timedelta(minutes=10)
            )
            
            return {
                "mfa_required": True,
                "mfa_session_token": mfa_session_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                }
            }
        
        # Create access tokens for active users
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Store session with Redis TTL management
        from app.core.session_manager import get_session_manager
        session_manager = get_session_manager(redis)
        
        await session_manager.create_session(
            user_id=str(user.id),
            user_email=user.email,
            ip_address="127.0.0.1",  # OAuth callback doesn't have request object
            user_agent="Google OAuth POST"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        }
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/google/callback")
async def auth_google_callback_post(
    request: GoogleCallback,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback - API endpoint for popup (alternative route)."""
    # This is an alias to the main callback handler
    return await google_callback_post(request, db)


@router.post("/mfa/verify")
async def verify_mfa(
    request: MFAVerification,
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA code for users with MFA enabled."""
    try:
        logger.info(f"MFA verification attempt with token: {request.mfa_session_token[:20]}...")
        logger.info(f"MFA verification: Full token received: {request.mfa_session_token}")
        
        # Verify MFA session token
        payload = verify_token(request.mfa_session_token, token_type="mfa_session")
        
        logger.info(f"MFA verification: Token payload received: {payload}")
        logger.info(f"MFA verification: Token type check: expected='mfa_session', actual='{payload.get('type') if payload else 'None'}'")
        
        if not payload:
            logger.error("MFA verification: Invalid or expired session token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token"
            )
        
        if payload.get("type") != "mfa_session":
            logger.error(f"MFA verification: Invalid token type: {payload.get('type')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token"
            )
        
        user_id = payload.get("sub")
        logger.info(f"MFA verification: User ID from token: {user_id}")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.mfa_enabled:
            logger.error(f"MFA verification: User not found or MFA not enabled for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user or MFA not enabled"
            )
        
        # Verify MFA code using TOTP
        logger.info(f"MFA verification: User {user.email} MFA enabled: {user.mfa_enabled}")
        logger.info(f"MFA verification: User MFA secret exists: {bool(user.mfa_secret)}")
        logger.info(f"MFA verification: Received code: {request.code}")
        
        # Decrypt MFA secret before verification
        decrypted_secret = decrypt_mfa_secret(user.mfa_secret)
        logger.info(f"MFA verification: Secret decrypted successfully: {bool(decrypted_secret)}")
        
        is_valid = verify_totp_token(decrypted_secret, request.code)
        logger.info(f"MFA verification: TOTP verification result: {is_valid}")
        
        if not is_valid:
            logger.error(f"MFA verification: Invalid TOTP code for user {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA code"
            )
        
        # Create access tokens after MFA verification
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        response = OTPVerificationResponse(
            mfa_required=False,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        )
        
        logger.info(f"MFA verification: Successful response prepared for user {user.email}")
        logger.info(f"MFA verification: Response mfa_required: {response.mfa_required}")
        logger.info(f"MFA verification: Response access_token: {response.access_token[:20] if response.access_token else 'None'}...")
        
        return response
        
    except Exception as e:
        logger.error(f"MFA verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.post("/me/delete")
async def delete_account(
    password: str = Form(...),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user account (requires password confirmation)."""
    # Verify password
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    try:
        # Create audit log before deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            action=AuditAction.USER_DELETED,
            resource_type="user",
            resource_id=str(current_user.id),
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            status="success",
            details={"reason": "User requested account deletion"}
        )
        db.add(audit_log)
        
        # Soft delete the user
        current_user.deleted_at = datetime.utcnow()
        current_user.is_active = False
        current_user.email = f"deleted_{current_user.id}@deleted.com"
        
        # Clear sensitive data
        current_user.password_hash = "deleted"  # Cannot be NULL, set to placeholder
        current_user.gmail_credentials = None
        current_user.gmail_email = None
        current_user.mfa_secret = None
        
        await db.commit()
        
        logger.info(f"User account deleted: {current_user.email}")
        
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )


@router.put("/me/password")
async def change_password(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Change current user password."""
    # Parse JSON body and extract body content
    import json
    try:
        # First check if there's any body at all
        body_bytes = await request.body()
        logger.info(f"Raw body bytes: {body_bytes}")
        
        if not body_bytes:
            logger.error("Empty request body received")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Empty request body"
            )
        
        raw_data = json.loads(body_bytes.decode('utf-8'))
        logger.info(f"Raw JSON received: {raw_data}")
        
        current_password = raw_data.get('current_password')
        new_password = raw_data.get('new_password')
        
        logger.info(f"Extracted passwords: current_password={current_password}, new_password={new_password}")
        
        if not current_password or not new_password:
            logger.error(f"Missing passwords. current_password={current_password}, new_password={new_password}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Both current_password and new_password are required"
            )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error parsing request: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid request format: {str(e)}"
        )
    
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Hash the new password to check against history
    new_password_hash = get_password_hash(new_password)
    
    # Check password reuse
    is_reused, reuse_error = await check_password_reuse(db, current_user, new_password_hash)
    if is_reused:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reuse_error
        )
    
    # Save old password to history
    await save_password_to_history(db, current_user, current_user.password_hash)
    
    # Update password
    current_user.password_hash = new_password_hash
    current_user.password_changed_at = datetime.utcnow()
    
    # Invalidate all other sessions (keep current one active)
    session_pattern = f"session:{current_user.id}:*"
    # Note: This would require modifying session storage to include device identifiers
    # For now, we'll keep current session active
    
    # Log password change
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.PASSWORD_CHANGED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    # Send password change notification email
    await send_password_change_notification(
        current_user.email, 
        request.client.host if request.client else None
    )
    
    logger.info(f"Password changed for {current_user.email}")
    
    return {"message": "Password changed successfully"}


# MFA Endpoints
@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: Request,
    setup_data: MFASetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Set up MFA for user account."""
    # Rate limiting check
    allowed, message = check_mfa_rate_limit(str(current_user.id), "setup", max_attempts=3, window_minutes=30)
    if not allowed:
        logger.warning(f"MFA setup rate limit exceeded for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message
        )
    
    # Password verification is no longer required for MFA setup
    # All users (OAuth and regular) can set up MFA without password
    # Security is maintained through MFA verification process and rate limiting
    logger.info(f"MFA setup initiated for {current_user.email} - password verification not required")
    
    # Generate new TOTP secret
    secret = generate_totp_secret()
    
    # Generate QR code
    uri = generate_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)
    
    # Generate secure alphanumeric backup codes
    backup_codes = [generate_otp(8) for _ in range(12)]
    
    # Generate MFA setup session token for validation
    from app.services.security import create_access_token
    mfa_session_token = create_access_token(
        data={"sub": str(current_user.id), "type": "mfa_setup", "backup_codes": backup_codes},
        expires_delta=timedelta(minutes=15)  # 15-minute session
    )
    
    # Store encrypted secret temporarily (not enabled yet)
    current_user.mfa_secret = encrypt_mfa_secret(secret)
    
    # Store encrypted backup codes temporarily
    from app.services.security import encrypt_backup_codes
    current_user.mfa_backup_codes = encrypt_backup_codes(backup_codes)
    
    await db.commit()
    
    # Log MFA setup initiation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.MFA_SETUP_INITIATED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"MFA setup initiated for {current_user.email}")
    
    return MFASetupResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes,
        mfa_session_token=mfa_session_token,  # Add session token for validation
        instructions=(
            "1. Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)\n"
            "2. Or manually enter the secret key in your app\n"
            "3. Enter the 6-digit code from your app to verify and enable MFA\n"
            "4. Save the backup codes in a secure location for account recovery\n"
            "5. This setup session expires in 15 minutes for security"
        )
    )


@router.post("/mfa/verify", response_model=dict)
async def verify_mfa_setup(
    request: Request,
    verify_data: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA setup and enable MFA."""
    # Rate limiting check
    allowed, message = check_mfa_rate_limit(str(current_user.id), "verify", max_attempts=5, window_minutes=15)
    if not allowed:
        logger.warning(f"MFA verification rate limit exceeded for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message
        )
    
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated"
        )
    
    # Decrypt secret and verify token
    try:
        secret = decrypt_mfa_secret(current_user.mfa_secret)
        if not verify_totp_token(secret, verify_data.token):
            logger.warning(f"Invalid MFA token for setup verification: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
    except Exception:
        logger.error(f"Error decrypting MFA secret for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying MFA setup"
        )
    
    # Enable MFA and store backup codes
    current_user.mfa_enabled = True
    
    # Store backup codes for account recovery (they were encrypted during setup)
    if verify_data.backup_codes:
        from app.services.security import encrypt_backup_codes
        current_user.mfa_backup_codes = encrypt_backup_codes(verify_data.backup_codes)
        current_user.mfa_backup_codes_used = []  # Initialize empty array for used codes
    
    # Clear rate limit on successful verification
    clear_mfa_rate_limit(str(current_user.id), "verify")
    
    await db.commit()
    
    # Log MFA enable
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.MFA_ENABLED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"MFA enabled for {current_user.email}")
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/enable", response_model=dict)
async def enable_mfa(
    request: Request,
    enable_data: MFAEnableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable MFA with verification token."""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not completed"
        )
    
    # Verify token
    try:
        secret = decrypt_mfa_secret(current_user.mfa_secret)
        if not verify_totp_token(secret, enable_data.token):
            logger.warning(f"Invalid MFA token for enable: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
    except Exception:
        logger.error(f"Error verifying MFA token for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error enabling MFA"
        )
    
    # Enable MFA
    current_user.mfa_enabled = True
    await db.commit()
    
    # Log MFA enable
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.MFA_ENABLED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"MFA enabled for {current_user.email}")
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable", response_model=dict)
async def disable_mfa(
    request: Request,
    disable_data: MFADisableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable MFA."""
    logger.info(f"MFA disable attempt for user: {current_user.email}")
    
    # Check if user is an OAuth user
    is_oauth_user = (
        current_user.gmail_credentials is not None or 
        current_user.gmail_email is not None or
        (current_user.password_hash and current_user.password_hash.startswith('$2b$12$kMMqwecAe9x2ubhZ.IH2Le'))
    )
    
    # For regular users, verify password first
    if not is_oauth_user:
        if not verify_password(disable_data.password, current_user.password_hash):
            logger.warning(f"Invalid password for MFA disable attempt: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        logger.info(f"Password verified for MFA disable: {current_user.email}")
    else:
        logger.info(f"OAuth user {current_user.email} disabling MFA - password verification skipped")
    
    # Verify current MFA token (required for all users)
    if current_user.mfa_enabled and current_user.mfa_secret:
        try:
            secret = decrypt_mfa_secret(current_user.mfa_secret)
            logger.info(f"MFA secret decrypted for disable: {current_user.email}")
            
            if not verify_totp_token(secret, disable_data.token):
                logger.warning(f"Invalid MFA token for disable: {current_user.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification code. Please enter the current 6-digit code from your authenticator app."
                )
            
            logger.info(f"MFA token verified for disable: {current_user.email}")
        except Exception as e:
            logger.error(f"Error verifying MFA token for disable: {current_user.email}, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error disabling MFA"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not currently enabled"
        )
    
    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    await db.commit()
    
    logger.info(f"MFA disabled in database for: {current_user.email}")
    
    # Log MFA disable
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.MFA_DISABLED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"MFA disabled successfully for {current_user.email}")
    
    return {"message": "MFA disabled successfully"}


@router.post("/mfa/verify-backup-code", response_model=dict)
async def verify_backup_code(
    request: Request,
    backup_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify MFA backup code for login or recovery."""
    backup_code = backup_data.get("backup_code")
    
    # Rate limiting check
    allowed, message = check_mfa_rate_limit(str(current_user.id), "backup_code", max_attempts=3, window_minutes=60)
    if not allowed:
        logger.warning(f"Backup code verification rate limit exceeded for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message
        )
    
    if not backup_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup code is required"
        )
    
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account"
        )
    
    # Check if backup codes exist
    if not current_user.mfa_backup_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No backup codes available for this account"
        )
    
    # Decrypt backup codes
    try:
        from app.services.security import decrypt_backup_codes
        backup_codes = decrypt_backup_codes(current_user.mfa_backup_codes)
    except Exception:
        logger.error(f"Error decrypting backup codes for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying backup code"
        )
    
    # Normalize backup code (remove spaces, make uppercase)
    normalized_code = backup_code.replace(" ", "").upper()
    
    # Check if code is valid
    if normalized_code not in backup_codes:
        logger.warning(f"Invalid backup code attempted for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid backup code"
        )
    
    # Check if code has already been used
    if current_user.mfa_backup_codes_used and normalized_code in current_user.mfa_backup_codes_used:
        logger.warning(f"Already used backup code attempted for {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup code has already been used"
        )
    
    # Mark backup code as used
    if not current_user.mfa_backup_codes_used:
        current_user.mfa_backup_codes_used = []
    
    current_user.mfa_backup_codes_used.append(normalized_code)
    
    # Remove from available codes and re-encrypt
    backup_codes.remove(normalized_code)
    from app.services.security import encrypt_backup_codes
    current_user.mfa_backup_codes = encrypt_backup_codes(backup_codes)
    
    # Generate new tokens for successful authentication
    from app.services.security import create_access_token, create_refresh_token
    
    access_token = create_access_token(data={"sub": str(current_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(current_user.id)})
    
    # Clear rate limit on successful verification
    clear_mfa_rate_limit(str(current_user.id), "backup_code")
    
    await db.commit()
    
    # Log backup code usage
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.MFA_BACKUP_CODE_USED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"Backup code verified successfully for {current_user.email}")
    
    return {
        "success": True,
        "message": "Backup code verified successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "mfa_enabled": current_user.mfa_enabled
        },
        "remaining_backup_codes": len(current_user.mfa_backup_codes) if current_user.mfa_backup_codes else 0
    }


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get MFA status for current user."""
    return MFAStatusResponse(
        enabled=current_user.mfa_enabled,
        setup_completed=bool(current_user.mfa_secret),
        has_backup_codes=False  # TODO: Implement backup codes storage
    )
