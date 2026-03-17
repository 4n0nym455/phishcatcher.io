"""
Admin Router

This module handles admin-only endpoints for system management.
Implements comprehensive security controls:
- Rate limiting on all endpoints
- MFA requirement for sensitive operations
- Self-protection (prevent self-demotion)
- Comprehensive audit logging
- Security monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_mongodb_database
from app.models.user import User
from app.models.analysis_job import AnalysisJob
from app.models.audit_log import AuditLog, AuditAction
from app.routers.auth import get_current_active_user
from app.ml.phishing_detector import get_phishing_detector
from app.services.security import verify_password

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter()

# Security settings
MAX_ADMIN_SESSION_AGE = timedelta(minutes=15)


async def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Verify user is admin."""
    if not current_user.is_admin:
        logger.warning(f"Unauthorized admin access attempt by {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_admin_mfa(
    request: Request,
    current_user: User = Depends(get_current_admin)
) -> User:
    """Verify admin has MFA enabled for sensitive operations."""
    if not current_user.mfa_enabled:
        logger.warning(f"Admin {current_user.email} attempted sensitive action without MFA")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA required for this operation. Please enable MFA in your account settings."
        )
    return current_user


async def log_admin_action(
    db: AsyncSession,
    admin: User,
    action: str,
    resource_type: str,
    resource_id: str,
    status: str = "success",
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Log admin action to audit log."""
    audit_log = AuditLog(
        user_id=admin.id,
        user_email=admin.email,
        action=getattr(AuditAction, action.upper().replace("-", "_"), AuditAction.USER_UPDATED),
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        details=details or {}
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(
        f"Admin action: {action} by {admin.email} on {resource_type}:{resource_id} - {status}"
    )


@router.get("/users")
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all users (admin only)."""
    query = select(User)
    
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | 
            User.full_name.ilike(f"%{search}%")
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "last_login": u.last_login,
                "created_at": u.created_at
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


@router.get("/users/{user_id}")
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get user details (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's analysis count
    analysis_count = await db.execute(
        select(func.count()).where(AnalysisJob.user_id == user_id)
    )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "company": user.company,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "email_verified": user.email_verified,
        "mfa_enabled": user.mfa_enabled,
        "last_login": user.last_login,
        "last_login_ip": user.last_login_ip,
        "created_at": user.created_at,
        "analysis_count": analysis_count.scalar()
    }


@router.put("/users/{user_id}")
@limiter.limit("30/minute")
async def update_user(
    request: Request,
    user_id: str,
    user_data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Update user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await log_admin_action(
            db, admin, "user-update-failed", "user", user_id,
            status="failed", details={"reason": "User not found"},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # SECURITY: Prevent admins from modifying other admins' roles
    if str(user.id) == str(admin.id):
        await log_admin_action(
            db, admin, "self-modification-attempted", "user", str(user.id),
            status="blocked", details={"attempted_changes": user_data},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        logger.warning(f"SECURITY: Admin {admin.email} attempted self-modification - BLOCKED")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify your own account"
        )
    
    # SECURITY: Prevent role changes entirely
    if "role" in user_data:
        await log_admin_action(
            db, admin, "role-change-attempted", "user", str(user.id),
            status="blocked", details={"attempted_role": user_data["role"]},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        logger.warning(f"SECURITY: Admin {admin.email} attempted role change - BLOCKED")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role changes are not permitted"
        )
    
    # Log previous state for audit
    previous_state = {
        "is_active": user.is_active,
        "full_name": user.full_name,
        "company": user.company
    }
    
    # Update allowed fields (suspend/activate only)
    if "is_active" in user_data:
        user.is_active = user_data["is_active"]
    if "full_name" in user_data:
        user.full_name = user_data["full_name"]
    if "company" in user_data:
        user.company = user_data["company"]
    
    await db.commit()
    
    # Log successful update
    await log_admin_action(
        db, admin, "user-updated", "user", str(user.id),
        status="success", 
        details={"previous_state": previous_state, "changes": user_data},
        ip_address=get_remote_address(request),
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info(f"User {user_id} updated by admin {admin.email}")
    
    return {"message": "User updated successfully"}


@router.delete("/users/{user_id}")
@limiter.limit("10/hour")
async def delete_user(
    request: Request,
    user_id: str,
    password_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin_mfa)
):
    """Delete user (admin only, MFA required, password confirmation)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        await log_admin_action(
            db, admin, "user-delete-failed", "user", user_id,
            status="failed", details={"reason": "User not found"},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # SECURITY: Verify admin password
    password = password_data.get("password")
    if not password:
        await log_admin_action(
            db, admin, "user-delete-failed", "user", str(user.id),
            status="failed", details={"reason": "Password confirmation required"},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password confirmation required"
        )
    
    if not verify_password(password, admin.password_hash):
        await log_admin_action(
            db, admin, "user-delete-failed", "user", str(user.id),
            status="failed", details={"reason": "Invalid password"},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        logger.warning(f"SECURITY: Invalid password attempt for user deletion by admin {admin.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # SECURITY: Prevent self-deletion
    if str(user.id) == str(admin.id):
        await log_admin_action(
            db, admin, "self-deletion-blocked", "user", str(user.id),
            status="blocked", details={"reason": "Self-deletion not allowed"},
            ip_address=get_remote_address(request),
            user_agent=request.headers.get("user-agent")
        )
        logger.warning(f"SECURITY: Admin {admin.email} attempted self-deletion - BLOCKED")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Log deletion target before removing
    await log_admin_action(
        db, admin, "user-deleted", "user", str(user.id),
        status="success", 
        details={
            "deleted_user_email": user.email,
            "deleted_user_role": user.role,
            "deleted_at": datetime.utcnow().isoformat()
        },
        ip_address=get_remote_address(request),
        user_agent=request.headers.get("user-agent")
    )
    
    await db.delete(user)
    await db.commit()
    
    logger.warning(f"SECURITY: User {user.email} ({user_id}) deleted by admin {admin.email}")
    
    return {"message": "User deleted successfully"}


@router.get("/stats")
@limiter.limit("60/minute")
async def get_system_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get system statistics (admin only)."""
    # User statistics
    total_users = await db.execute(select(func.count()).select_from(User))
    active_users = await db.execute(select(func.count()).where(User.is_active == True))
    new_users_today = await db.execute(
        select(func.count()).where(
            User.created_at >= datetime.utcnow() - timedelta(days=1)
        )
    )
    
    # Analysis statistics
    total_analyses = await db.execute(select(func.count()).select_from(AnalysisJob))
    completed_analyses = await db.execute(
        select(func.count()).where(AnalysisJob.status == "completed")
    )
    analyses_today = await db.execute(
        select(func.count()).where(
            AnalysisJob.created_at >= datetime.utcnow() - timedelta(days=1)
        )
    )
    
    # Threat statistics
    phishing_count = await db.execute(
        select(func.count()).where(AnalysisJob.threat_category == "phishing")
    )
    malware_count = await db.execute(
        select(func.count()).where(AnalysisJob.threat_category == "malware")
    )
    
    # Average risk score
    avg_risk = await db.execute(
        select(func.avg(AnalysisJob.risk_score)).where(
            AnalysisJob.status == "completed"
        )
    )
    
    return {
        "users": {
            "total": total_users.scalar(),
            "active": active_users.scalar(),
            "new_today": new_users_today.scalar()
        },
        "analyses": {
            "total": total_analyses.scalar(),
            "completed": completed_analyses.scalar(),
            "today": analyses_today.scalar()
        },
        "threats": {
            "phishing_detected": phishing_count.scalar(),
            "malware_detected": malware_count.scalar(),
            "average_risk_score": round(avg_risk.scalar() or 0, 2)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/model-info")
@limiter.limit("60/minute")
async def get_model_info(
    request: Request,
    admin: User = Depends(get_current_admin)
):
    """Get ML model information (admin only)."""
    detector = get_phishing_detector()
    
    return detector.get_model_info()


@router.post("/model/retrain")
@limiter.limit("3/hour")
async def retrain_model(
    request: Request,
    admin: User = Depends(require_admin_mfa)
):
    """Trigger model retraining (admin only, MFA required)."""
    logger.warning(f"SECURITY: Model retraining triggered by admin {admin.email}")
    
    # Log the action
    db = await get_db().__anext__()
    await log_admin_action(
        db, admin, "model-retrain-queued", "model", "ml-model",
        status="pending", 
        details={"triggered_at": datetime.utcnow().isoformat()},
        ip_address=get_remote_address(request),
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "message": "Model retraining queued",
        "status": "pending"
    }


@router.get("/audit-logs")
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get audit logs (admin only)."""
    import uuid
    
    # Build base query with only necessary columns for filtering
    base_query = select(AuditLog.id, AuditLog.created_at, AuditLog.action, 
                       AuditLog.status, AuditLog.user_id, AuditLog.user_email,
                       AuditLog.ip_address).where(
        AuditLog.created_at >= datetime.utcnow() - timedelta(days=days)
    )
    
    # Apply filters efficiently
    if action:
        base_query = base_query.where(AuditLog.action == action)
    
    if status:
        base_query = base_query.where(AuditLog.status == status)
    
    if user_id:
        # Validate UUID format
        try:
            uuid.UUID(user_id)
            base_query = base_query.where(AuditLog.user_id == user_id)
        except (ValueError, AttributeError):
            # Invalid UUID format
            raise HTTPException(
                status_code=400,
                detail=f"Invalid user_id format: {user_id}. Must be a valid UUID."
            )
    
    # Get total count using optimized count query (avoid subquery)
    count_query = select(func.count(AuditLog.id)).where(
        AuditLog.created_at >= datetime.utcnow() - timedelta(days=days)
    )
    
    # Apply same filters to count query
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if status:
        count_query = count_query.where(AuditLog.status == status)
    if user_id:
        try:
            uuid.UUID(user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)
        except (ValueError, AttributeError):
            pass  # Already validated above
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results with optimized ordering and limiting
    paginated_query = select(AuditLog).where(
        AuditLog.created_at >= datetime.utcnow() - timedelta(days=days)
    )
    
    # Apply filters to main query
    if action:
        paginated_query = paginated_query.where(AuditLog.action == action)
    if status:
        paginated_query = paginated_query.where(AuditLog.status == status)
    if user_id:
        try:
            uuid.UUID(user_id)
            paginated_query = paginated_query.where(AuditLog.user_id == user_id)
        except (ValueError, AttributeError):
            pass  # Already validated above
    
    # Order and paginate efficiently
    paginated_query = paginated_query.order_by(desc(AuditLog.created_at))
    paginated_query = paginated_query.offset((page - 1) * page_size).limit(page_size)
    
    # Execute with memory-efficient fetching
    result = await db.execute(paginated_query)
    logs = result.scalars().all()
    
    return {
        "items": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }
