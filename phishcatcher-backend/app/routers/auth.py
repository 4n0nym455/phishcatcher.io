"""
auth.py  (router)

Consolidated authentication router.

Endpoints:
  POST /auth/register            – create user, send activation email
  POST /auth/login               – validate credentials, send OTP
  POST /auth/verify-otp          – validate OTP, return tokens (or MFA challenge)
  POST /auth/resend-otp          – resend OTP within active login window
  POST /auth/refresh             – rotate access + refresh tokens
  POST /auth/logout              – destroy session
  POST /auth/forgot-password     – send password-reset email
  POST /auth/reset-password      – consume reset token, set new password
  GET  /auth/me                  – current user
  PUT  /auth/me/password         – change password (authenticated)
  PUT  /auth/me/phone            – update phone number (sends SMS OTP)
  POST /auth/me/phone/verify     – verify phone with SMS OTP code
  POST /auth/me/delete           – soft-delete account
  GET  /auth/google/url          – get Google OAuth URL
  POST /auth/google/callback     – exchange code for tokens
  GET  /auth/mfa/status
  POST /auth/mfa/setup
  POST /auth/mfa/verify          – used BOTH for setup-verify and login MFA check
  POST /auth/mfa/enable
  POST /auth/mfa/disable
  POST /auth/mfa/verify-backup-code
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, status, Depends, Body, Form
from fastapi import UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_redis, get_db_session
from app.models.user import User
from app.models.audit_log import AuditLog, AuditAction
from app.core.session_manager import get_session_manager
from app.services.email_service import (
    send_password_reset_email,
    send_password_change_notification,
    EmailService,
    email_service,
)
from app.services.password_history import check_password_reuse, save_password_to_history
from app.services.google_oauth import google_oauth_service
from app.services.activation_service import activation_service
from app.services.storage import StorageService, storage_service
from app.services.security import (
    verify_password, get_password_hash, generate_otp,
    encrypt_mfa_secret, decrypt_mfa_secret, encrypt_backup_codes, decrypt_backup_codes,
    create_access_token, create_refresh_token, create_password_reset_token, verify_token, get_token_expiry,
    should_lock_account, should_lock_otp_account, calculate_lock_time,
    check_mfa_rate_limit, clear_mfa_rate_limit,
    check_mfa_rate_limit_async, clear_mfa_rate_limit_async,
    create_mfa_session_token,
    is_ip_locked_async as is_ip_locked,
    should_lock_ip_based_async as should_lock_ip_based,
    increment_ip_failed_attempts_async as increment_ip_failed_attempts,
    lock_ip_address_async as lock_ip_address,
    reset_ip_failed_attempts_async as reset_ip_failed_attempts,
    verify_totp_token,
    validate_password_strength,
    generate_totp_secret, generate_totp_uri, generate_qr_code,
    verify_token_ip, get_client_ip, encrypt_data, decrypt_data,
)
from app.services.token_service import token_service
from app.schemas.auth import (
    UserCreate, UserResponse, Token, TokenRefresh,
    OTPVerify, ResendOTP,
    PasswordResetRequest, PasswordReset, PasswordChange,
    LoginResponse, OTPVerificationResponse,
    MFASetupRequest, MFASetupResponse, MFAVerifyRequest,
    MFAEnableRequest, MFADisableRequest, MFAStatusResponse,
    MFAVerification, GoogleAuthUrl, GoogleCallback,
    DeleteAccountRequest, PhoneUpdateRequest, PhoneVerifyRequest,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# ─── Normalisation helpers ─────────────────────────────────────────────────────

def normalize_email(email: str) -> str:
    email = email.strip().lower()
    try:
        local, domain = email.split("@", 1)
    except ValueError:
        return email
    if domain in {"gmail.com", "googlemail.com"}:
        local = local.split("+")[0].replace(".", "")
    elif domain in {"outlook.com", "hotmail.com", "live.com"}:
        local = local.split("+")[0]
    elif domain in {"yahoo.com", "ymail.com"}:
        local = local.split("-")[0]
    return f"{local}@{domain}"


# ─── Current user dependency ───────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    db:    AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token, token_type="access")
    if not payload:
        raise exc
    
    jti = payload.get("jti")
    if jti and await token_service.is_token_revoked(jti, redis):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise exc
    
    iat = payload.get("iat")
    if iat:
        iat_ts = int(iat.timestamp()) if isinstance(iat, datetime) else int(iat)
        if await token_service.check_user_tokens_revoked(user_id, redis, iat_ts):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    if payload.get("ip"):
        client_ip = get_client_ip(request)
        if not verify_token_ip(payload, client_ip):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token IP mismatch. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Check if the session still exists in Redis (may have been revoked by admin)
    session_id = payload.get("sid")
    if session_id and user_id:
        session_exists = await redis.exists(f"session:{user_id}:{session_id}")
        if not session_exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise exc
    
    if request and user.signing_key_hash:
        signature = request.headers.get("X-Signature")
        timestamp = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")
        method = request.method
        path = request.url.path
        
        if signature and timestamp and nonce:
            import time
            try:
                ts = int(timestamp)
                if abs(time.time() - ts) > 300:
                    logger.warning("Request signature timestamp too old for user %s", user_id)
            except ValueError:
                pass
            
            if await token_service.is_nonce_used(nonce, redis):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Request replay detected.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            await token_service.store_nonce(nonce, redis, 300)
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.is_locked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is locked.")
    return current_user


# ─── Register ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account. An activation email will be sent. The account status is set to 'pending' until activated.",
)
async def register(user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    from app.utils.validators import validate_email, validate_phone
    
    is_valid, err = validate_email(user_data.email)
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)
    
    normalized = normalize_email(user_data.email)

    is_valid, err = validate_phone(user_data.phone or "")
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)

    # Duplicate check via indexed normalized_email column (exclude deleted accounts)
    dup = await db.execute(select(User).where(
        User.normalized_email == normalized,
        User.deleted_at.is_(None)
    ))
    if dup.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "This email address (or an alias of it) is already registered.")

    is_valid, err = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)

    user = User(
        email=user_data.email,
        normalized_email=normalized,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        company=user_data.company,
        phone=user_data.phone or None,
        account_status="pending",
    )
    db.add(user)
    await db.flush()  # get user.id

    db.add(AuditLog(
        user_id=user.id, user_email=user.email,
        action=AuditAction.USER_REGISTERED, resource_type="user", resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
    ))
    await db.commit()

    logger.info("User registered: %s", user.email)
    return user


# ─── Login (step 1) ───────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=None,
    summary="Login (Step 1: Credentials)",
    description="Validates email/password and sends an OTP code. Returns `mfa_required` flag. If MFA is enabled, an `mfa_session_token` is returned for step 2.",
    responses={
        200: {"description": "Credentials valid, OTP sent"},
        401: {"description": "Invalid credentials"},
        423: {"description": "Account or IP locked"},
    },
)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
    username: str = Form(...),
    password: str = Form(...),
):
    """Validate credentials and send OTP. Returns { email, mfa_required, [mfa_session_token] }."""
    settings = get_settings()
    
    # Get client IP
    client_ip = request.client.host if request.client else None
    
    # Check if IP is locked
    if await is_ip_locked(redis, client_ip):
        raise HTTPException(status.HTTP_423_LOCKED,
                            f"Too many failed attempts. This IP is temporarily locked. Try again later.")

    # Find user (exclude deleted accounts)
    result = await db.execute(select(User).where(
        User.email == username,
        User.deleted_at.is_(None)
    ))
    user   = result.scalar_one_or_none()

    def _bad_creds(reason: str):
        db.add(AuditLog(
            user_id=user.id if user else None,
            user_email=username,
            action=AuditAction.LOGIN,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            status="failure",
            details={"reason": reason, "failed_attempts": getattr(user, "failed_login_attempts", 0)},
        ))

    if not user or not verify_password(password, user.password_hash):
        # Increment IP-based failed attempts
        ip_attempts = await increment_ip_failed_attempts(redis, client_ip)
        
        # Lock IP if too many failed attempts
        if await should_lock_ip_based(redis, client_ip):
            await lock_ip_address(redis, client_ip)
            _bad_creds("ip_locked")
            await db.commit()
            raise HTTPException(status.HTTP_423_LOCKED,
                                "Too many failed attempts. This IP is temporarily locked. Try again later.")
        
        # Still track user-specific attempts for account lockout (but IP lockout is primary)
        if user:
            user.failed_login_attempts += 1
            if should_lock_account(user.failed_login_attempts):
                user.locked_until = calculate_lock_time(5)
                _bad_creds("account_locked")
                await db.commit()
                raise HTTPException(status.HTTP_423_LOCKED,
                                    "Account locked due to multiple failed attempts. Try again in 5 minutes.")
            _bad_creds("invalid_credentials")
        else:
            _bad_creds("invalid_credentials")  # Always use same reason to prevent user enumeration
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.",
                            headers={"WWW-Authenticate": "Bearer"})

    # Check if user account is locked
    if user.is_locked:
        raise HTTPException(status.HTTP_423_LOCKED,
                            f"Account locked until {user.locked_until.strftime('%H:%M:%S')} UTC.")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account has been deactivated. Please contact an administrator for assistance.")

    if user.account_status == "pending":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is pending admin approval. You cannot log in until your account has been approved.")

    # Reset failed attempts on successful credential check
    user.failed_login_attempts = 0
    user.locked_until = None
    await reset_ip_failed_attempts(redis, client_ip)  # Reset IP attempts on success

    # Generate & store OTP
    otp     = generate_otp()
    otp_key = f"otp:{user.email}"
    await redis.setex(otp_key, settings.OTP_EXPIRE_MINUTES * 60, otp)
    await redis.setex(f"login_attempt:{user.email}", settings.OTP_EXPIRE_MINUTES * 60, "pending")

    # Audit
    db.add(AuditLog(
        user_id=user.id, user_email=user.email,
        action=AuditAction.LOGIN,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
        details={"step": "credentials_verified", "otp_sent": True},
    ))
    await db.commit()

    # Send OTP via configured channels
    email_svc = EmailService()
    settings = get_settings()
    otp_channel = settings.OTP_CHANNEL.lower()
    send_email_otp = otp_channel in ("email", "both")
    send_sms_otp = otp_channel in ("sms", "both")

    otp_sent_to = []

    if send_email_otp:
        try:
            await email_svc.send_otp_verification(
                to_email=user.email,
                user_name=user.full_name or user.email,
                code=otp,
                action="verify your login",
            )
            otp_sent_to.append("email")
        except Exception as exc:
            logger.error("Failed to send OTP email to %s: %s", user.email, exc)

    if send_sms_otp and user.phone and user.phone_verified:
        try:
            from app.services.sms_service import sms_service
            await sms_service.send_otp(user.phone, otp)
            otp_sent_to.append("sms")
        except Exception as exc:
            logger.error("Failed to send OTP SMS to %s: %s", user.phone, exc)

    channel_label = " and ".join(otp_sent_to) if otp_sent_to else "your email"

    # If MFA is enabled, issue a short-lived MFA session token instead of full tokens
    if user.mfa_enabled:
        mfa_token = create_mfa_session_token(
            data={"sub": str(user.id), "type": "mfa_session"},
            expires_delta=timedelta(minutes=15),
        )
        return LoginResponse(message=f"OTP sent via {channel_label}. MFA required.", email=user.email,
                             mfa_required=True, mfa_session_token=mfa_token)

    return LoginResponse(message=f"OTP sent to {channel_label}.", email=user.email, mfa_required=False)


# ─── Verify OTP (step 2) ──────────────────────────────────────────────────────

@router.post(
    "/verify-otp",
    response_model=OTPVerificationResponse,
    summary="Verify OTP (Step 2)",
    description="Validates the OTP code sent during login. Returns JWT tokens on success, or an MFA challenge if MFA is enabled.",
)
async def verify_otp(
    body:    OTPVerify,
    request: Request,
    db:      AsyncSession = Depends(get_db),
    redis    = Depends(get_redis),
):
    result = await db.execute(select(User).where(
        User.email == body.email,
        User.deleted_at.is_(None)
    ))
    user   = result.scalar_one_or_none()
    if not user:
        # Don't reveal if email exists or not
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP.")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account has been deactivated. Please contact an administrator for assistance.")

    if user.account_status == "pending":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is pending admin approval. You cannot log in until your account has been approved.")

    if user.is_locked:
        raise HTTPException(status.HTTP_423_LOCKED,
                            f"Account locked until {user.locked_until.strftime('%H:%M:%S')} UTC.")

    stored_otp = await redis.get(f"otp:{body.email}")
    if not stored_otp or not secrets.compare_digest(stored_otp, body.otp):
        user.failed_otp_attempts += 1
        if should_lock_otp_account(user.failed_otp_attempts):
            user.locked_until = calculate_lock_time(5)
            await redis.delete(f"otp:{body.email}", f"login_attempt:{body.email}")
            await db.commit()
            raise HTTPException(status.HTTP_423_LOCKED,
                                "Account locked due to multiple failed OTP attempts. Try again in 5 minutes.")
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OTP.")

    # OTP valid – clean up
    await redis.delete(f"otp:{body.email}")
    user.failed_otp_attempts  = 0
    user.last_login           = datetime.now(timezone.utc)
    user.last_login_ip        = request.client.host if request.client else None

    # If MFA enabled → MFA challenge
    if user.mfa_enabled:
        session_id = str(uuid.uuid4())
        mfa_token = create_mfa_session_token(
            data={"sub": str(user.id), "type": "mfa_session", "sid": session_id},
            expires_delta=timedelta(minutes=10),
        )
        user.mfa_session_created = datetime.now(timezone.utc)
        db.add(AuditLog(user_id=user.id, user_email=user.email,
                        action=AuditAction.MFA_REQUIRED, status="success"))
        await db.commit()
        return OTPVerificationResponse(mfa_required=True, mfa_session_token=mfa_token,
                                       user={"id": str(user.id), "email": user.email,
                                             "full_name": user.full_name, "role": user.role})

    # Issue tokens with IP binding
    client_ip = get_client_ip(request)
    session_id = str(uuid.uuid4())
    access_token, _ = create_access_token({"sub": str(user.id), "sid": session_id}, ip_address=client_ip)
    refresh_token, _ = create_refresh_token({"sub": str(user.id), "sid": session_id}, ip_address=client_ip)

    session_mgr = get_session_manager(redis)
    await session_mgr.create_session(user_id=str(user.id), user_email=user.email,
                                     ip_address=client_ip,
                                     user_agent=request.headers.get("user-agent", ""),
                                     session_id=session_id)

    db.add(AuditLog(user_id=user.id, user_email=user.email, action=AuditAction.LOGIN,
                    ip_address=request.client.host if request.client else None,
                    status="success", details={"step": "otp_verified"}))
    await db.commit()

    return OTPVerificationResponse(
        mfa_required=False,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user={"id": str(user.id), "email": user.email,
              "full_name": user.full_name, "role": user.role},
    )


# ─── Resend OTP ────────────────────────────────────────────────────────────────

@router.post(
    "/resend-otp",
    summary="Resend OTP",
    description="Resends the OTP code if there is an active login window.",
)
async def resend_otp(
    body:    ResendOTP,
    request: Request,
    db:      AsyncSession = Depends(get_db),
    redis    = Depends(get_redis),
):
    settings = get_settings()
    result   = await db.execute(select(User).where(User.email == body.email))
    user     = result.scalar_one_or_none()
    if not user:
        # Don't reveal if email exists or not
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No active login session found.")
    if user.is_locked:
        raise HTTPException(status.HTTP_423_LOCKED, "Account is locked.")

    # Require an active login window
    if not await redis.get(f"login_attempt:{body.email}"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "No active login session. Please log in again.")

    otp = generate_otp()
    await redis.setex(f"otp:{body.email}", settings.OTP_EXPIRE_MINUTES * 60, otp)
    await redis.setex(f"login_attempt:{body.email}", settings.OTP_EXPIRE_MINUTES * 60, "pending")

    email_svc = EmailService()
    try:
        await email_svc.send_otp_verification(
            to_email=user.email, user_name=user.full_name or user.email,
            code=otp, action="verify your login",
        )
    except Exception as exc:
        logger.error("Failed to resend OTP to %s: %s", user.email, exc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to send OTP email.")

    db.add(AuditLog(user_id=user.id, user_email=user.email, action=AuditAction.OTP_SENT,
                    ip_address=request.client.host if request.client else None, status="success"))
    await db.commit()
    return {"message": "OTP resent.", "email": user.email}


# ─── Token refresh ────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Rotates access and refresh tokens using a valid refresh token.",
)
async def refresh_token(body: TokenRefresh, request: Request, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)):
    payload = verify_token(body.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token.")

    result = await db.execute(select(User).where(User.id == payload.get("sub")))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token.")
    
    iat = payload.get("iat")
    if iat:
        iat_ts = int(iat.timestamp()) if isinstance(iat, datetime) else int(iat)
        if await token_service.check_user_tokens_revoked(str(user.id), redis, iat_ts):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your account has been deactivated. Please contact an administrator for assistance.")

    if user.account_status == "pending":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your account is pending admin approval. You cannot refresh your session until your account has been approved.")

    if user.is_locked:
        raise HTTPException(status.HTTP_423_LOCKED,
                            f"Account locked until {user.locked_until.strftime('%H:%M:%S')} UTC.")

    settings = get_settings()
    client_ip = get_client_ip(request)
    session_id = payload.get("sid")
    
    # Check if the session still exists (may have been revoked by admin)
    if session_id:
        session_exists = await redis.exists(f"session:{payload.get('sub')}:{session_id}")
        if not session_exists:
            await token_service.revoke_token(payload.get("jti"), redis, ttl_seconds=86400)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    token_payload = {"sub": str(user.id)}
    if session_id:
        token_payload["sid"] = session_id
    access_token, _ = create_access_token(token_payload, ip_address=client_ip)
    refresh_token, _ = create_refresh_token(token_payload, ip_address=client_ip)
    
    import hashlib
    response_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse.model_validate(user).model_dump(),
    }
    
    if body.signing_key:
        user.signing_key_hash = hashlib.sha256(body.signing_key.encode()).hexdigest()
        await db.commit()
    
    return response_data


# ─── Logout ───────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    summary="Logout",
    description="Destroys the current session and revokes the access token.",
)
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis),
):
    payload = verify_token(token)
    jti = payload.get("jti") if payload else None
    session_id = payload.get("sid") if payload else None
    
    if jti:
        await token_service.revoke_token(jti, redis, ttl_seconds=3600)
    
    if session_id:
        session_mgr = get_session_manager(redis)
        await session_mgr.destroy_session(str(current_user.id), session_id)
    
    async with get_db_session() as db:
        db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                        action=AuditAction.LOGOUT,
                        ip_address=get_client_ip(request),
                        status="success"))
        await db.commit()
    return {"message": "Logged out successfully."}


# ─── Forgot / reset password ──────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Sends a password reset email if the address is registered. Always returns 200 to prevent email enumeration.",
)
async def forgot_password(
    body:  PasswordResetRequest,
    db:    AsyncSession = Depends(get_db),
    redis  = Depends(get_redis),
):
    result = await db.execute(select(User).where(
        User.email == body.email,
        User.deleted_at.is_(None)
    ))
    user   = result.scalar_one_or_none()
    # Always return 200 to prevent email enumeration
    if user:
        reset_token = create_password_reset_token(
            {"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(hours=1),
        )
        await redis.setex(f"password_reset:{user.id}", 3600, reset_token)
        settings = get_settings()
        await send_password_reset_email(
            user.email,
            reset_token,
        )
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post(
    "/reset-password",
    summary="Reset password",
    description="Consumes a reset token and sets a new password. The old password is saved to history to prevent reuse.",
)
async def reset_password(
    body:  PasswordReset,
    db:    AsyncSession = Depends(get_db),
    redis  = Depends(get_redis),
):
    payload = verify_token(body.token, token_type="password_reset")
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token.")

    user_id = payload.get("sub")
    stored  = await redis.get(f"password_reset:{user_id}")
    
    # Debug logging
    logger.info(f"Token verification successful: user_id={user_id}")
    logger.info(f"Stored token: {stored}")
    logger.info(f"Provided token: {body.token}")
    logger.info(f"Token match: {stored == body.token}")
    
    if not stored:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset token already used or expired.")
    
    # Verify that stored token matches the provided token (prevent token reuse)
    if stored != body.token:
        logger.error(f"Token mismatch: stored={stored}, provided={body.token}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reset token.")

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")

    is_valid, err = validate_password_strength(body.new_password)
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)

    new_hash = get_password_hash(body.new_password)
    is_reused, reuse_err = await check_password_reuse(db, user, new_hash)
    if is_reused:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reuse_err)

    await save_password_to_history(db, user, user.password_hash)
    user.password_hash      = new_hash
    user.password_changed_at = datetime.now(timezone.utc)
    await redis.delete(f"password_reset:{user_id}")
    await db.commit()
    await token_service.revoke_all_user_tokens(str(user.id), redis)
    await send_password_change_notification(user.email)
    return {"message": "Password reset successfully."}


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile information, including avatar URL if set.",
)
async def get_me(current_user: User = Depends(get_current_active_user), request: Request = None):
    settings = get_settings()
    # Add avatar URL to user response if available
    user_data = {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "company": current_user.company,
        "phone": current_user.phone,
        "phone_verified": current_user.phone_verified,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "email_verified": current_user.email_verified,
        "mfa_enabled": current_user.mfa_enabled,
        "last_login": current_user.last_login,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "avatar_url": None,
        "avatar_updated_at": None
    }
    
    # Add avatar URL if user has one - use proxy endpoint to avoid CORS issues
    if current_user.avatar_object_name and current_user.avatar_bucket:
        try:
            # Use configured external URL if available, otherwise try X-Forwarded-Host
            if settings.API_EXTERNAL_URL:
                base_url = settings.API_EXTERNAL_URL.rstrip('/')
            else:
                proto = request.headers.get("X-Forwarded-Proto", "http")
                forward_host = request.headers.get("X-Forwarded-Host")
                if forward_host:
                    base_url = f"{proto}://{forward_host}"
                else:
                    # Fallback: use Host header from request (this is the server's host, not client's)
                    host_header = request.headers.get("host", "")
                    base_url = f"{proto}://{host_header}"
            
            user_data["avatar_url"] = f"{base_url}/api/v1/auth/avatars/{current_user.id}"
            user_data["avatar_updated_at"] = current_user.updated_at.isoformat() if current_user.updated_at else None
        except Exception:
            pass
    
    return user_data


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    company: Optional[str] = None


@router.put(
    "/me",
    summary="Update profile",
    description="Updates the current user's display name and/or company.",
)
async def update_me(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name.strip() or None
    if body.company is not None:
        current_user.company = body.company.strip() or None
    await db.commit()
    return {"message": "Profile updated successfully"}


@router.post(
    "/me/avatar",
    summary="Upload avatar",
    description="Uploads a profile picture (PNG, JPEG, or WEBP, max 10MB). Replaces any existing avatar.",
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    # Tight allowlist for avatars
    allowed = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    if file.content_type not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid image type. Use PNG, JPEG, or WEBP.")

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file.")

    # Avatar size limit: 10MB
    max_avatar_size = 10 * 1024 * 1024  # 10MB in bytes
    if len(content) > max_avatar_size:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File too large. Maximum size is 10MB.")

    # Delete previous avatar if it exists
    if current_user.avatar_object_name and current_user.avatar_bucket:
        try:
            await storage_service.delete_object(
                current_user.avatar_object_name,
                bucket=current_user.avatar_bucket
            )
        except Exception:
            # Ignore deletion errors, continue with upload
            pass

    # Store under user folder; keep private and serve via presigned URL
    # Always use PNG since cropper outputs PNG format
    safe_filename = "avatar.png"
    safe_content_type = "image/png"
    upload = await storage_service.upload_bytes(
        data=content,
        filename=safe_filename,
        content_type=safe_content_type,
        folder=f"avatars/{current_user.id}",
        is_public=False,
        bucket=settings.MINIO_BUCKET_AVATARS,
        metadata={"user_id": str(current_user.id), "kind": "avatar"},
    )

    current_user.avatar_object_name = upload["object_name"]
    current_user.avatar_bucket = upload["bucket"]
    current_user.avatar_content_type = safe_content_type
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Avatar uploaded", "avatar_url": upload["url"]}


@router.get(
    "/me/avatar",
    summary="Get avatar URL",
    description="Returns a proxied URL to the user's avatar image.",
)
async def get_avatar_url(
    current_user: User = Depends(get_current_active_user),
    request: Request = None,
):
    settings = get_settings()
    if not current_user.avatar_object_name or not current_user.avatar_bucket:
        return {"avatar_url": None}

    # Use proxy endpoint to avoid CORS issues
    if settings.API_EXTERNAL_URL:
        base_url = settings.API_EXTERNAL_URL.rstrip('/')
    else:
        proto = request.headers.get("X-Forwarded-Proto", "http")
        forward_host = request.headers.get("X-Forwarded-Host")
        if forward_host:
            base_url = f"{proto}://{forward_host}"
        else:
            host_header = request.headers.get("host", "")
            base_url = f"{proto}://{host_header}"
    
    url = f"{base_url}/api/v1/auth/avatars/{current_user.id}"
    return {"avatar_url": url}


@router.get(
    "/avatars/{user_id}",
    summary="Get avatar image",
    description="Proxy endpoint that serves the avatar image bytes directly. Used as `<img src>` to avoid CORS issues with MinIO.",
    responses={
        200: {"description": "Avatar image"},
        404: {"description": "Avatar not found"},
    },
)
async def get_avatar_proxy(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Proxy avatar requests to avoid CORS issues with MinIO presigned URLs."""
    import uuid
    settings = get_settings()
    
    # Validate UUID format
    try:
        uuid.UUID(user_id)
    except (ValueError, AttributeError):
        logger.warning(f"Invalid UUID format requested: {user_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avatar not found")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.avatar_object_name or not user.avatar_bucket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avatar not found")
    
    try:
        data = await storage_service.get_file_bytes(
            user.avatar_object_name,
            bucket=user.avatar_bucket,
        )
        
        content_type = user.avatar_content_type or "image/png"
        
        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'inline; filename="avatar.png"',
            }
        )
    except Exception as e:
        logger.error(f"Failed to fetch avatar for user {user_id}: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to load avatar")


@router.put(
    "/me/password",
    summary="Change password",
    description="Changes the current user's password. Requires current password, and new password must not be a recent previous password.",
)
async def change_password(
    request:      Request,
    current_user: User = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
    redis         = Depends(get_redis),
):
    import json
    try:
        raw  = await request.body()
        data = json.loads(raw)
        current_pwd = data.get("current_password", "")
        new_pwd     = data.get("new_password", "")
        if not current_pwd or not new_pwd:
            raise ValueError("missing fields")
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Body must be JSON with current_password and new_password.")

    if not verify_password(current_pwd, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")

    is_valid, err = validate_password_strength(new_pwd)
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)

    new_hash = get_password_hash(new_pwd)
    is_reused, reuse_err = await check_password_reuse(db, current_user, new_hash)
    if is_reused:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reuse_err)

    await save_password_to_history(db, current_user, current_user.password_hash)
    current_user.password_hash       = new_hash
    current_user.password_changed_at  = datetime.now(timezone.utc)

    db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                    action=AuditAction.PASSWORD_CHANGED,
                    ip_address=request.client.host if request.client else None, status="success"))
    await db.commit()
    await token_service.revoke_all_user_tokens(str(current_user.id), redis)
    await send_password_change_notification(current_user.email,
                                            request.client.host if request.client else None)
    return {"message": "Password changed successfully."}


