"""
Session Management Routes

Endpoints for session status, validation, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import redis.asyncio as redis
import logging

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.core.session_manager import get_session_manager
from app.models.audit_log import AuditLog, AuditAction
from app.database import get_redis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def get_session_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Get current session status and information."""
    session_manager = get_session_manager(redis_client)
    
    session_info = await session_manager.get_session_info(str(current_user.id))
    
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
            "created_at": session_info["created_at"],
            "last_activity": session_info["last_activity"],
            "expires_at": session_info["expires_at"],
            "inactivity_expires_at": session_info["inactivity_expires_at"],
            "remaining_inactivity_minutes": session_info["remaining_inactivity_minutes"],
            "remaining_session_minutes": session_info["remaining_session_minutes"],
            "last_activity_minutes_ago": session_info["last_activity_minutes_ago"]
        },
        "limits": {
            "max_session_hours": 2,
            "inactivity_minutes": 20
        }
    }


@router.post("/extend")
async def extend_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Extend session duration for active users."""
    session_manager = get_session_manager(redis_client)
    
    # Check if session is valid
    is_valid, reason = await session_manager.is_session_valid(str(current_user.id))
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Cannot extend session: {reason}"
        )
    
    # Extend session
    extended = await session_manager.extend_session(str(current_user.id))
    
    if not extended:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend session"
        )
    
    # Log session extension
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
    
    # Get updated session info
    session_info = await session_manager.get_session_info(str(current_user.id))
    
    return {
        "session_extended": True,
        "session": {
            "expires_at": session_info["expires_at"],
            "inactivity_expires_at": session_info["inactivity_expires_at"],
            "remaining_inactivity_minutes": session_info["remaining_inactivity_minutes"],
            "remaining_session_minutes": session_info["remaining_session_minutes"]
        }
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Logout user and destroy session."""
    session_manager = get_session_manager(redis_client)
    
    # Destroy session
    session_destroyed = await session_manager.destroy_session(str(current_user.id))
    
    # Log logout
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.LOGOUT,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success",
        details={"session_destroyed": session_destroyed}
    )
    db.add(audit_log)
    await db.commit()
    
    return {
        "logout_success": True,
        "session_destroyed": session_destroyed,
        "message": "Successfully logged out"
    }


@router.get("/validate")
async def validate_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Validate session and return status."""
    session_manager = get_session_manager(redis_client)
    
    is_valid, reason = await session_manager.is_session_valid(str(current_user.id))
    
    if not is_valid:
        return {
            "valid": False,
            "reason": reason,
            "code": "SESSION_INVALID"
        }
    
    session_info = await session_manager.get_session_info(str(current_user.id))
    
    return {
        "valid": True,
        "session": {
            "remaining_inactivity_minutes": session_info["remaining_inactivity_minutes"],
            "remaining_session_minutes": session_info["remaining_session_minutes"],
            "last_activity_minutes_ago": session_info["last_activity_minutes_ago"]
        }
    }


@router.post("/cleanup")
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
