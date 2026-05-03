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
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
import io

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
router = APIRouter(tags=["Admin"])

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


@router.get(
    "/users",
    summary="List all users",
    description="Returns paginated user list with search, filtering, and sorting. Admin only.",
)
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", pattern="^(created_at|email|last_login)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
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
    
    if role:
        query = query.where(User.role == role)
    
    account_status = request.query_params.get("account_status")
    if account_status:
        query = query.where(User.account_status == account_status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = {
        "created_at": User.created_at,
        "email": User.email,
        "last_login": User.last_login,
    }.get(sort_by, User.created_at)
    
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
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
                "account_status": u.account_status,
                "is_verified": u.is_verified,
                "mfa_enabled": u.mfa_enabled,
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


@router.get(
    "/users/export",
    summary="Export user report",
    description="Generates and downloads a PDF report of all users with optional date and status filters. Admin only.",
)
@limiter.limit("30/minute")
async def export_users_report(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Export user management report as PDF (admin only)."""
    from app.services.report_service import generate_user_management_report
    
    if start_date or end_date:
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2020, 1, 1)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc)
        date_filter = (User.created_at >= start_dt) & (User.created_at <= end_dt)
    else:
        start_dt = None
        end_dt = None
        date_filter = True
    
    query = select(User)
    if start_dt or end_dt:
        query = query.where(date_filter)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role:
        query = query.where(User.role == role)
    
    query = query.order_by(User.created_at.desc()).limit(500)
    result = await db.execute(query)
    users = result.scalars().all()
    
    user_data = [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "company": getattr(u, 'company', None),
            "role": u.role,
            "is_active": u.is_active,
            "account_status": u.account_status,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
    
    date_range = {
        "start_date": start_date,
        "end_date": end_date,
    }
    filters = {
        "is_active": is_active,
        "role": role,
    }
    
    pdf_bytes = generate_user_management_report(user_data, date_range, filters)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"user_management_report_{timestamp}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/audit-logs/export",
    summary="Export audit log report",
    description="Generates and downloads a PDF report of audit logs with optional filters. Admin only.",
)
@limiter.limit("30/minute")
async def export_audit_logs_report(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    user_email: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Export audit log report as PDF (admin only)."""
    from app.services.report_service import generate_audit_log_report
    
    if start_date or end_date:
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now(timezone.utc) - timedelta(days=30)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc)
        date_filter = (AuditLog.created_at >= start_dt) & (AuditLog.created_at <= end_dt)
    else:
        start_dt = datetime.now(timezone.utc) - timedelta(days=30)
        end_dt = datetime.now(timezone.utc)
        date_filter = AuditLog.created_at >= start_dt
    
    query = select(AuditLog).where(date_filter)
    if action:
        actions = [a.strip().lower() for a in action.split(',')]
        if len(actions) == 1:
            query = query.where(AuditLog.action.ilike(actions[0]))
        else:
            query = query.where(AuditLog.action.in_(actions))
    if status:
        query = query.where(AuditLog.status == status)
    if user_email:
        query = query.where(AuditLog.user_email.ilike(f"%{user_email}%"))
    
    query = query.order_by(desc(AuditLog.created_at)).limit(500)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    log_data = [
        {
            "id": str(log.id),
            "user_email": log.user_email,
            "action": log.action,
            "resource_type": log.resource_type,
            "status": log.status,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    
    date_range = {
        "start_date": start_date,
        "end_date": end_date,
    }
    filters = {
        "action": action,
        "status": status,
        "user_email": user_email,
    }
    
    pdf_bytes = generate_audit_log_report(log_data, date_range, filters)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"audit_log_report_{timestamp}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/users/{user_id}",
    summary="Get user details",
    description="Returns detailed information about a specific user including analysis count. Admin only.",
)
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get user details (admin only)."""
    analysis_count_subq = (
        select(func.count(AnalysisJob.id))
        .where(AnalysisJob.user_id == user_id)
        .scalar_subquery()
    )
    
    result = await db.execute(
        select(User, analysis_count_subq.label("analysis_count"))
        .where(User.id == user_id)
    )
    row = result.first()
    
    if not row or not row.User:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = row.User
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
        "analysis_count": row.analysis_count or 0
    }


@router.put(
    "/users/{user_id}",
    summary="Update user",
    description="Updates user fields (is_active, full_name, company, account_status). Prevents self-modification and role changes. Admin only.",
)
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
    if "account_status" in user_data:
        user.account_status = user_data["account_status"]
        if user_data["account_status"] == "active":
            user.is_active = True
    
    await db.commit()
    
    # If account was approved, send notification email
    if user_data.get("account_status") == "active":
        try:
            from app.services.email_service import email_service
            settings = get_settings()
            await email_service.send_account_approved(
                to_email=user.email,
                user_name=user.full_name or user.email.split("@")[0],
                dashboard_url=f"{settings.FRONTEND_URL}/login"
            )
            logger.info(f"Approval email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send approval email to {user.email}: {e}")
    
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


@router.delete(
    "/users/{user_id}",
    summary="Delete user",
    description="Permanently deletes a user and all associated data. Requires MFA and password confirmation. Prevents self-deletion. Admin only.",
)
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
            "deleted_at": datetime.now(timezone.utc).isoformat()
        },
        ip_address=get_remote_address(request),
        user_agent=request.headers.get("user-agent")
    )
    
    await db.delete(user)
    await db.commit()
    
    from app.database import get_mongodb_database
    mongodb = get_mongodb_database()
    
    await mongodb.analysis_results.delete_many({"user_id": str(user.id)})
    await mongodb.gmail_analysis_queue.delete_many({"user_id": str(user.id)})
    await mongodb.notifications.delete_many({"user_id": str(user.id)})
    
    logger.warning(f"SECURITY: User {user.email} ({user_id}) deleted by admin {admin.email}")
    
    return {"message": "User deleted successfully"}


@router.get(
    "/stats",
    summary="Get system statistics",
    description="Returns aggregated statistics for users, analyses, threats, and system health. Admin only.",
)
@limiter.limit("60/minute")
async def get_system_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get system statistics (admin only)."""
    from app.models.email_provider import EmailProvider
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    today = datetime.now(timezone.utc) - timedelta(days=1)
    
    # Single query for all user stats
    user_stats_query = select(
        func.count().label('total'),
        func.sum(case((User.is_active == True, 1), else_=0)).label('active'),
        func.sum(case((User.created_at >= today, 1), else_=0)).label('new_today'),
        func.sum(case((User.account_status == "pending", 1), else_=0)).label('pending'),
        func.sum(case((User.mfa_enabled == True, 1), else_=0)).label('mfa'),
        func.sum(case((User.last_login >= thirty_days_ago, 1), else_=0)).label('active_30d'),
    ).select_from(User)
    user_stats = await db.execute(user_stats_query)
    u = user_stats.one()
    
    # Single query for all analysis stats (only completed rows for avg)
    analysis_stats_query = select(
        func.count().label('total'),
        func.sum(case((AnalysisJob.status == "completed", 1), else_=0)).label('completed'),
        func.sum(case((AnalysisJob.created_at >= today, 1), else_=0)).label('today'),
        func.sum(case((AnalysisJob.status.in_(["processing", "pending"]), 1), else_=0)).label('active'),
        func.sum(case((AnalysisJob.threat_category == "phishing", 1), else_=0)).label('phishing'),
        func.sum(case((AnalysisJob.threat_category == "malware", 1), else_=0)).label('malware'),
        func.avg(AnalysisJob.risk_score).label('avg_risk'),
    ).select_from(AnalysisJob)
    analysis_stats = await db.execute(analysis_stats_query)
    a = analysis_stats.one()
    
    # Gmail connections (separate table)
    gmail_result = await db.execute(
        select(func.count(EmailProvider.id))
        .where(EmailProvider.provider_type == "gmail", EmailProvider.is_connected == True)
    )
    
    total_users_val = u.total
    active_users_val = u.active or 0
    new_today_val = u.new_today or 0
    pending_activations_val = u.pending or 0
    mfa_enabled_users_val = u.mfa or 0
    active_users_30d_val = u.active_30d or 0
    
    total_analyses_val = a.total
    completed_analyses_val = a.completed or 0
    analyses_today_val = a.today or 0
    email_analysed_active_count = a.active or 0
    phishing_count_val = a.phishing or 0
    malware_count_val = a.malware or 0
    threats_detected = phishing_count_val + malware_count_val
    avg_risk_val = a.avg_risk or 0
    gmail_connections_val = gmail_result.scalar() or 0
    
    return {
        "users": {
            "total": total_users_val,
            "active": active_users_val,
            "new_today": new_today_val
        },
        "analyses": {
            "total": total_analyses_val,
            "completed": completed_analyses_val,
            "today": analyses_today_val,
            "active": email_analysed_active_count
        },
        "threats": {
            "phishing_detected": phishing_count_val,
            "malware_detected": malware_count_val,
            "detected": threats_detected,
            "average_risk_score": round(avg_risk_val, 2)
        },
        "pending_activations": pending_activations_val,
        "gmail_connections": gmail_connections_val,
        "mfa_enabled_users": mfa_enabled_users_val,
        "active_users_30d": active_users_30d_val,
        "total_users": total_users_val,
        "active_users": active_users_val,
        "total_emails": completed_analyses_val,
        "threats_detected": threats_detected,
        "avg_threat_score": round(avg_risk_val, 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/model-info",
    summary="Get ML model information",
    description="Returns the current ML model's version, accuracy, and training metadata. Admin only.",
)
@limiter.limit("60/minute")
async def get_model_info(
    request: Request,
    admin: User = Depends(get_current_admin)
):
    """Get ML model information (admin only)."""
    detector = get_phishing_detector()
    
    return detector.get_model_info()


@router.post(
    "/model/retrain",
    summary="Trigger model retraining",
    description="Queues an ML model retraining job. Requires MFA. Admin only.",
)
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
        details={"triggered_at": datetime.now(timezone.utc).isoformat()},
        ip_address=get_remote_address(request),
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "message": "Model retraining queued",
        "status": "pending"
    }


@router.get(
    "/analytics",
    summary="Get analytics data",
    description="Returns time-series data for daily analyses, threat categories, risk distribution, and user activity charts. Admin only.",
)
@limiter.limit("30/minute")
async def get_analytics(
    request: Request,
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get analytics data for charts (admin only)."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Daily analyses: single GROUP BY query instead of 4*days queries
    daily_stats_query = select(
        func.date_trunc('day', AnalysisJob.created_at).label('day'),
        func.count().label('total'),
        func.sum(case((AnalysisJob.threat_category == "phishing", 1), else_=0)).label('phishing'),
        func.sum(case((AnalysisJob.risk_score.between(40, 69), 1), else_=0)).label('suspicious'),
        func.sum(case(
            ((AnalysisJob.risk_score < 40) & (AnalysisJob.status == "completed"), 1),
            else_=0
        )).label('safe'),
    ).where(
        AnalysisJob.created_at >= start_date
    ).group_by(
        'day'
    ).order_by(
        'day'
    )
    daily_result = await db.execute(daily_stats_query)
    daily_rows = {row.day.strftime('%Y-%m-%d'): row for row in daily_result.all()}
    
    daily_data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        row = daily_rows.get(day_str)
        daily_data.append({
            "date": day_str,
            "total": row.total if row else 0,
            "phishing": row.phishing if row else 0,
            "suspicious": row.suspicious if row else 0,
            "safe": row.safe if row else 0,
        })
    
    # Threat category breakdown (all time)
    category_query = select(
        AnalysisJob.threat_category,
        func.count(AnalysisJob.id)
    ).where(
        AnalysisJob.threat_category.isnot(None),
        AnalysisJob.threat_category != ""
    ).group_by(AnalysisJob.threat_category)
    
    category_result = await db.execute(category_query)
    category_breakdown = [
        {"category": row[0] or "unknown", "count": row[1]}
        for row in category_result.all()
    ]
    
    # Risk score distribution: single query with conditional aggregation
    risk_distribution_query = select(
        func.sum(case((AnalysisJob.risk_score.between(0, 20), 1), else_=0)).label('range_0_20'),
        func.sum(case((AnalysisJob.risk_score.between(21, 40), 1), else_=0)).label('range_21_40'),
        func.sum(case((AnalysisJob.risk_score.between(41, 60), 1), else_=0)).label('range_41_60'),
        func.sum(case((AnalysisJob.risk_score.between(61, 80), 1), else_=0)).label('range_61_80'),
        func.sum(case((AnalysisJob.risk_score.between(81, 100), 1), else_=0)).label('range_81_100'),
    ).where(
        AnalysisJob.status == "completed"
    )
    risk_result = await db.execute(risk_distribution_query)
    risk_row = risk_result.one()
    risk_distribution = [
        {"range": "0-20", "count": risk_row.range_0_20 or 0},
        {"range": "21-40", "count": risk_row.range_21_40 or 0},
        {"range": "41-60", "count": risk_row.range_41_60 or 0},
        {"range": "61-80", "count": risk_row.range_61_80 or 0},
        {"range": "81-100", "count": risk_row.range_81_100 or 0},
    ]
    
    # User activity: 2 GROUP BY queries instead of 2*days queries
    new_users_query = select(
        func.date_trunc('day', User.created_at).label('day'),
        func.count(User.id).label('count')
    ).where(
        User.created_at >= start_date
    ).group_by('day')
    new_users_result = await db.execute(new_users_query)
    new_users_by_day = {row.day.strftime('%Y-%m-%d'): row.count for row in new_users_result.all()}
    
    active_users_query = select(
        func.date_trunc('day', User.last_login).label('day'),
        func.count(User.id).label('count')
    ).where(
        User.last_login >= start_date,
        User.last_login.isnot(None)
    ).group_by('day')
    active_result = await db.execute(active_users_query)
    active_users_by_day = {row.day.strftime('%Y-%m-%d'): row.count for row in active_result.all()}
    
    user_activity = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        user_activity.append({
            "date": day_str,
            "new_users": new_users_by_day.get(day_str, 0),
            "active_users": active_users_by_day.get(day_str, 0),
        })
    
    # Get current period stats (last 7 days or current period)
    current_period_start = now - timedelta(days=min(7, days))
    
    current_phishing = await db.execute(
        select(func.count(AnalysisJob.id)).where(
            AnalysisJob.created_at >= current_period_start,
            AnalysisJob.threat_category == "phishing"
        )
    )
    
    current_suspicious = await db.execute(
        select(func.count(AnalysisJob.id)).where(
            AnalysisJob.created_at >= current_period_start,
            AnalysisJob.risk_score >= 40,
            AnalysisJob.risk_score < 70
        )
    )
    
    current_safe = await db.execute(
        select(func.count(AnalysisJob.id)).where(
            AnalysisJob.created_at >= current_period_start,
            AnalysisJob.risk_score < 40,
            AnalysisJob.status == "completed"
        )
    )
    
    # Get users active in last 30 days
    thirty_days_ago = now - timedelta(days=30)
    active_users_30d = await db.execute(
        select(func.count(User.id)).where(
            User.last_login >= thirty_days_ago
        )
    )
    
    return {
        "daily_analyses": daily_data,
        "category_breakdown": category_breakdown,
        "risk_distribution": risk_distribution,
        "user_activity": user_activity,
        "period_days": days,
        "current_threat_status": {
            "phishing": current_phishing.scalar() or 0,
            "suspicious": current_suspicious.scalar() or 0,
            "safe": current_safe.scalar() or 0
        },
        "active_users_30d": active_users_30d.scalar() or 0
    }


@router.get(
    "/audit-logs",
    summary="Get audit logs",
    description="Returns paginated audit logs with filtering by action, status, user email, resource type, and date range. Admin only.",
)
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    status: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get audit logs (admin only)."""
    # Determine date filter: use start/end if provided, otherwise fall back to days
    if start_date or end_date:
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now(timezone.utc) - timedelta(days=90)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc)
        date_filter = (AuditLog.created_at >= start_dt) & (AuditLog.created_at <= end_dt)
    else:
        date_filter = AuditLog.created_at >= datetime.now(timezone.utc) - timedelta(days=days)

    # Build count query
    count_query = select(func.count(AuditLog.id)).where(date_filter)
    if action:
        # Support comma-separated actions (e.g., "login,logout,token_refresh")
        actions = [a.strip().lower() for a in action.split(',')]
        if len(actions) == 1:
            count_query = count_query.where(AuditLog.action.ilike(actions[0]))
        else:
            count_query = count_query.where(AuditLog.action.in_(actions))
    if status:
        count_query = count_query.where(AuditLog.status == status)
    if user_email:
        count_query = count_query.where(AuditLog.user_email.ilike(f"%{user_email}%"))
    if resource_type:
        count_query = count_query.where(AuditLog.resource_type.ilike(f"%{resource_type}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Build paginated query
    paginated_query = select(AuditLog).where(date_filter)
    if action:
        actions = [a.strip().lower() for a in action.split(',')]
        if len(actions) == 1:
            paginated_query = paginated_query.where(AuditLog.action.ilike(actions[0]))
        else:
            paginated_query = paginated_query.where(AuditLog.action.in_(actions))
    if status:
        paginated_query = paginated_query.where(AuditLog.status == status)
    if user_email:
        paginated_query = paginated_query.where(AuditLog.user_email.ilike(f"%{user_email}%"))
    if resource_type:
        paginated_query = paginated_query.where(AuditLog.resource_type.ilike(f"%{resource_type}%"))

    paginated_query = paginated_query.order_by(desc(AuditLog.created_at))
    paginated_query = paginated_query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(paginated_query)
    logs = result.scalars().all()

    return {
        "items": [log.to_dict() for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }
