"""
Analysis Router

This module handles email analysis endpoints including:
- File upload for analysis
- Get analysis results
- Analysis history
- Report download
"""

import io
import logging
import os
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional, List

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


async def _get_analysis_data_dict(
    job,
    mongo_id: str,
    db: AsyncSession
) -> Optional[dict]:
    """
    Get full analysis data as a dictionary.
    Used by both the get_analysis endpoint and PDF download.
    """
    mongodb = get_mongodb_database()
    detailed_result = None
    
    if mongo_id:
        detailed_result = await mongodb.analysis_results.find_one({"_id": mongo_id})
        if not detailed_result:
            detailed_result = await mongodb.analysis_results.find_one({"job_id": mongo_id})
    
    if not detailed_result:
        return None
    
    # Extract email metadata
    email_meta_raw = detailed_result.get("email_metadata", {})
    recipient_val = email_meta_raw.get("recipient", [])
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
    
    # Extract ML prediction
    ml_prediction = detailed_result.get("ml_prediction", {})
    ml_details = None
    if ml_prediction:
        ml_details = {
            "is_phishing": ml_prediction.get("is_phishing"),
            "phishing_probability": ml_prediction.get("phishing_probability"),
            "safe_probability": ml_prediction.get("safe_probability"),
            "category": ml_prediction.get("category"),
            "confidence": ml_prediction.get("confidence"),
            "model_version": ml_prediction.get("model_version"),
            "features_used": ml_prediction.get("features_used")
        }
    
    # Normalize threat intelligence
    threat_intel = _normalize_threat_intelligence(detailed_result.get("threat_intelligence", {}))
    
    # Extract URL-specific TI scores from threat_intel indicators
    # Also consider original_url for proper domain matching after redirects
    url_ti_scores = {}
    url_ti_domains = {}
    for ind in threat_intel.get("indicators", []):
        if ind.get("indicator_type") in ("url_reputation", "url_analysis", "phishing_check"):
            indicator_value = ind.get("indicator_value", "")
            original_url = ind.get("original_url", "")
            
            # Store the indicator data
            ti_data = {
                "score": ind.get("score", 0),
                "risk_level": ind.get("risk_level", "none"),
                "api_name": ind.get("api_name", ""),
                "original_url": original_url
            }
            
            # Store by exact value
            if indicator_value:
                url_ti_scores[indicator_value] = ti_data
            
            # Also store original URL for matching
            if original_url:
                url_ti_scores[original_url] = ti_data
            
            # Extract and store domains from both indicator_value and original_url
            from urllib.parse import urlparse
            for url_to_parse in [indicator_value, original_url]:
                if not url_to_parse:
                    continue
                try:
                    if not url_to_parse.startswith('http'):
                        url_to_parse = 'https://' + url_to_parse
                    parsed = urlparse(url_to_parse)
                    ti_domain = parsed.netloc.lower()
                    if ti_domain:
                        url_ti_domains[ti_domain] = ti_data
                except Exception:
                    pass
    
    # Get URL expansions from threat_intel
    url_expansions = threat_intel.get("url_expansions", {})
    
    # Normalize links with threat intelligence scores
    links_analyzed = detailed_result.get("links_analyzed", [])
    links_normalized = []
    for link in links_analyzed:
        if isinstance(link, dict):
            url = link.get("url", "")
            domain = link.get("domain", "")
            
            # Extract domain from URL if not present
            if not domain and url:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                except Exception:
                    pass
            
            # Try to find a matching TI score
            ti_score = link.get("risk_score", 0)
            ti_risk = "none"
            expansion = url_expansions.get(url, {})
            
            # Helper function to extract base domain (e.g., google.com from mail.google.com)
            def get_base_domain(domain):
                if not domain:
                    return None
                parts = domain.split('.')
                # Common multi-part TLDs
                multi_part_tlds = {
                    'co.uk', 'co.jp', 'co.nz', 'co.in', 'co.za', 'co.kr',
                    'com.au', 'com.br', 'com.mx', 'com.cn', 'com.sg',
                    'net.au', 'org.uk', 'org.cn', 'ac.uk', 'gov.uk',
                    'ne.jp', 'or.jp', 'ac.jp', 'ad.jp', 'gr.jp'
                }
                if len(parts) >= 3:
                    tld = '.'.join(parts[-2:])
                    if tld in multi_part_tlds:
                        return '.'.join(parts[-3:])
                return '.'.join(parts[-2:]) if len(parts) >= 2 else domain
            
            # Helper function to find best domain match (including subdomains)
            def find_best_domain_match(link_domain, ti_domains):
                if not link_domain:
                    return None
                
                # Exact match
                if link_domain in ti_domains:
                    return ti_domains[link_domain]
                
                # Get base domains for comparison
                link_base = get_base_domain(link_domain)
                
                # Check TI domains for base domain match
                for ti_domain, ti_data in ti_domains.items():
                    ti_base = get_base_domain(ti_domain)
                    
                    # Base domains match
                    if link_base and ti_base and link_base == ti_base:
                        return ti_data
                    
                    # TI domain is parent of link
                    if link_domain.endswith('.' + ti_domain):
                        return ti_data
                    
                    # Link domain is parent of TI domain
                    if ti_domain.endswith('.' + link_domain):
                        return ti_data
                
                return None
            
            # Check direct URL match
            if url in url_ti_scores:
                ti_score = int(url_ti_scores[url].get("score", 0) * 100)
                ti_risk = url_ti_scores[url].get("risk_level", "none")
            # Check domain match (including parent domain)
            else:
                match = find_best_domain_match(domain, url_ti_domains)
                if match:
                    ti_score = int(match.get("score", 0) * 100)
                    ti_risk = match.get("risk_level", "none")
                # Check expanded URL match
                elif expansion.get("expanded"):
                    expanded = expansion.get("expanded", "")
                    if expanded in url_ti_scores:
                        ti_score = int(url_ti_scores[expanded].get("score", 0) * 100)
                        ti_risk = url_ti_scores[expanded].get("risk_level", "none")
                    else:
                        try:
                            parsed_exp = urlparse(expanded)
                            exp_domain = parsed_exp.netloc.lower()
                            exp_match = find_best_domain_match(exp_domain, url_ti_domains)
                            if exp_match:
                                ti_score = int(exp_match.get("score", 0) * 100)
                                ti_risk = exp_match.get("risk_level", "none")
                        except Exception:
                            pass
            
            # Set status based on TI results
            link_status = link.get("status", "unknown")
            if ti_risk in ("high", "critical"):
                link_status = "suspicious"
            elif ti_risk == "medium":
                link_status = "caution"
            elif ti_risk == "none" and link_status == "unknown":
                link_status = "safe"
            
            links_normalized.append({
                "url": url,
                "display_text": link.get("display_text"),
                "domain": domain,
                "ip_address": link.get("ip_address"),
                "status": link_status,
                "risk_score": ti_score,
                "reputation_score": link.get("reputation_score"),
                "category": link.get("category"),
                "redirects_to": expansion.get("expanded"),
                "is_shortened": link.get("is_shortened", False),
                "is_ip_based": link.get("is_ip_based", False),
                "threat_intelligence": link.get("threat_intelligence", {})
            })
    
    # Extract hash-specific TI scores from threat_intel indicators
    hash_ti_scores = {}
    for ind in threat_intel.get("indicators", []):
        if ind.get("indicator_type") == "file_reputation":
            indicator_value = ind.get("indicator_value", "")
            if indicator_value:
                hash_ti_scores[indicator_value] = {
                    "score": ind.get("score", 0),
                    "risk_level": ind.get("risk_level", "none"),
                    "api_name": ind.get("api_name", ""),
                    "details": ind.get("details", {})
                }
    
    # Normalize attachments with threat intelligence scores
    attachments_analyzed = detailed_result.get("attachments_analyzed", [])
    attachments_normalized = []
    for att in attachments_analyzed:
        if isinstance(att, dict):
            hash_sha256 = att.get("hash_sha256", "")
            
            # Try to find matching TI score by hash
            att_score = att.get("risk_score", 0)
            att_risk = "none"
            ti_details = {}
            if hash_sha256 in hash_ti_scores:
                ti_data = hash_ti_scores[hash_sha256]
                att_score = int(ti_data.get("score", 0) * 100)
                att_risk = ti_data.get("risk_level", "none")
                ti_details = ti_data.get("details", {})
            
            # Set status based on TI results
            att_status = att.get("status", "unknown")
            if att_risk in ("high", "critical"):
                att_status = "suspicious"
            elif att_risk == "medium":
                att_status = "caution"
            elif att_risk == "none" and att_status == "unknown":
                att_status = "safe"
            
            attachments_normalized.append({
                "filename": att.get("filename", ""),
                "content_type": att.get("content_type", ""),
                "size": att.get("size", 0),
                "hash_md5": att.get("hash_md5"),
                "hash_sha1": att.get("hash_sha1"),
                "hash_sha256": hash_sha256,
                "status": att_status,
                "risk_score": att_score,
                "threat_intelligence": att.get("threat_intelligence", {}),
                "ti_details": ti_details,
                "is_executable": att.get("is_executable", False),
                "is_script": att.get("is_script", False)
            })
    
    # Build the full dict
    return {
        "id": str(job.id),
        "source_type": job.source_type,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_step": job.current_step,
        "email_metadata": {
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
        "risk_score": job.risk_score,
        "threat_category": job.threat_category,
        "confidence": job.confidence,
        "findings": detailed_result.get("findings", []),
        "findings_count": job.findings_count,
        "critical_findings": job.critical_findings,
        "high_findings": job.high_findings,
        "medium_findings": job.medium_findings,
        "low_findings": job.low_findings,
        "links_analyzed": links_normalized,
        "urls_analyzed": links_normalized,
        "attachments_analyzed": attachments_normalized,
        "risk_factors": detailed_result.get("risk_factors"),
        "ml_analysis": ml_details,
        "threat_intelligence": threat_intel,
        "report_generated": job.report_generated,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "duration_seconds": job.duration_seconds,
        "email_headers": detailed_result.get("email_headers", {}),
        "recommendations": detailed_result.get("recommendations", []),
    }


def _normalize_threat_intelligence(ti_data: dict) -> dict:
    """
    Normalize threat intelligence data for frontend consumption.
    
    Handles both old format (indicators as strings) and new format (indicators as objects).
    """
    if not ti_data:
        return {
            'overall_risk_score': 0,
            'risk_category': 'unknown',
            'confidence': 0,
            'indicators': [],
            'warnings': []
        }
    
    indicators = ti_data.get('indicators', [])
    
    # Check if indicators are in old format (strings) and convert to objects
    if indicators and isinstance(indicators, list):
        first_ind = indicators[0] if indicators else None
        if isinstance(first_ind, str):
            # Old format: convert strings to objects
            normalized_indicators = []
            for ind_str in indicators:
                if not isinstance(ind_str, str):
                    continue
                
                # Parse string format: "api_name: description"
                parts = ind_str.split(':', 1)
                api_name = parts[0].strip() if parts else 'unknown'
                description = parts[1].strip() if len(parts) > 1 else ''
                
                # Map API names
                display_name = api_name
                indicator_type = 'reputation'
                
                if api_name == 'abuseipdb':
                    display_name = 'abuseipdb'
                elif api_name in ('whoisjson', 'rdap'):
                    display_name = 'rdap'
                    indicator_type = 'domain_age'
                elif api_name == 'abuseipdb_domain':
                    display_name = 'abuseipdb_domain'
                elif api_name in ('phishtank', 'urlscan'):
                    display_name = 'phishtank'
                    indicator_type = 'phishing_check'
                elif 'virustotal' in api_name:
                    display_name = 'virustotal_url'
                    indicator_type = 'url_reputation'
                
                # Determine risk level from description
                risk_level = 'none'
                if 'high risk' in description.lower():
                    risk_level = 'high'
                elif 'medium' in description.lower():
                    risk_level = 'medium'
                elif 'low' in description.lower():
                    risk_level = 'low'
                
                normalized_indicators.append({
                    'api_name': display_name,
                    'indicator_type': indicator_type,
                    'indicator_value': '',
                    'details': {'description': description},
                    'score': 1.0 if risk_level in ('high', 'critical') else 0.5 if risk_level == 'medium' else 0.0,
                    'risk_level': risk_level
                })
            
            indicators = normalized_indicators
        elif isinstance(first_ind, dict):
            # New format - ensure all required fields exist
            normalized_indicators = []
            for ind in indicators:
                if isinstance(ind, dict):
                    normalized_indicators.append({
                        'api_name': ind.get('api_name', 'unknown'),
                        'indicator_type': ind.get('indicator_type', 'reputation'),
                        'indicator_value': ind.get('indicator_value', ''),
                        'details': ind.get('details', {}),
                        'score': ind.get('score', 0),
                        'risk_level': ind.get('risk_level', 'none')
                    })
            indicators = normalized_indicators
    
    return {
        'overall_risk_score': ti_data.get('overall_risk_score', 0),
        'risk_category': ti_data.get('risk_category', ti_data.get('category', 'unknown')),
        'confidence': ti_data.get('confidence', 0),
        'indicators': indicators if isinstance(indicators, list) else [],
        'warnings': ti_data.get('warnings', [])
    }


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
            category_map = {"caution": "suspicious", "unknown": "suspicious", "safe": "safe"}
            category_raw = category_map.get(category_raw.lower(), "suspicious")
        
        # Extract threat intelligence data
        raw_ti = mongo_result.get("threat_intelligence", {})
        threat_intelligence = _normalize_threat_intelligence(raw_ti)
        
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
            completed_at=mongo_result.get("created_at"),
            threat_intelligence=threat_intelligence
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
                ml_details = {
                    "is_phishing": ml_prediction.get("is_phishing"),
                    "phishing_probability": ml_prediction.get("phishing_probability"),
                    "safe_probability": ml_prediction.get("safe_probability"),
                    "category": ml_prediction.get("category"),
                    "confidence": ml_prediction.get("confidence"),
                    "model_version": ml_prediction.get("model_version"),
                    "features_used": ml_prediction.get("features_used")
                }
                detailed_result["ml_analysis"] = ml_details
            
            # Extract threat intelligence data
            threat_intelligence = _normalize_threat_intelligence(detailed_result.get("threat_intelligence", {}))
    
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
        threat_intelligence=threat_intelligence if detailed_result else None,
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
    
    from app.database import get_mongodb_database
    
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
    """Download analysis report as PDF."""
    from fastapi.responses import StreamingResponse
    from app.services.report_service import report_service
    
    if not analysis_id or analysis_id in ('None', 'null', 'undefined', ''):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis ID"
        )
    
    try:
        UUID(analysis_id)
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
    
    mongo_id = job.mongodb_result_id.replace("-", "") if job.mongodb_result_id else None
    analysis_doc = await _get_analysis_data_dict(job, mongo_id, db)
    
    if not analysis_doc:
        analysis_doc = {
            "id": str(job.id),
            "risk_score": job.risk_score or 0,
            "threat_category": job.threat_category or "Unknown",
            "confidence": job.confidence or 0.85,
            "email_metadata": {
                "sender": job.file_name or "Unknown",
                "subject": job.file_name or "Email Analysis Report",
                "date": job.created_at
            },
            "findings": [],
            "threat_intelligence": {"overall_risk_score": 0, "indicators": [], "warnings": []},
            "links_analyzed": [],
            "urls_analyzed": [],
            "attachments_analyzed": [],
            "recommendations": [],
            "risk_factors": {},
            "created_at": job.created_at
        }
    
    pdf_bytes = report_service.generate_analysis_pdf(analysis_doc, show_sensitive=False)
    
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
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=phishcatcher-report-{analysis_id}.pdf"}
    )


@router.get("/reports/weekly", response_model=WeeklyReport)
async def get_weekly_report(
    week_start: Optional[datetime] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get analysis report for a custom date range or week."""
    from datetime import timedelta
    from sqlalchemy import or_, and_
    
    if start_date and end_date:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
    elif week_start:
        start_dt = week_start
        end_dt = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    else:
        start_dt = datetime.utcnow() - timedelta(days=7)
        end_dt = datetime.utcnow()
    
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == current_user.id)
        .where(AnalysisJob.status == "completed")
        .where(
            or_(
                and_(
                    AnalysisJob.completed_at.isnot(None),
                    AnalysisJob.completed_at >= start_dt,
                    AnalysisJob.completed_at <= end_dt
                ),
                and_(
                    AnalysisJob.completed_at.is_(None),
                    AnalysisJob.created_at >= start_dt,
                    AnalysisJob.created_at <= end_dt
                )
            )
        )
        .order_by(desc(AnalysisJob.completed_at))
    )
    jobs = result.scalars().all()
    
    total_analyses = len(jobs)
    # Use risk_score like frontend: >=70 = threat, >=40 and <70 = suspicious, <40 = safe
    phishing_detected = sum(1 for j in jobs if j.threat_category in ["phishing", "malware"] and j.risk_score and j.risk_score >= 70)
    malware_detected = sum(1 for j in jobs if j.threat_category == "malware" and j.risk_score and j.risk_score >= 70)
    suspicious_detected = sum(1 for j in jobs if j.risk_score and j.risk_score >= 40 and j.risk_score < 70)
    safe_emails = sum(1 for j in jobs if j.risk_score and j.risk_score < 40)
    
    risk_scores = [j.risk_score for j in jobs if j.risk_score is not None]
    average_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    
    # Generate daily breakdown for the period
    daily_breakdown = []
    current_date = start_dt.date()
    period_end_date = end_dt.date()
    while current_date <= period_end_date:
        day_name = current_date.strftime('%a')
        day_jobs = [j for j in jobs if 
            (j.completed_at and j.completed_at.date() == current_date) or
            (not j.completed_at and j.created_at and j.created_at.date() == current_date)
        ]
        daily_breakdown.append({
            "day": day_name,
            "analyzed": len(day_jobs),
            "threats": sum(1 for j in day_jobs if j.risk_score and j.risk_score >= 70),
            "suspicious": sum(1 for j in day_jobs if j.risk_score and j.risk_score >= 40 and j.risk_score < 70)
        })
        current_date += timedelta(days=1)
    
    threats_by_category = {}
    for j in jobs:
        if j.risk_score and j.risk_score >= 70:
            cat = j.threat_category or "threat"
            if cat not in threats_by_category:
                threats_by_category[cat] = {"count": 0, "risk_score": 0}
            threats_by_category[cat]["count"] += 1
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
        week_start=start_dt,
        week_end=end_dt,
        period_start=start_dt.isoformat(),
        period_end=end_dt.isoformat(),
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


@router.get("/reports/batch")
async def get_batch_report(
    ids: List[str] = Query(..., description="List of analysis IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get batch report for selected analyses."""
    if not ids:
        raise HTTPException(status_code=400, detail="No analysis IDs provided")
    
    if len(ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 analyses allowed")
    
    # Fetch analyses
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id.in_([UUID(i) for i in ids if i]),
            AnalysisJob.user_id == current_user.id,
            AnalysisJob.status == "completed"
        )
    )
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(status_code=404, detail="No analyses found")
    
    total_analyses = len(jobs)
    phishing_detected = sum(1 for j in jobs if j.threat_category == "phishing")
    malware_detected = sum(1 for j in jobs if j.threat_category == "malware")
    suspicious_detected = sum(1 for j in jobs if j.threat_category == "suspicious")
    safe_emails = sum(1 for j in jobs if j.threat_category == "safe")
    
    # Daily breakdown
    daily_map = {}
    for j in jobs:
        if j.completed_at:
            day = j.completed_at.strftime('%a')
            if day not in daily_map:
                daily_map[day] = {"day": day, "analyzed": 0, "threats": 0}
            daily_map[day]["analyzed"] += 1
            if j.threat_category in ["phishing", "malware"]:
                daily_map[day]["threats"] += 1
    
    daily_breakdown = list(daily_map.values())[:7]
    
    return {
        "total_analyses": total_analyses,
        "phishing_detected": phishing_detected,
        "malware_detected": malware_detected,
        "suspicious_detected": suspicious_detected,
        "safe_emails": safe_emails,
        "daily_breakdown": daily_breakdown,
    }


