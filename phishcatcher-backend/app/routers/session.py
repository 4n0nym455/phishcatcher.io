"""
Session Management Routes

Endpoints for session status, validation, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import redis.asyncio as redis
import logging

from app.database import get_db, get_redis
from app.models.user import User
from app.routers.auth import get_current_user
from app.core.session_manager import get_session_manager
from app.models.audit_log import AuditLog, AuditAction
from app.config import get_settings
from app.services.security import verify_token
from fastapi.security import OAuth2PasswordBearer

settings = get_settings()

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Session"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def _get_session_id(request: Request, token: Optional[str] = None) -> Optional[str]:
    """Extract session_id from request state (set by middleware) or token."""
    if hasattr(request.state, "session_id"):
        return request.state.session_id
    if token:
        payload = verify_token(token)
        if payload:
            return payload.get("sid")
    return None


@router.get(
    "/status",
    summary="Get session status",
    description="Returns the current session's details including expiry times, remaining minutes, and session limits.",
)
async def get_session_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get current session status and information."""
    session_manager = get_session_manager(redis_client)
    session_id = _get_session_id(request)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session ID found"
        )
    
    session_info = await session_manager.get_session_info(str(current_user.id), session_id)
    
    if not session_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session found"
        )
    
    return {
        "session_active": True,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role
        },
        "session": {
            "session_id": session_info.get("session_id"),
            "created_at": session_info.get("created_at"),
            "login_time": session_info.get("login_time"),
            "ip_address": session_info.get("ip_address"),
            "user_agent": session_info.get("user_agent"),
            "remaining_session_minutes": session_info.get("remaining_session_minutes", 0),
            "session_ttl_seconds": session_info.get("session_ttl_seconds", 0),
            "session_age_minutes": session_info.get("session_age_minutes", 0),
            "max_duration_minutes": session_info.get("max_duration_minutes", 0)
        },
        "limits": {
            "max_session_hours": settings.SESSION_MAX_DURATION_MINUTES // 60,
            "inactivity_minutes": settings.SESSION_INACTIVITY_MINUTES
        }
    }


@router.post(
    "/extend",
    summary="Extend session",
    description="Extends the current session duration. Fails if the session is already expired or invalid.",
)
async def extend_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Extend session duration for active users."""
    session_manager = get_session_manager(redis_client)
    session_id = _get_session_id(request)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session ID found"
        )
    
    is_valid, reason = await session_manager.is_session_valid(str(current_user.id), session_id)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Cannot extend session: {reason}"
        )
    
    extended = await session_manager.extend_session(str(current_user.id), session_id)
    
    if not extended:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend session"
        )
    
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action="session_extended",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    session_info = await session_manager.get_session_info(str(current_user.id), session_id)
    
    return {
        "session_extended": True,
        "session": {
            "remaining_session_minutes": session_info.get("remaining_session_minutes", 0),
            "session_ttl_seconds": session_info.get("session_ttl_seconds", 0),
            "session_age_minutes": session_info.get("session_age_minutes", 0)
        }
    }


@router.post(
    "/logout",
    summary="Logout via session",
    description="Destroys the current session only. Other device sessions remain active.",
)
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Logout user and destroy only the current session."""
    from app.services.token_service import token_service
    
    payload = verify_token(token)
    jti = payload.get("jti") if payload else None
    session_id = payload.get("sid") if payload else None
    
    if jti:
        await token_service.revoke_token(jti, redis_client, ttl_seconds=3600)
    
    session_manager = get_session_manager(redis_client)
    
    if session_id:
        session_destroyed = await session_manager.destroy_session(str(current_user.id), session_id)
    else:
        session_destroyed = False
    
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.LOGOUT,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
        details={"session_destroyed": session_destroyed, "session_id": session_id}
    )
    db.add(audit_log)
    await db.commit()
    
    return {
        "logout_success": True,
        "session_destroyed": session_destroyed,
        "message": "Successfully logged out"
    }


@router.get(
    "/validate",
    summary="Validate session",
    description="Checks if the current session is still valid and returns remaining time info.",
)
async def validate_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Validate session and return status."""
    session_manager = get_session_manager(redis_client)
    session_id = _get_session_id(request)

    if not session_id:
        return {
            "valid": False,
            "reason": "No session ID found",
            "code": "SESSION_INVALID"
        }
    
    is_valid, reason = await session_manager.is_session_valid(str(current_user.id), session_id)
    
    if not is_valid:
        return {
            "valid": False,
            "reason": reason,
            "code": "SESSION_INVALID"
        }
    
    session_info = await session_manager.get_session_info(str(current_user.id), session_id)
    
    return {
        "valid": True,
        "session": {
            "remaining_session_minutes": session_info.get("remaining_session_minutes", 0),
            "session_age_minutes": session_info.get("session_age_minutes", 0)
        }
    }


@router.get(
    "/list",
    summary="List all user sessions (admin only)",
    description="Returns all active sessions for all users. Admin access required.",
)
async def list_all_sessions(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """List all active sessions (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    payload = verify_token(token, token_type="access")
    current_session_id = payload.get("sid") if payload else None
    
    session_manager = get_session_manager(redis_client)
    sessions = await session_manager.get_all_sessions()
    
    for s in sessions:
        s["is_current"] = s["session_id"] == current_session_id
    
    return {
        "sessions": sessions,
        "total": len(sessions)
    }


@router.post(
    "/revoke/{user_id}/{session_id}",
    summary="Revoke a specific session (admin only)",
    description="Revokes a specific session for a user. Admin access required.",
)
async def revoke_session(
    user_id: str,
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Revoke a specific session (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    session_manager = get_session_manager(redis_client)
    destroyed = await session_manager.destroy_session(user_id, session_id)
    
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.LOGOUT,
        ip_address=request.client.host if request.client else None,
        status="success",
        details={"action": "admin_revoke_session", "target_user_id": user_id, "target_session_id": session_id}
    )
    db.add(audit_log)
    await db.commit()
    
    return {
        "session_revoked": destroyed,
        "message": "Session revoked" if destroyed else "Session not found"
    }


@router.post(
    "/cleanup",
    summary="Cleanup expired sessions",
    description="Removes all expired sessions from Redis. Admin access required.",
)
async def cleanup_expired_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Cleanup expired sessions (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    session_manager = get_session_manager(redis_client)
    cleaned_count = await session_manager.cleanup_expired_sessions()
    
    return {
        "cleanup_completed": True,
        "cleaned_sessions": cleaned_count
    }
