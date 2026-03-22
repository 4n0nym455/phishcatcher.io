"""
Analysis Router

This module handles email analysis endpoints including:
- File upload for analysis
- Get analysis results
- Analysis history
- Report download
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, get_mongodb_database
from app.models.user import User
from app.models.analysis_job import AnalysisJob
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.analysis import (
    AnalysisResponse, AnalysisList, AnalysisFilters, 
    ReportFormat, WeeklyReport, AnalysisStatus
)
from app.routers.auth import get_current_active_user
from app.tasks.analysis import analyze_email_task
from app.services.storage import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=AnalysisStatus, status_code=status.HTTP_202_ACCEPTED)
async def upload_email(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload an email file for analysis with MinIO storage."""
    settings = get_settings()
    
    # Validate file type
    allowed_extensions = settings.ALLOWED_FILE_EXTENSIONS
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    storage_result = None
    try:
        # Upload file to MinIO storage
        storage_result = await storage_service.upload_bytes(
            data=content,
            filename=file.filename,
            folder=f"emails/{current_user.id}",
            is_public=False,
            metadata={
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "upload_source": "web_upload"
            }
        )
        
        logger.info(f"File uploaded to MinIO: {storage_result['object_name']}")
        
    except RuntimeError as e:
        if "MinIO storage service is not available" in str(e):
            logger.warning(f"MinIO not available, proceeding without storage: {e}")
            # Continue without MinIO storage - file will be passed directly to analysis
            storage_result = None
        else:
            raise
    except Exception as e:
        logger.error(f"Failed to upload file to MinIO: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store file. Please try again."
        )
    
    # Create analysis job
    job = AnalysisJob(
        user_id=current_user.id,
        source_type="upload",
        file_name=file.filename,
        file_size=len(content),
        file_type=file_ext.lstrip('.'),
        status="pending",
        storage_object_name=storage_result["object_name"] if storage_result else None,
        storage_bucket=storage_result["bucket"] if storage_result else None
    )
    
    db.add(job)
    await db.flush()
    
    # Log analysis creation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.ANALYSIS_CREATED,
        resource_type="analysis",
        resource_id=job.id,
        status="success",
        details={
            "file_name": file.filename, 
            "file_size": len(content),
            "storage_object": storage_result["object_name"] if storage_result else None,
            "storage_available": storage_result is not None
        }
    )
    db.add(audit_log)
    await db.commit()
    
    # Queue analysis task with file from MinIO
    analyze_email_task.delay(str(job.id), content, str(current_user.id))
    
    logger.info(f"Analysis job {job.id} created for user {current_user.email}")
    
    return AnalysisStatus(
        id=str(job.id),
        status=job.status,
        progress_percent=0,
        current_step="Queued for analysis"
    )


@router.get("/history", response_model=AnalysisList)
async def get_analysis_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    threat_category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's analysis history."""
    # Build query
    query = select(AnalysisJob).where(AnalysisJob.user_id == current_user.id)
    
    if status:
        query = query.where(AnalysisJob.status == status)
    
    if threat_category:
        query = query.where(AnalysisJob.threat_category == threat_category)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(desc(AnalysisJob.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return AnalysisList(
        items=[
            {
                "id": str(job.id),
                "source_type": job.source_type,
                "file_name": job.file_name,
                "status": job.status,
                "risk_score": job.risk_score,
                "threat_category": job.threat_category,
                "findings_count": job.findings_count,
                "created_at": job.created_at,
                "completed_at": job.completed_at
            }
            for job in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get analysis results by ID."""
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.id == analysis_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Check ownership
    if str(job.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get detailed results from MongoDB if available
    findings = []
    links_analyzed = []
    attachments_analyzed = []
    risk_factors = None
    
    if job.mongodb_result_id:
        mongodb = get_mongodb_database()
        detailed_result = await mongodb.analysis_results.find_one(
            {"_id": job.mongodb_result_id}
        )
        
        if detailed_result:
            findings = detailed_result.get("findings", [])
            links_analyzed = detailed_result.get("links_analyzed", [])
            attachments_analyzed = detailed_result.get("attachments_analyzed", [])
            risk_factors = detailed_result.get("risk_factors")
    
    return AnalysisResponse(
        id=str(job.id),
        source_type=job.source_type,
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        email_metadata={
            "subject": job.file_name  # Using filename as subject for uploaded files
        } if job.source_type == "upload" else None,
        risk_score=job.risk_score,
        threat_category=job.threat_category,
        confidence=job.confidence,
        findings=findings,
        findings_count=job.findings_count,
        critical_findings=job.critical_findings,
        high_findings=job.high_findings,
        medium_findings=job.medium_findings,
        low_findings=job.low_findings,
        links_analyzed=links_analyzed,
        attachments_analyzed=attachments_analyzed,
        risk_factors=risk_factors,
        report_generated=job.report_generated,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_seconds=job.duration_seconds
    )


@router.get("/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get analysis status (lightweight endpoint for polling)."""
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.id == analysis_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    if str(job.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return AnalysisStatus(
        id=str(job.id),
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        risk_score=job.risk_score,
        threat_category=job.threat_category
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an analysis."""
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.id == analysis_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    if str(job.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete from MongoDB
    if job.mongodb_result_id:
        mongodb = get_mongodb_database()
        await mongodb.analysis_results.delete_one({"_id": job.mongodb_result_id})
    
    # Delete from PostgreSQL
    await db.delete(job)
    
    # Log deletion
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.ANALYSIS_DELETED,
        resource_type="analysis",
        resource_id=job.id,
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"Analysis {analysis_id} deleted by {current_user.email}")


@router.get("/{analysis_id}/download")
async def download_report(
    analysis_id: str,
    format: ReportFormat = ReportFormat.PDF,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download analysis report."""
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.id == analysis_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    if str(job.user_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis not completed yet"
        )
    
    # TODO: Generate report file
    # For now, return JSON data
    
    # Log download
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.REPORT_DOWNLOADED,
        resource_type="analysis",
        resource_id=job.id,
        status="success",
        details={"format": format}
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "Report generation not implemented yet"}


@router.get("/reports/weekly", response_model=WeeklyReport)
async def get_weekly_report(
    week_start: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get weekly analysis report."""
    # Calculate week range
    if not week_start:
        week_start = datetime.utcnow() - timedelta(days=7)
    
    week_end = week_start + timedelta(days=7)
    
    # Query analyses in date range
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.user_id == current_user.id,
            AnalysisJob.status == "completed",
            AnalysisJob.completed_at >= week_start,
            AnalysisJob.completed_at < week_end
        )
    )
    jobs = result.scalars().all()
    
    # Calculate statistics
    total_analyses = len(jobs)
    phishing_detected = sum(1 for j in jobs if j.threat_category == "phishing")
    malware_detected = sum(1 for j in jobs if j.threat_category == "malware")
    suspicious_detected = sum(1 for j in jobs if j.threat_category == "suspicious")
    safe_emails = sum(1 for j in jobs if j.threat_category == "safe")
    
    risk_scores = [j.risk_score for j in jobs if j.risk_score is not None]
    average_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    
    return WeeklyReport(
        week_start=week_start,
        week_end=week_end,
        total_analyses=total_analyses,
        total_emails=total_analyses,
        phishing_detected=phishing_detected,
        malware_detected=malware_detected,
        suspicious_detected=suspicious_detected,
        safe_emails=safe_emails,
        average_risk_score=average_risk_score,
        top_threats=[],
        daily_breakdown=[]
    )