# ─── Phone Management ─────────────────────────────────────────────────────────

@router.put(
    "/me/phone",
    summary="Update phone number",
    description="Updates the user's phone number and sends a verification code via SMS.",
)
async def update_phone(
    body: PhoneUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    redis = Depends(get_redis),
):
    from app.utils.validators import validate_phone
    from app.services.sms_service import sms_service

    is_valid, err = validate_phone(body.phone)
    if not is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)

    # Handle phone removal (empty string)
    if not body.phone:
        current_user.phone = None
        current_user.phone_verified = False
        async with get_db_session() as db:
            await db.commit()
        return {"message": "Phone number removed"}

    current_user.phone = body.phone
    current_user.phone_verified = False
    async with get_db_session() as db:
        await db.commit()

    code = generate_otp()
    await redis.setex(f"phone_otp:{current_user.id}", 600, code)

    try:
        await sms_service.send_otp(current_user.phone, code)
    except Exception as exc:
        logger.error("Failed to send phone verification SMS to %s: %s", current_user.phone, exc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to send verification SMS")

    return {"message": "Phone verification code sent via SMS"}


@router.post(
    "/me/phone/verify",
    summary="Verify phone number",
    description="Verifies the phone number using the OTP code sent via SMS.",
)
async def verify_phone(
    body: PhoneVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    redis = Depends(get_redis),
):
    stored_code = await redis.get(f"phone_otp:{current_user.id}")
    if not stored_code or not secrets.compare_digest(
        stored_code.decode() if isinstance(stored_code, bytes) else stored_code,
        body.code,
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification code")

    await redis.delete(f"phone_otp:{current_user.id}")
    current_user.phone_verified = True
    async with get_db_session() as db:
        await db.commit()

    return {"message": "Phone verified successfully"}


@router.post(
    "/me/delete",
    summary="Delete account",
    description="Soft-deletes the current user's account. Requires password confirmation. Removes all associated data (sessions, analysis results, notifications, avatar).",
)
async def delete_account(
    delete_request: DeleteAccountRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    if not verify_password(delete_request.password, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect password.")

    # Soft delete
    # Delete user's avatar if it exists
    if current_user.avatar_object_name and current_user.avatar_bucket:
        try:
            await storage_service.delete_object(
                current_user.avatar_object_name,
                bucket=current_user.avatar_bucket
            )
        except Exception:
            # Ignore deletion errors
            pass

    db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                    action=AuditAction.USER_DELETED, resource_type="user",
                    resource_id=str(current_user.id), status="success",
                    details={"reason": "self-requested"},
                    ip_address=request.client.host if request.client else None))
    current_user.deleted_at   = datetime.now(timezone.utc)
    current_user.is_active    = False
    current_user.email        = f"deleted_{current_user.id}@deleted.phishcatcher"
    current_user.password_hash = "deleted"
    current_user.gmail_credentials = None
    current_user.mfa_secret   = None
    current_user.mfa_backup_codes = None
    current_user.phone = None
    current_user.phone_verified = False
    current_user.avatar_object_name = None
    current_user.avatar_bucket = None
    current_user.avatar_content_type = None
    
    # Clear all sessions for this user (Redis session manager has one session per user)
    session_mgr = get_session_manager(redis)
    await session_mgr.destroy_session(str(current_user.id))
    await token_service.revoke_all_user_tokens(str(current_user.id), redis)
    
    from app.database import get_mongodb_database
    mongodb = get_mongodb_database()
    user_id_str = str(current_user.id)
    
    await mongodb.analysis_results.delete_many({"user_id": user_id_str})
    await mongodb.gmail_analysis_queue.delete_many({"user_id": user_id_str})
    await mongodb.notifications.delete_many({"user_id": user_id_str})
    
    await db.commit()
    return {"message": "Account deleted successfully."}


# ─── Google OAuth ─────────────────────────────────────────────────────────────

@router.get(
    "/google/url",
    response_model=GoogleAuthUrl,
    summary="Get Google OAuth URL",
    description="Returns the Google OAuth authorization URL for sign-in. Returns 503 if Google OAuth is not configured.",
)
async def google_auth_url():
    try:
        result = google_oauth_service.get_auth_url()
        return GoogleAuthUrl(auth_url=result["auth_url"], state=result["state"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.post(
    "/google/callback",
    summary="Google OAuth callback",
    description="Exchanges an OAuth authorization code for tokens. Creates a pending account for new users (requires activation).",
)
async def google_callback(
    body:  GoogleCallback,
    request: Request,
    db:    AsyncSession = Depends(get_db),
    redis  = Depends(get_redis),
):
    token_data = await google_oauth_service.handle_oauth_callback(body.code, body.state)
    if not token_data.get("success"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            token_data.get("error", "Google authentication failed."))

    result = await db.execute(select(User).where(
        User.email == token_data["email"],
        User.deleted_at.is_(None)
    ))
    user   = result.scalar_one_or_none()

    if not user:
        # New user – create pending account and require activation
        user = User(
            email=token_data["email"],
            normalized_email=normalize_email(token_data["email"]),
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            full_name=token_data.get("name"),
            email_verified=True,
            account_status="pending",
        )
        db.add(user)
        await db.flush()

        token = await activation_service.generate_activation_token(str(user.id))
        code  = await activation_service.generate_activation_code(str(user.id))
        await activation_service.send_activation_email(
            user_email=user.email,
            user_name=user.full_name or user.email.split("@")[0],
            user_id=str(user.id),
            activation_token=token,
            activation_code=code,
        )
        await db.commit()
        return {
            "activation_required": True,
            "email":     user.email,
            "full_name": user.full_name,
            "message":   "Please check your email for activation instructions.",
        }

    if user.account_status == "pending":
        # Existing but not activated – resend activation
        token = await activation_service.generate_activation_token(str(user.id))
        code  = await activation_service.generate_activation_code(str(user.id))
        await activation_service.send_activation_email(
            user_email=user.email,
            user_name=user.full_name or user.email.split("@")[0],
            user_id=str(user.id),
            activation_token=token,
            activation_code=code,
        )
        return {
            "activation_required": True,
            "email":     user.email,
            "full_name": user.full_name,
            "message":   "Your account is pending activation. Check your email.",
        }

    if user.mfa_enabled:
        mfa_token = create_mfa_session_token(
            data={"sub": str(user.id), "type": "mfa_session"},
            expires_delta=timedelta(minutes=10),
        )
        return {"mfa_required": True, "mfa_session_token": mfa_token,
                "user": {"id": str(user.id), "email": user.email,
                         "full_name": user.full_name, "role": user.role}}

    # Active user without MFA → issue tokens
    client_ip = get_client_ip(request)
    session_id = str(uuid.uuid4())
    access_token, _ = create_access_token({"sub": str(user.id), "sid": session_id}, ip_address=client_ip)
    refresh_token, _ = create_refresh_token({"sub": str(user.id), "sid": session_id}, ip_address=client_ip)
    session_mgr   = get_session_manager(redis)
    await session_mgr.create_session(user_id=str(user.id), user_email=user.email,
                                     ip_address=client_ip or "oauth", user_agent=request.headers.get("user-agent", "Google OAuth"),
                                     session_id=session_id)
    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user": {"id": str(user.id), "email": user.email,
                 "full_name": user.full_name, "role": user.role},
    }


# ─── MFA ─────────────────────────────────────────────────────────────────────

@router.get(
    "/mfa/status",
    response_model=MFAStatusResponse,
    summary="Get MFA status",
    description="Returns whether MFA is enabled, setup is completed, and backup codes exist.",
)
async def mfa_status(current_user: User = Depends(get_current_active_user)):
    return MFAStatusResponse(
        enabled=current_user.mfa_enabled,
        setup_completed=bool(current_user.mfa_secret),
        has_backup_codes=bool(current_user.mfa_backup_codes),
    )


@router.post(
    "/mfa/setup",
    response_model=MFASetupResponse,
    summary="Setup MFA",
    description="Generates a TOTP secret, QR code, and backup codes. Returns an MFA session token for verification.",
)
async def mfa_setup(
    request:      Request,
    _:            MFASetupRequest,
    current_user: User = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
    redis         = Depends(get_redis),
):
    allowed, msg = await check_mfa_rate_limit_async(redis, str(current_user.id), "setup", max_attempts=3, window_minutes=30)
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, msg)

    secret  = generate_totp_secret()
    uri     = generate_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)
    backup_codes = [generate_otp(8) for _ in range(12)]

    mfa_session = create_mfa_session_token(
        data={"sub": str(current_user.id), "type": "mfa_setup"},
        expires_delta=timedelta(minutes=15),
    )

    current_user.mfa_secret      = encrypt_mfa_secret(secret)
    current_user.mfa_backup_codes = encrypt_backup_codes(backup_codes)
    db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                    action=AuditAction.MFA_SETUP_INITIATED, status="success"))
    await db.commit()

    return MFASetupResponse(
        secret=secret, qr_code=qr_code, backup_codes=backup_codes,
        mfa_session_token=mfa_session,
        instructions=(
            "1. Scan the QR code with your authenticator app.\n"
            "2. Enter the 6-digit code below to enable MFA.\n"
            "3. Save your backup codes in a secure place."
        ),
    )


@router.post(
    "/mfa/verify",
    summary="Verify MFA code",
    description="Dual-purpose: verifies TOTP during login flow (returns JWT tokens) or during setup flow (enables MFA). Requires an MFA session token.",
)
async def mfa_verify(
    request: Request,
    body:    MFAVerification,
    db:      AsyncSession = Depends(get_db),
    redis    = Depends(get_redis),
):
    """
    Dual-purpose:
    - Called during login flow (with mfa_session_token issued at login/OTP).
    - Called during MFA setup (with token from /mfa/setup).
    Returns tokens on success (login) or {"message": "MFA enabled"} (setup).
    """
    payload = verify_token(body.mfa_session_token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired MFA session.")

    user_id = payload.get("sub")
    flow    = payload.get("type", "mfa_session")  # "mfa_session" | "mfa_setup"

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user or not user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA not configured for this account.")
    
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account has been deactivated. Please contact an administrator for assistance.")
    
    if user.is_locked:
        raise HTTPException(status.HTTP_423_LOCKED,
                            f"Account locked until {user.locked_until.strftime('%H:%M:%S')} UTC.")

    secret   = decrypt_mfa_secret(user.mfa_secret)
    is_valid = verify_totp_token(secret, body.code)
    if not is_valid:
        allowed, msg = await check_mfa_rate_limit_async(redis, user_id, "verify", max_attempts=5, window_minutes=15)
        db.add(AuditLog(user_id=user.id, user_email=user.email,
                        action=AuditAction.MFA_FAILURE, status="failure"))
        await db.commit()
        if not allowed:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, msg)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid MFA code.")

    # --- Setup flow ---
    if flow == "mfa_setup":
        user.mfa_enabled = True
        await clear_mfa_rate_limit_async(redis, str(user.id), "setup")
        db.add(AuditLog(user_id=user.id, user_email=user.email,
                        action=AuditAction.MFA_ENABLED, status="success"))
        await db.commit()
        return {"message": "MFA enabled successfully."}

    # --- Login flow ---
    client_ip = get_client_ip(request)
    session_id = mfa_payload.get("sid", str(uuid.uuid4()))
    access_token, _ = create_access_token({"sub": str(user.id), "sid": session_id}, ip_address=client_ip)
    refresh_token, _ = create_refresh_token({"sub": str(user.id), "sid": session_id}, ip_address=client_ip)
    session_mgr   = get_session_manager(redis)
    await session_mgr.create_session(user_id=str(user.id), user_email=user.email,
                                     ip_address=client_ip,
                                     user_agent=request.headers.get("user-agent", ""),
                                     session_id=session_id)
    db.add(AuditLog(user_id=user.id, user_email=user.email,
                    action=AuditAction.MFA_SUCCESS, status="success"))
    await db.commit()
    return OTPVerificationResponse(
        mfa_required=False,
        access_token=access_token, refresh_token=refresh_token, token_type="bearer",
        user={"id": str(user.id), "email": user.email,
              "full_name": user.full_name, "role": user.role},
    )


@router.post(
    "/mfa/enable",
    summary="Enable MFA",
    description="Enables MFA on the account. Requires a valid TOTP verification code.",
)
async def mfa_enable(
    request:      Request,
    body:         MFAEnableRequest,
    current_user: User = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
):
    if not current_user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA setup not completed.")
    secret = decrypt_mfa_secret(current_user.mfa_secret)
    if not verify_totp_token(secret, body.token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification code.")
    current_user.mfa_enabled = True
    db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                    action=AuditAction.MFA_ENABLED, status="success"))
    await db.commit()
    return {"message": "MFA enabled."}


@router.post(
    "/mfa/disable",
    summary="Disable MFA",
    description="Disables MFA. Requires a valid TOTP code. Non-OAuth users must also provide their password.",
)
async def mfa_disable(
    request:      Request,
    body:         MFADisableRequest,
    current_user: User = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
):
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA is not currently enabled.")

    # Verify TOTP token always required
    secret = decrypt_mfa_secret(current_user.mfa_secret)
    if not verify_totp_token(secret, body.token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Invalid authenticator code. Enter the current 6-digit code from your app.")

    # Password required only for non-OAuth users
    is_oauth = bool(current_user.gmail_credentials or current_user.gmail_email)
    if not is_oauth and not verify_password(body.password, current_user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid password.")

    current_user.mfa_enabled  = False
    current_user.mfa_secret   = None
    db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                    action=AuditAction.MFA_DISABLED, status="success"))
    await db.commit()
    return {"message": "MFA disabled."}