@router.get("/reports/summary/download")
async def download_summary_report(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download summary report as PDF for a date range."""
    from fastapi.responses import StreamingResponse
    from app.services.report_service import report_service
    from sqlalchemy import or_, and_
    
    if not start_date or not end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date and end date are required"
        )
    
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)"
        )
    
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == current_user.id)
        .where(AnalysisJob.status == "completed")
        .where(
            or_(
                and_(
                    AnalysisJob.completed_at.isnot(None),
                    AnalysisJob.completed_at >= start_dt,
                    AnalysisJob.completed_at <= end_dt
                ),
                and_(
                    AnalysisJob.completed_at.is_(None),
                    AnalysisJob.created_at >= start_dt,
                    AnalysisJob.created_at <= end_dt
                )
            )
        )
        .order_by(desc(AnalysisJob.completed_at))
    )
    jobs = result.scalars().all()
    
    logger.info(f"Summary report: date range {start_date} to {end_date}, found {len(jobs)} jobs")
    for j in jobs[:3]:
        logger.info(f"  Job: id={j.id}, status={j.status}, completed_at={j.completed_at}, created_at={j.created_at}, threat_category={j.threat_category}")
    
    total_analyses = len(jobs)
    threats = sum(1 for j in jobs if j.risk_score and j.risk_score >= 70)
    phishing_detected = sum(1 for j in jobs if j.threat_category == "phishing" and j.risk_score and j.risk_score >= 70)
    malware_detected = sum(1 for j in jobs if j.threat_category == "malware" and j.risk_score and j.risk_score >= 70)
    suspicious_detected = sum(1 for j in jobs if j.risk_score and j.risk_score >= 40 and j.risk_score < 70)
    safe_emails = sum(1 for j in jobs if not j.risk_score or j.risk_score < 40)
    
    daily_map = {}
    for j in jobs:
        date_to_use = j.completed_at or j.created_at
        if date_to_use:
            day = date_to_use.strftime('%Y-%m-%d')
            if day not in daily_map:
                daily_map[day] = {"day": day, "analyzed": 0, "threats": 0, "suspicious": 0}
            daily_map[day]["analyzed"] += 1
            if j.threat_category in ["phishing", "malware"]:
                daily_map[day]["threats"] += 1
            elif j.threat_category in ["suspicious", "caution"]:
                daily_map[day]["suspicious"] += 1
    
    daily_breakdown = sorted(list(daily_map.values()), key=lambda x: x["day"])
    
    from app.database import get_mongodb_database
    mongodb = get_mongodb_database()
    
    job_data_map = {}
    for j in jobs:
        job_data_map[str(j.id)] = {
            "subject": j.file_name or "Unknown",
            "sender": "Unknown",
        }
    
    found_count = 0
    for j in jobs:
        jid = str(j.id)
        mongo_id = j.mongodb_result_id
        
        if mongo_id:
            doc = await mongodb.analysis_results.find_one({"_id": mongo_id})
            if doc:
                email_meta = doc.get('email_metadata', {})
                sender = email_meta.get('sender', email_meta.get('from', ''))
                subject = email_meta.get('subject', '')
                if sender:
                    job_data_map[jid]['sender'] = sender
                if subject:
                    job_data_map[jid]['subject'] = subject
                found_count += 1
                continue
        
        doc = await mongodb.analysis_results.find_one({"job_id": jid})
        if not doc:
            clean_id = jid.replace('-', '')
            doc = await mongodb.analysis_results.find_one({"job_id": clean_id})
        
        if doc:
            email_meta = doc.get('email_metadata', {})
            sender = email_meta.get('sender', email_meta.get('from', ''))
            subject = email_meta.get('subject', '')
            if sender:
                job_data_map[jid]['sender'] = sender
            if subject:
                job_data_map[jid]['subject'] = subject
            found_count += 1
    
    logger.info(f"Summary report: MongoDB lookup found {found_count} matches out of {len(jobs)} jobs")
    if found_count > 0:
        for jid, data in list(job_data_map.items())[:3]:
            logger.info(f"  {jid}: sender={data['sender']}")
    
    top_threats = []
    threat_jobs = [j for j in jobs if j.risk_score and j.risk_score >= 70]
    for j in threat_jobs[:10]:
        jid = str(j.id)
        data = job_data_map.get(jid, {"subject": j.file_name or "Unknown", "sender": "Unknown"})
        top_threats.append({
            "subject": data.get("subject", j.file_name or "Unknown"),
            "sender": data.get("sender", "Unknown"),
            "risk_score": j.risk_score or 0,
            "category": j.threat_category or "Unknown"
        })
    
    sender_map = {}
    for j in jobs:
        jid = str(j.id)
        sender = job_data_map.get(jid, {}).get("sender", "Unknown")
        if sender not in sender_map:
            sender_map[sender] = 0
        sender_map[sender] += 1
    
    top_senders = [{"sender": s, "count": c} for s, c in sorted(sender_map.items(), key=lambda x: -x[1])[:10]]
    
    report_data = {
        "total_analyses": total_analyses,
        "threats": threats,
        "phishing_detected": phishing_detected,
        "malware_detected": malware_detected,
        "suspicious_detected": suspicious_detected,
        "safe_emails": safe_emails,
        "daily_breakdown": daily_breakdown,
        "top_threats": top_threats,
        "top_senders": top_senders,
    }
    
    pdf_bytes = report_service.generate_summary_pdf(report_data, start_date, end_date)
    
    filename = f"phishcatcher-summary-{start_date}-to-{end_date}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/reports/combined/download")
async def download_combined_report(
    body: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download combined PDF report for multiple analyses."""
    from fastapi.responses import StreamingResponse
    from app.services.report_service import report_service
    from app.models.analysis_job import AnalysisJob
    
    ids = body.get("ids", [])
    
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No analysis IDs provided")
    
    if len(ids) > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 5 analyses can be combined")
    
    analyses = []
    start_date = None
    end_date = None
    
    for analysis_id in ids:
        try:
            UUID(analysis_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid analysis ID: {analysis_id}")
        
        result = await db.execute(
            select(AnalysisJob).where(AnalysisJob.id == analysis_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis not found: {analysis_id}")
        
        if str(job.user_id) != str(current_user.id) and not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis not completed: {analysis_id}"
            )
        
        mongodb = get_mongodb_database()
        
        analysis_doc = None
        lookup_reason = "not_tried"
        
        # Try multiple lookup strategies
        search_ids = [analysis_id, job.mongodb_result_id]
        # Clean UUID (remove dashes)
        clean_id = analysis_id.replace('-', '')
        if clean_id != analysis_id:
            search_ids.append(clean_id)
        
        for search_id in search_ids:
            if not search_id:
                continue
            # Try _id
            analysis_doc = await mongodb.analysis_results.find_one({"_id": search_id})
            if analysis_doc:
                lookup_reason = f"found_by_id:{search_id}"
                break
            # Try job_id
            analysis_doc = await mongodb.analysis_results.find_one({"job_id": search_id})
            if analysis_doc:
                lookup_reason = f"found_by_job_id:{search_id}"
                break
        
        # If still not found, search by job_id across all documents
        if not analysis_doc:
            analysis_doc = await mongodb.analysis_results.find_one({"job_id": analysis_id})
            if analysis_doc:
                lookup_reason = f"found_by_job_id_fallback:{analysis_id}"
        
        if analysis_doc:
            logger.info(f"Combined report: MongoDB lookup for {analysis_id}: {lookup_reason}")
        else:
            logger.warning(f"Combined report: MongoDB NOT FOUND for {analysis_id}, mongodb_result_id={job.mongodb_result_id}")
        
        if analysis_doc:
            analysis_doc = dict(analysis_doc)
            if "_id" in analysis_doc:
                del analysis_doc["_id"]
            if "user_id" in analysis_doc:
                del analysis_doc["user_id"]
        else:
            analysis_doc = {
                "id": str(job.id),
                "job_id": str(job.id),
                "risk_score": job.risk_score or 0,
                "risk_assessment": {
                    "overall_score": job.risk_score or 0,
                    "category": job.threat_category or "Unknown",
                    "confidence": job.confidence,
                },
                "confidence": job.confidence,
                "source_type": job.source_type,
                "file_name": job.file_name,
                "email_metadata": {
                    "sender": job.file_name or "Unknown",
                    "subject": job.file_name or "Email Analysis Report",
                    "date": str(job.created_at) if job.created_at else None
                },
                "findings_count": job.findings_count or 0,
                "critical_findings": job.critical_findings or 0,
                "high_findings": job.high_findings or 0,
                "medium_findings": job.medium_findings or 0,
                "low_findings": job.low_findings or 0,
                "findings": [],
                "links_analyzed": [],
                "attachments_analyzed": [],
            }
        
        if job.created_at:
            if not start_date or job.created_at < start_date:
                start_date = job.created_at
            if not end_date or job.created_at > end_date:
                end_date = job.created_at
        
        analyses.append(analysis_doc)
        
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            action=AuditAction.REPORT_DOWNLOADED,
            resource_type="analysis",
            resource_id=analysis_id,
            ip_address=None,
            status="success",
            details={"report_type": "combined", "analysis_count": len(analyses)},
        )
        db.add(audit_log)
    
    await db.commit()
    
    start_str = start_date.strftime('%Y-%m-%d') if start_date else datetime.now().strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d') if end_date else datetime.now().strftime('%Y-%m-%d')
    
    pdf_bytes = report_service.generate_combined_pdf(analyses, start_str, end_str)
    
    filename = f"phishcatcher-combined-{datetime.now().strftime('%Y-%m-%d')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
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
