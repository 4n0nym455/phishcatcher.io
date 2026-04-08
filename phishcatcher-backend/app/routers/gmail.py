"""
Gmail Integration Router

This module provides API endpoints for Gmail integration including:
- OAuth authentication flow
- Email fetching and analysis
- Gmail account management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, Body, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging

from app.database import get_db
from app.models.user import User
from app.models.analysis_job import AnalysisJob
from app.routers.auth import get_current_active_user
from app.services.gmail_service import gmail_service
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])

@router.get("/auth/url")
async def get_gmail_auth_url(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Get Gmail OAuth authorization URL for current user."""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA must be enabled before connecting Gmail. Enable MFA in Settings first."
        )
    try:
        auth_url = gmail_service.get_auth_url(str(current_user.id), current_user.email)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting Gmail auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Gmail authorization URL"
        )

@router.post("/callback")
async def gmail_auth_callback_post(
    code: str = Body(...),
    state: str = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback from frontend."""
    try:
        result = await gmail_service.handle_oauth_callback(code, state)
        if result.get("success"):
            return {"success": True, "email": result.get("email")}
        else:
            return {"success": False, "error": result.get("error", "Failed to connect Gmail")}
    except Exception as e:
        logger.error(f"Gmail OAuth callback error: {e}")
        return {"success": False, "error": str(e)}

@router.get("/callback")
async def gmail_auth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback (redirect from Google)."""
    from fastapi.responses import HTMLResponse
    
    try:
        result = await gmail_service.handle_oauth_callback(code, state)
        if result.get("success"):
            email = result.get("email")
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Gmail Connected</title>
            </head>
            <body>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'gmail-connected', email: '{email}' }}, '*');
                    }}
                    window.close();
                    setTimeout(() => {{ window.close(); }}, 100);
                </script>
                <p>Gmail connected successfully! You can close this window.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html)
        else:
            html = """
            <!DOCTYPE html>
            <html>
            <body>
                <script>
                    if (window.opener) {
                        window.opener.postMessage({ type: 'gmail-error', error: 'Failed to connect Gmail' }, '*');
                    }
                    window.close();
                </script>
                <p>Failed to connect Gmail. Please try again.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html, status_code=400)
    except Exception as e:
        logger.error(f"Gmail OAuth callback error: {e}")
        html = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'gmail-error', error: '{str(e)}' }}, '*');
                }}
                window.close();
            </script>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=500)

@router.get("/status")
async def get_gmail_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get Gmail connection status for current user."""
    from app.database import get_mongodb_database
    
    mongodb = get_mongodb_database()
    queue = []
    emails_scanned = 0
    threats_found = 0
    
    async for q in mongodb.gmail_analysis_queue.find({"user_id": str(current_user.id)}):
        status = q.get("status", "pending")
        if status == "pending":
            queue.append({"message_id": q["message_id"], "subject": q.get("subject", ""), "from": q.get("from", "")})
        elif status == "completed":
            emails_scanned += 1
            if q.get("risk_score", 0) >= 40:
                threats_found += 1
    
    return {
        "connected": bool(current_user.gmail_credentials),
        "email": current_user.gmail_email,
        "connected_at": current_user.gmail_connected_at,
        "emails_scanned": emails_scanned,
        "threats_found": threats_found,
        "queued": queue
    }

@router.get("/queue")
async def get_gmail_queue(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get all items in the Gmail analysis queue with their status."""
    from app.database import get_mongodb_database
    
    mongodb = get_mongodb_database()
    
    pending = []
    processing = []
    completed = []
    
    async for q in mongodb.gmail_analysis_queue.find({"user_id": str(current_user.id)}).sort("created_at", -1):
        item = {
            "id": str(q["_id"]),
            "message_id": q["message_id"],
            "subject": q.get("subject", ""),
            "from": q.get("from", ""),
            "to": q.get("to", ""),
            "date": q.get("date"),
            "snippet": q.get("snippet", ""),
            "labels": q.get("labels", []),
            "status": q.get("status", "pending"),
            "created_at": q.get("created_at"),
            "completed_at": q.get("completed_at"),
            "analysis_id": q.get("analysis_id"),
            "risk_score": q.get("risk_score"),
            "error": q.get("error"),
        }
        status = q.get("status", "pending")
        if status == "pending":
            pending.append(item)
        elif status == "processing":
            processing.append(item)
        elif status == "completed":
            completed.append(item)
        elif status == "failed":
            completed.append(item)
    
    return {
        "pending": pending,
        "processing": processing,
        "completed": completed,
        "counts": {
            "pending": len(pending),
            "processing": len(processing),
            "completed": len(completed)
        }
    }

@router.post("/queue/{message_id}/process")
async def process_queue_item(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Process a specific queued email synchronously."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    
    from app.database import get_mongodb_database
    from datetime import datetime
    
    mongodb = get_mongodb_database()
    
    existing = await mongodb.gmail_analysis_queue.find_one({
        "user_id": str(current_user.id),
        "message_id": message_id
    })
    
    if existing and existing.get("status") == "completed":
        return {
            "message": "Email already analyzed",
            "analysis_id": existing.get("analysis_id")
        }
    
    await mongodb.gmail_analysis_queue.update_one(
        {"user_id": str(current_user.id), "message_id": message_id},
        {"$set": {"status": "processing", "started_at": datetime.utcnow()}}
    )
    
    try:
        result = await process_gmail_email_sync(str(current_user.id), message_id)
        
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": str(current_user.id), "message_id": message_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "analysis_id": str(result.get("_id")),
                "risk_score": result.get("risk_assessment", {}).get("overall_score"),
                "threat_category": result.get("risk_assessment", {}).get("category")
            }}
        )
        
        return {
            "message": "Analysis completed",
            "analysis_id": str(result.get("_id"))
        }
    except Exception as e:
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": str(current_user.id), "message_id": message_id},
            {"$set": {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error": str(e)
            }}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


async def process_gmail_email_sync(user_id: str, message_id: str) -> Dict[str, Any]:
    """Process a Gmail email synchronously (no Celery)."""
    from app.services.gmail_service import gmail_service
    from app.ml.email_parser import EmailParser
    from app.ml.risk_scorer import get_risk_scorer
    from app.services.threat_intel import get_threat_intel_service
    from app.database import get_mongodb_database
    from datetime import datetime
    import base64
    
    email_raw = await gmail_service.get_email_by_id(user_id, message_id)
    if not email_raw:
        raise Exception("Failed to fetch email from Gmail")
    
    raw_bytes = base64.urlsafe_b64decode(email_raw['raw'])
    
    parser = EmailParser(raw_bytes)
    parsed_email = parser.parse()
    
    risk_scorer = get_risk_scorer()
    analysis_result = risk_scorer.analyze(parsed_email)
    
    # Also run threat intelligence analysis
    sender_email = parsed_email.get("headers", {}).get("from", "")
    urls = [link.get("url", "") for link in parsed_email.get("links", [])]
    attachments = parsed_email.get("attachments", [])
    attachment_hashes = [att.get("sha256", "") for att in attachments if att.get("sha256")]
    threat_intel = get_threat_intel_service()
    ti_result = await threat_intel.analyze_email_threats(sender_email=sender_email, urls=urls, attachment_hashes=attachment_hashes)
    
    # Combine ML and TI scores
    ml_score = analysis_result.get("risk_score", 0) / 100.0
    ti_score = ti_result.get("overall_risk_score", 0) / 100.0
    final_score = (ml_score * 0.4 + ti_score * 0.6) if ti_score > 0 else ml_score
    
    mongodb = get_mongodb_database()
    detailed_result = {
        "job_id": message_id,
        "user_id": user_id,
        "source": "gmail",
        "gmail_message_id": message_id,
        "email_metadata": {
            "subject": parsed_email.get("headers", {}).get("subject"),
            "sender": parsed_email.get("headers", {}).get("from"),
            "recipient": parsed_email.get("headers", {}).get("to"),
            "date": parsed_email.get("headers", {}).get("date"),
            "message_id": parsed_email.get("headers", {}).get("message_id")
        },
        "risk_assessment": {
            "overall_score": int(final_score * 100),
            "category": analysis_result.get("threat_category", "suspicious"),
            "confidence": analysis_result.get("confidence", 0)
        },
        "findings": analysis_result.get("findings", []),
        "links_analyzed": parsed_email.get("links", []),
        "attachments_analyzed": parsed_email.get("attachments", []),
        "risk_factors": analysis_result.get("risk_factors", {}),
        "ml_prediction": analysis_result.get("ml_prediction", {}),
        "threat_intelligence": {
            "overall_risk_score": ti_result.get("overall_risk_score", 0),
            "indicators": ti_result.get("indicators", []),
            "warnings": ti_result.get("warnings", [])
        },
        "created_at": datetime.utcnow()
    }
    
    # Generate 32-char hex ID BEFORE insert
    import uuid
    analysis_id = uuid.uuid4().hex
    detailed_result["_id"] = analysis_id
    detailed_result["job_id"] = analysis_id
    
    try:
        await mongodb.analysis_results.insert_one(detailed_result)
    except Exception as e:
        logger.error(f"MongoDB insert failed: {e}")
        analysis_id = f"fallback_{message_id}_{int(datetime.utcnow().timestamp())}"
        detailed_result["_id"] = analysis_id
        detailed_result["job_id"] = message_id
    
    # Create PostgreSQL AnalysisJob record for history/dashboard/report integration
    try:
        from sqlalchemy import select
        from app.database import get_db
        async for db in get_db():
            # Find user by ID
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                job = AnalysisJob(
                    id=uuid.UUID(analysis_id),
                    user_id=user_id,
                    source_type="gmail",
                    external_message_id=message_id,
                    file_name=parsed_email.get("headers", {}).get("subject", "Gmail email"),
                    status="completed",
                    progress_percent=100,
                    current_step="Complete",
                    risk_score=analysis_result.get("risk_score", 0),
                    threat_category=analysis_result.get("threat_category", "suspicious"),
                    confidence=analysis_result.get("confidence", 0),
                    findings_count=len(analysis_result.get("findings", [])),
                    critical_findings=sum(1 for f in analysis_result.get("findings", []) if f.get("severity") == "critical"),
                    high_findings=sum(1 for f in analysis_result.get("findings", []) if f.get("severity") == "high"),
                    mongodb_result_id=analysis_id,
                    completed_at=datetime.utcnow()
                )
                db.add(job)
                await db.commit()
            break
    except Exception as job_err:
        logger.warning(f"Failed to create AnalysisJob for Gmail: {job_err}")
    
    return detailed_result

@router.post("/queue/clear")
async def clear_completed_queue(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Clear completed items from the queue."""
    from app.database import get_mongodb_database
    
    mongodb = get_mongodb_database()
    result = await mongodb.gmail_analysis_queue.delete_many({
        "user_id": str(current_user.id),
        "status": {"$in": ["completed", "failed"]}
    })
    
    return {
        "message": f"Cleared {result.deleted_count} items from queue"
    }

@router.delete("/queue/{message_id}")
async def delete_queue_item(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Delete a specific item from the queue."""
    from app.database import get_mongodb_database
    
    mongodb = get_mongodb_database()
    result = await mongodb.gmail_analysis_queue.delete_one({
        "user_id": str(current_user.id),
        "message_id": message_id
    })
    
    if result.deleted_count > 0:
        return {"message": "Item removed from queue"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in queue"
        )

@router.post("/disconnect")
async def disconnect_gmail(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Disconnect Gmail account for current user."""
    try:
        success = await gmail_service.disconnect_gmail(str(current_user.id))
        if success:
            return {"message": "Gmail account disconnected successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disconnect Gmail account"
            )
    except Exception as e:
        logger.error(f"Error disconnecting Gmail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect Gmail account"
        )

@router.get("/emails")
async def list_gmail_emails(
    max_results: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    q: str = None,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """List emails from connected Gmail account with optional search query."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    try:
        page_token = None if page == 1 else str((page - 1) * max_results)
        emails = await gmail_service.fetch_emails_paginated(
            str(current_user.id), 
            max_results=max_results,
            page_token=page_token,
            query=q
        )
        return emails
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch emails"
        )

@router.get("/emails/search")
async def search_gmail_emails(
    q: str,
    max_results: int = 50,
    page: int = 1,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Search emails using Gmail search syntax (advanced)."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query is required"
        )
    try:
        page_token = None if page == 1 else str((page - 1) * max_results)
        result = await gmail_service.search_emails(
            str(current_user.id),
            query=q,
            max_results=max_results,
            page_token=page_token
        )
        return result
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search emails"
        )

@router.get("/emails/filter")
async def filter_gmail_emails(
    filter_type: str = None,
    has_attachments: bool = None,
    date_from: str = None,
    date_to: str = None,
    from_address: str = None,
    subject: str = None,
    email_contains: str = None,
    max_results: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Filter emails using predefined or custom filters."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    try:
        query = gmail_service.build_filter_query(
            filter_type=filter_type,
            date_from=date_from,
            date_to=date_to,
            from_address=from_address,
            subject_keyword=subject,
            has_attachments=has_attachments,
            email_contains=email_contains
        )
        
        page_token = None if page == 1 else str((page - 1) * max_results)
        result = await gmail_service.fetch_emails_paginated(
            str(current_user.id),
            max_results=max_results,
            page_token=page_token,
            query=query
        )
        return {
            **result,
            "applied_filters": {
                "filter_type": filter_type,
                "has_attachments": has_attachments,
                "date_from": date_from,
                "date_to": date_to,
                "from_address": from_address,
                "subject": subject,
                "email_contains": email_contains
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to filter emails"
        )

@router.get("/emails/query-builder")
async def get_query_builder_suggestions(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get available Gmail search operators and example queries."""
    return {
        "operators": {
            "from": {"description": "Sender email or name", "example": "from:john@example.com"},
            "to": {"description": "Recipient email or name", "example": "to:me"},
            "subject": {"description": "Words in subject line", "example": "subject:invoice"},
            "has": {"description": "Has attachments or drive items", "example": "has:attachment"},
            "filename": {"description": "Attachment filename", "example": "filename:pdf"},
            "newer_than": {"description": "Emails newer than period", "example": "newer_than:7d"},
            "older_than": {"description": "Emails older than period", "example": "older_than:30d"},
            "after": {"description": "Emails after specific date", "example": "after:2024/01/01"},
            "before": {"description": "Emails before specific date", "example": "before:2024/12/31"},
            "is": {"description": "Email status", "example": "is:unread"},
            "label": {"description": "Gmail label", "example": "label:work"},
            "in": {"description": "Location in mailbox", "example": "in:inbox"},
            "cc": {"description": "Cc'd recipient", "example": "cc:boss@company.com"},
            "bcc": {"description": "Bcc'd recipient", "example": "bcc:secret@place.com"},
        },
        "examples": [
            {"query": "from:bank subject:urgent has:attachment", "label": "Bank phishing with attachment"},
            {"query": "subject:password newer_than:7d", "label": "Recent password reset"},
            {"query": "from:noreply has:attachment filename:pdf", "label": "Auto emails with PDFs"},
            {"query": "is:unread newer_than:30d -label:promotions", "label": "Unread (excluding promotions)"},
            {"query": "subject:(invoice OR payment) from:amazon", "label": "Invoice/payment from Amazon"},
        ]
    }

@router.post("/emails/queue")
async def queue_gmail_emails(
    message_ids: List[str] = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Add emails to analysis queue without starting analysis."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    
    from app.database import get_mongodb_database
    from datetime import datetime
    
    mongodb = get_mongodb_database()
    gmail_svc = gmail_service
    queued = []
    
    for msg_id in message_ids:
        existing = await mongodb.gmail_analysis_queue.find_one({
            "user_id": str(current_user.id),
            "message_id": msg_id
        })
        
        if existing:
            if existing.get("status") in ["pending", "processing"]:
                queued.append({"message_id": msg_id, "status": "already_queued"})
                continue
            elif existing.get("status") == "completed":
                queued.append({"message_id": msg_id, "status": "already_analyzed"})
                continue
        
        email_data = await gmail_svc.get_email_headers(str(current_user.id), msg_id)
        subject = ""
        sender = ""
        recipient = ""
        date = ""
        snippet = ""
        labels = []
        if email_data and 'payload' in email_data:
            for header in email_data['payload'].get('headers', []):
                if header.get('name') == 'Subject':
                    subject = header.get('value', '')
                elif header.get('name') == 'From':
                    sender = header.get('value', '')
                elif header.get('name') == 'To':
                    recipient = header.get('value', '')
                elif header.get('name') == 'Date':
                    date = header.get('value', '')
            snippet = email_data.get('snippet', '')
            labels = email_data.get('labelIds', [])
        
        queue_doc = {
            "user_id": str(current_user.id),
            "message_id": msg_id,
            "subject": subject,
            "from": sender,
            "to": recipient,
            "date": date,
            "snippet": snippet,
            "labels": labels,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        await mongodb.gmail_analysis_queue.insert_one(queue_doc)
        queued.append({"message_id": msg_id, "status": "queued"})
    
    queued_count = sum(1 for r in queued if r.get("status") == "queued")
    return {
        "message": f"{queued_count} emails added to queue",
        "queued": queued
    }


@router.post("/emails/analyze")
async def analyze_gmail_emails(
    message_ids: List[str] = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Analyze selected emails synchronously."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    try:
        from app.database import get_mongodb_database
        from datetime import datetime
        
        mongodb = get_mongodb_database()
        
        gmail_svc = gmail_service
        results = []
        for msg_id in message_ids:
            email_data = await gmail_svc.get_email_headers(str(current_user.id), msg_id)
            subject = ""
            sender = ""
            if email_data and 'payload' in email_data:
                for header in email_data['payload'].get('headers', []):
                    if header.get('name') == 'Subject':
                        subject = header.get('value', '')
                    elif header.get('name') == 'From':
                        sender = header.get('value', '')
            
            queue_doc = {
                "user_id": str(current_user.id),
                "message_id": msg_id,
                "subject": subject,
                "from": sender,
                "status": "processing",
                "created_at": datetime.utcnow(),
                "started_at": datetime.utcnow()
            }
            await mongodb.gmail_analysis_queue.insert_one(queue_doc)
            
            try:
                result = await process_gmail_email_sync(str(current_user.id), msg_id)
                
                await mongodb.gmail_analysis_queue.update_one(
                    {"user_id": str(current_user.id), "message_id": msg_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "analysis_id": str(result.get("_id")),
                        "risk_score": result.get("risk_assessment", {}).get("overall_score"),
                        "threat_category": result.get("risk_assessment", {}).get("category")
                    }}
                )
                
                results.append({
                    "message_id": msg_id,
                    "status": "completed",
                    "analysis_id": str(result.get("_id"))
                })
            except Exception as email_err:
                await mongodb.gmail_analysis_queue.update_one(
                    {"user_id": str(current_user.id), "message_id": msg_id},
                    {"$set": {
                        "status": "failed",
                        "completed_at": datetime.utcnow(),
                        "error": str(email_err)
                    }}
                )
                results.append({
                    "message_id": msg_id,
                    "status": "failed",
                    "error": str(email_err)
                })
        
        completed = sum(1 for r in results if r.get("status") == "completed")
        return {
            "message": f"{completed}/{len(results)} emails analyzed successfully",
            "results": results
        }
    except Exception as e:
        logger.error(f"Error analyzing emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze emails"
        )

@router.post("/emails/{message_id}/safe")
async def mark_email_safe(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Mark email as safe (not phishing)."""
    try:
        success = await gmail_service.mark_as_safe(str(current_user.id), message_id)
        if success:
            return {"message": "Email marked as safe"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to mark email as safe"
            )
    except Exception as e:
        logger.error(f"Error marking email as safe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark email as safe"
        )

@router.post("/emails/{message_id}/phishing")
async def report_phishing(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Report email as phishing."""
    try:
        success = await gmail_service.report_phishing(str(current_user.id), message_id)
        if success:
            return {"message": "Email reported as phishing"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to report email as phishing"
            )
    except Exception as e:
        logger.error(f"Error reporting phishing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to report email as phishing"
        )
