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
from datetime import datetime, timedelta
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
    queue_only: bool = Query(False, description="Only add to queue without starting analysis"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload an email file for analysis with MinIO storage.
    
    If queue_only=True, the file is added to queue without starting analysis.
    User can then initiate analysis from the Analysis page.
    """
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
        settings = get_settings()
        storage_result = await storage_service.upload_bytes(
            data=content,
            filename=file.filename,
            folder=f"emails/{current_user.id}",
            is_public=False,
            bucket=settings.MINIO_BUCKET_EMAILS,
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
        # Degrade gracefully when object storage is unreachable (e.g. local API run
        # with Docker-only endpoint like "minio:9000"). Analysis can still proceed
        # with in-memory file content.
        logger.warning(f"MinIO upload failed, continuing without storage: {e}")
        storage_result = None
    
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
        resource_id=str(job.id),
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
    
    # Add to same queue as Gmail emails
    from app.database import get_mongodb_database
    from datetime import datetime
    mongodb = get_mongodb_database()
    
    queue_doc = {
        "user_id": str(current_user.id),
        "job_id": str(job.id),
        "message_id": str(job.id),
        "source": "upload",
        "file_name": file.filename,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "subject": file.filename,
        "sender": "upload"
    }
    await mongodb.gmail_analysis_queue.insert_one(queue_doc)
    
    current_step = "Added to queue"
    
    return AnalysisStatus(
        id=str(job.id),
        status=job.status,
        progress_percent=0,
        current_step=current_step
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
                "analysis_id": str(job.id),
                "source_type": job.source_type,
                "file_name": job.file_name,
                "subject": job.file_name or f"{job.source_type.title()} analysis" if job.source_type else "Untitled",
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
    # Validate analysis_id - accept PostgreSQL UUIDs (with or without dashes) and 32-char hex IDs
    if not analysis_id or analysis_id in ('None', 'null', 'undefined', ''):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Check if it's a 32-char hex string (could be UUID without dashes or custom hex ID)
    import re
    hex_id_pattern = re.compile(r'^[0-9a-f]{32}$', re.I)
    is_hex_32 = bool(hex_id_pattern.match(analysis_id))
    
    # Store original for MongoDB lookup
    original_id = analysis_id
    
    # Check if it's a PostgreSQL UUID (8-4-4-4-12 format)
    is_uuid = False
    analysis_uuid = None
    try:
        import uuid
        analysis_uuid = uuid.UUID(analysis_id)
        is_uuid = True
    except (ValueError, AttributeError):
        pass
    
    # If it's a 32-char hex without dashes, try to parse as UUID
    was_hex_32 = is_hex_32  # Track if it was originally hex
    if is_hex_32 and not is_uuid:
        try:
            formatted = f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}"
            analysis_uuid = uuid.UUID(formatted)
            is_uuid = True
        except Exception:
            pass
    
    if not is_uuid and not is_hex_32:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    job = None
    
    # Query PostgreSQL if valid UUID
    if is_uuid and analysis_uuid:
        result = await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == analysis_uuid)
        )
        job = result.scalar_one_or_none()
        
        if job:
            # Check ownership
            if str(job.user_id) != str(current_user.id) and not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
    
    # If not found in PostgreSQL, check MongoDB (even if it was converted to UUID)
    if not job:
        mongodb = get_mongodb_database()
        
        # Clean ID for MongoDB lookup (remove dashes)
        clean_id = original_id.replace("-", "")
        clean_analysis_id = analysis_id.replace("-", "") if analysis_id else None
        
        # Try with original ID (may be 32-char hex already)
        mongo_result = await mongodb.analysis_results.find_one({"_id": original_id})
        
        # Try with cleaned ID (UUID without dashes)
        if not mongo_result and clean_id != original_id:
            mongo_result = await mongodb.analysis_results.find_one({"_id": clean_id})
        
        # Try with job_id field
        if not mongo_result:
            mongo_result = await mongodb.analysis_results.find_one({"job_id": original_id})
        
        # Try with cleaned job_id
        if not mongo_result and clean_id:
            mongo_result = await mongodb.analysis_results.find_one({"job_id": clean_id})
        
        if not mongo_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Check ownership via user_id in MongoDB
        mongo_user_id = str(mongo_result.get("user_id", ""))
        if mongo_user_id and mongo_user_id != str(current_user.id) and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Build response from MongoDB data with proper type conversions
        email_meta_raw = mongo_result.get("email_metadata", {})
        
        # Convert email_metadata recipient to list if needed
        recipient_val = email_meta_raw.get("recipient")
        if isinstance(recipient_val, str):
            # Parse "Name <email>" or just "email" format
            import re
            email_match = re.search(r'<(.+?)>|^(.+?)$', recipient_val)
            recipient_list = [email_match.group(1) or email_match.group(2) if email_match else recipient_val]
        else:
            recipient_list = recipient_val if isinstance(recipient_val, list) else []
        
        # Convert date string to datetime if needed
        date_val = email_meta_raw.get("date")
        date_parsed = None
        if date_val and isinstance(date_val, str):
            try:
                # Try parsing RFC 2822 date format
                from email.utils import parsedate_to_datetime
                date_parsed = parsedate_to_datetime(date_val)
            except Exception:
                try:
                    # Fallback to manual parse
                    date_parsed = datetime.strptime(date_val, '%a, %d %b %Y %H:%M:%S %z')
                except Exception:
                    pass
        
        # Map threat_category to valid enum value
        category_raw = mongo_result.get("risk_assessment", {}).get("category", "")
        valid_categories = {"phishing", "malware", "spoofing", "spam", "safe", "suspicious"}
        if category_raw.lower() not in valid_categories:
            # Map invalid categories to valid ones
            category_map = {"caution": "suspicious", "unknown": "suspicious", "safe": "safe"}
            category_raw = category_map.get(category_raw.lower(), "suspicious")
        
        return AnalysisResponse(
            id=original_id,
            source_type=mongo_result.get("source", "unknown"),
            status="completed",
            progress_percent=100,
            current_step="Analysis complete",
            email_metadata={
                "subject": email_meta_raw.get("subject"),
                "sender": email_meta_raw.get("sender"),
                "sender_name": email_meta_raw.get("sender_name"),
                "recipient": recipient_list,
                "cc": email_meta_raw.get("cc", []),
                "bcc": email_meta_raw.get("bcc", []),
                "date": date_parsed,
                "message_id": email_meta_raw.get("message_id"),
                "reply_to": email_meta_raw.get("reply_to"),
                "return_path": email_meta_raw.get("return_path"),
            },
            risk_score=mongo_result.get("risk_assessment", {}).get("overall_score"),
            threat_category=category_raw,
            confidence=mongo_result.get("risk_assessment", {}).get("confidence"),
            findings=mongo_result.get("findings", []),
            findings_count=len(mongo_result.get("findings", [])),
            created_at=mongo_result.get("created_at"),
            completed_at=mongo_result.get("created_at")
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
    email_meta_from_mongo = None
    
    # Clean the mongodb_result_id (remove dashes for MongoDB lookup)
    mongo_id = job.mongodb_result_id.replace("-", "") if job.mongodb_result_id else None
    
    if mongo_id:
        mongodb = get_mongodb_database()
        detailed_result = await mongodb.analysis_results.find_one(
            {"_id": mongo_id}
        )
        
        # Also try by job_id if not found
        if not detailed_result:
            detailed_result = await mongodb.analysis_results.find_one(
                {"job_id": mongo_id}
            )
        
        if detailed_result:
            findings = detailed_result.get("findings", [])
            links_analyzed = detailed_result.get("links_analyzed", [])
            attachments_analyzed = detailed_result.get("attachments_analyzed", [])
            risk_factors = detailed_result.get("risk_factors")
            
            # Extract email_metadata from MongoDB if available
            email_meta_raw = detailed_result.get("email_metadata")
            if email_meta_raw:
                recipient_val = email_meta_raw.get("recipient")
                if isinstance(recipient_val, str):
                    import re
                    email_match = re.search(r'<(.+?)>|^(.+?)$', recipient_val)
                    recipient_list = [email_match.group(1) or email_match.group(2) if email_match else recipient_val]
                else:
                    recipient_list = recipient_val if isinstance(recipient_val, list) else []
                
                date_val = email_meta_raw.get("date")
                date_parsed = None
                if date_val and isinstance(date_val, str):
                    try:
                        from email.utils import parsedate_to_datetime
                        date_parsed = parsedate_to_datetime(date_val)
                    except Exception:
                        try:
                            date_parsed = datetime.strptime(date_val, '%a, %d %b %Y %H:%M:%S %z')
                        except Exception:
                            pass
                
                email_meta_from_mongo = {
                    "subject": email_meta_raw.get("subject"),
                    "sender": email_meta_raw.get("sender"),
                    "sender_name": email_meta_raw.get("sender_name"),
                    "recipient": recipient_list,
                    "cc": email_meta_raw.get("cc", []),
                    "bcc": email_meta_raw.get("bcc", []),
                    "date": date_parsed,
                    "message_id": email_meta_raw.get("message_id"),
                    "reply_to": email_meta_raw.get("reply_to"),
                    "return_path": email_meta_raw.get("return_path"),
                }
            
            # Extract ML prediction details if available
            ml_prediction = detailed_result.get("ml_prediction", {})
            if ml_prediction:
                # Add ML details to the response
                ml_details = {
                    "is_phishing": ml_prediction.get("is_phishing"),
                    "phishing_probability": ml_prediction.get("phishing_probability"),
                    "safe_probability": ml_prediction.get("safe_probability"),
                    "category": ml_prediction.get("category"),
                    "confidence": ml_prediction.get("confidence"),
                    "model_version": ml_prediction.get("model_version"),
                    "features_used": ml_prediction.get("features_used")
                }
                # Store in a custom field for frontend
                detailed_result["ml_analysis"] = ml_details
    
    # Normalize links_analyzed to ensure required fields
    links_analyzed_normalized = []
    for link in links_analyzed:
        if isinstance(link, dict):
            links_analyzed_normalized.append({
                "url": link.get("url", ""),
                "display_text": link.get("display_text"),
                "domain": link.get("domain", ""),
                "ip_address": link.get("ip_address"),
                "status": link.get("status", "unknown"),
                "reputation_score": link.get("reputation_score"),
                "category": link.get("category"),
                "redirects_to": link.get("redirects_to"),
                "is_shortened": link.get("is_shortened", False),
                "is_ip_based": link.get("is_ip_based", False),
                "threat_intelligence": link.get("threat_intelligence", {})
            })
    
    # Normalize attachments_analyzed to ensure required fields
    attachments_analyzed_normalized = []
    for att in attachments_analyzed:
        if isinstance(att, dict):
            attachments_analyzed_normalized.append({
                "filename": att.get("filename", ""),
                "content_type": att.get("content_type", ""),
                "size": att.get("size", 0),
                "hash_md5": att.get("hash_md5"),
                "hash_sha1": att.get("hash_sha1"),
                "hash_sha256": att.get("hash_sha256"),
                "status": att.get("status", "unknown"),
                "threat_intelligence": att.get("threat_intelligence", {}),
                "is_executable": att.get("is_executable", False),
                "is_script": att.get("is_script", False)
            })
    
    return AnalysisResponse(
        id=str(job.id),
        source_type=job.source_type,
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        email_metadata=email_meta_from_mongo or ({"subject": job.file_name} if job.source_type == "upload" else None),
        risk_score=job.risk_score,
        threat_category=job.threat_category,
        confidence=job.confidence,
        findings=findings,
        findings_count=job.findings_count,
        critical_findings=job.critical_findings,
        high_findings=job.high_findings,
        medium_findings=job.medium_findings,
        low_findings=job.low_findings,
        links_analyzed=links_analyzed_normalized,
        attachments_analyzed=attachments_analyzed_normalized,
        risk_factors=risk_factors,
        ml_analysis=detailed_result.get("ml_analysis") if detailed_result else None,
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
    # Validate analysis_id - accept UUIDs (with or without dashes) and 32-char hex IDs
    if not analysis_id or analysis_id in ('None', 'null', 'undefined', ''):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Check if it's a 32-char hex string
    import re
    hex_id_pattern = re.compile(r'^[0-9a-f]{32}$', re.I)
    is_hex_32 = bool(hex_id_pattern.match(analysis_id))
    
    # Store original for MongoDB lookup
    original_id = analysis_id
    
    # Check if it's a PostgreSQL UUID
    is_uuid = False
    analysis_uuid = None
    try:
        import uuid
        analysis_uuid = uuid.UUID(analysis_id)
        is_uuid = True
    except (ValueError, AttributeError):
        pass
    
    # If 32-char hex without dashes, try to parse as UUID
    if is_hex_32 and not is_uuid:
        try:
            formatted = f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}"
            analysis_uuid = uuid.UUID(formatted)
            is_uuid = True
        except Exception:
            pass
    
    if not is_uuid and not is_hex_32:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Query PostgreSQL if valid UUID
    if is_uuid and analysis_uuid:
        result = await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == analysis_uuid)
        )
        job = result.scalar_one_or_none()
        
        if job:
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
    
    # For hex IDs or converted UUIDs, check MongoDB
    if is_hex_32:
        from app.database import get_mongodb_database
        mongodb = get_mongodb_database()
        
        # Try original ID first
        mongo_result = await mongodb.analysis_results.find_one({"_id": original_id})
        
        # Also try with converted UUID
        if not mongo_result and original_id != analysis_id:
            mongo_result = await mongodb.analysis_results.find_one({"_id": analysis_id})
        
        # Try with job_id (for Gmail results stored with MongoDB ObjectId)
        if not mongo_result:
            mongo_result = await mongodb.analysis_results.find_one({"job_id": original_id})
        
        if mongo_result:
            # Check ownership
            mongo_user_id = str(mongo_result.get("user_id", ""))
            if mongo_user_id and mongo_user_id != str(current_user.id) and not current_user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
            
            return AnalysisStatus(
                id=original_id,
                status="completed",
                progress_percent=100,
                current_step="Complete",
                risk_score=mongo_result.get("risk_assessment", {}).get("overall_score"),
                threat_category=mongo_result.get("risk_assessment", {}).get("category")
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Analysis not found"
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an analysis."""
    # Validate analysis_id - accept both PostgreSQL UUIDs and 32-char hex IDs
    if not analysis_id or analysis_id in ('None', 'null', 'undefined', ''):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    import re
    hex_id_pattern = re.compile(r'^[0-9a-f]{32}$', re.I)
    is_hex_32 = bool(hex_id_pattern.match(analysis_id))
    
    is_uuid = False
    analysis_uuid = None
    try:
        import uuid
        analysis_uuid = uuid.UUID(analysis_id)
        is_uuid = True
    except (ValueError, AttributeError):
        pass
    
    # If 32-char hex without dashes, try to parse as UUID
    if is_hex_32 and not is_uuid:
        try:
            formatted = f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}"
            analysis_uuid = uuid.UUID(formatted)
            is_uuid = True
        except Exception:
            pass
    
    if not is_uuid and not is_hex_32:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    if is_hex_32 and not is_uuid:
        # Delete from MongoDB directly
        from app.database import get_mongodb_database
        mongodb = get_mongodb_database()
        await mongodb.analysis_results.delete_one({"_id": analysis_id})
        return None
    
    if is_uuid and analysis_uuid:
        result = await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == analysis_uuid)
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
        resource_id=analysis_id,
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
    # Validate analysis_id
    if not analysis_id or analysis_id in ('None', 'null', 'undefined', ''):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID"
        )
    
    # Validate UUID format
    try:
        import uuid
        uuid.UUID(analysis_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID format"
        )
    
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
        resource_id=analysis_id,
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
    from datetime import timedelta
    
    if not week_start:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    week_end = week_start + timedelta(days=7)
    
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.user_id == current_user.id,
            AnalysisJob.status == "completed",
            AnalysisJob.completed_at >= week_start,
            AnalysisJob.completed_at < week_end
        )
    )
    jobs = result.scalars().all()
    
    total_analyses = len(jobs)
    phishing_detected = sum(1 for j in jobs if j.threat_category == "phishing")
    malware_detected = sum(1 for j in jobs if j.threat_category == "malware")
    suspicious_detected = sum(1 for j in jobs if j.threat_category == "suspicious")
    safe_emails = sum(1 for j in jobs if j.threat_category == "safe")
    
    risk_scores = [j.risk_score for j in jobs if j.risk_score is not None]
    average_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    
    daily_breakdown = []
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, day_name in enumerate(day_names):
        day_start = week_start + timedelta(days=i)
        day_jobs = [j for j in jobs if j.completed_at and j.completed_at.date() == day_start.date()]
        daily_breakdown.append({
            "day": day_name,
            "analyzed": len(day_jobs),
            "threats": sum(1 for j in day_jobs if j.threat_category in ["phishing", "malware"]),
            "suspicious": sum(1 for j in day_jobs if j.threat_category == "suspicious")
        })
    
    threats_by_category = {}
    for j in jobs:
        if j.threat_category in ["phishing", "malware"]:
            cat = j.threat_category
            if cat not in threats_by_category:
                threats_by_category[cat] = {"count": 0, "risk_score": 0}
            threats_by_category[cat]["count"] += 1
            if j.risk_score:
                threats_by_category[cat]["risk_score"] += j.risk_score
    
    top_threats = []
    for cat, data in threats_by_category.items():
        if data["count"] > 0:
            top_threats.append({
                "id": cat,
                "subject": f"{cat.title()} threat detected",
                "sender": f"Multiple sources",
                "count": data["count"],
                "risk_score": int(data["risk_score"] / data["count"]) if data["risk_score"] > 0 else 0
            })
    
    top_threats = sorted(top_threats, key=lambda x: x["count"], reverse=True)[:5]
    
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
        top_threats=top_threats,
        daily_breakdown=daily_breakdown
    )


@router.post("/{job_id}/start")
async def start_upload_analysis(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start analysis for a pending upload job."""
    from app.models.analysis_job import AnalysisJob
    
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID")
    
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_uuid,
            AnalysisJob.user_id == current_user.id
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    if job.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Job is not pending (current status: {job.status})"
        )
    
    job.status = "queued"
    await db.commit()
    
    analyze_email_task.delay(str(job.id), None, str(current_user.id))
    
    return {"message": "Analysis started", "job_id": job_id}