@router.post(
    "/mfa/verify-backup-code",
    summary="Verify MFA backup code",
    description="Uses a one-time backup code for MFA authentication. Returns JWT tokens on success. The code is marked as used and cannot be reused.",
)
async def verify_backup_code(
    request:      Request,
    body:         dict,
    current_user: User = Depends(get_current_active_user),
    db:           AsyncSession = Depends(get_db),
    redis         = Depends(get_redis),
):
    code = body.get("backup_code", "")
    allowed, msg = await check_mfa_rate_limit_async(redis, str(current_user.id), "backup_code",
                                        max_attempts=3, window_minutes=60)
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, msg)

    if not current_user.mfa_enabled or not current_user.mfa_backup_codes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "MFA / backup codes not configured.")

    codes      = decrypt_backup_codes(current_user.mfa_backup_codes)
    normalized = code.replace(" ", "").upper()
    if normalized not in codes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid backup code.")
    used = current_user.mfa_backup_codes_used or []
    if normalized in used:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Backup code already used.")

    # Mark used
    codes.remove(normalized)
    current_user.mfa_backup_codes      = encrypt_backup_codes(codes)
    current_user.mfa_backup_codes_used = [*used, normalized]
    await clear_mfa_rate_limit_async(redis, str(current_user.id), "backup_code")

    client_ip = get_client_ip(request)
    session_id = str(uuid.uuid4())
    access_token, _ = create_access_token({"sub": str(current_user.id), "sid": session_id}, ip_address=client_ip)
    refresh_token, _ = create_refresh_token({"sub": str(current_user.id), "sid": session_id}, ip_address=client_ip)
    session_mgr   = get_session_manager(redis)
    await session_mgr.create_session(user_id=str(current_user.id), user_email=current_user.email,
                                     ip_address=client_ip,
                                     user_agent=request.headers.get("user-agent", ""),
                                     session_id=session_id)

    db.add(AuditLog(user_id=current_user.id, user_email=current_user.email,
                    action=AuditAction.MFA_BACKUP_CODE_USED, status="success"))
    await db.commit()
    return {
        "success":       True,
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "user": {"id": str(current_user.id), "email": current_user.email,
                 "full_name": current_user.full_name, "role": current_user.role},
        "remaining_backup_codes": len(codes),
    }