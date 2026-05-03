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
from sqlalchemy import select
from typing import Dict, Any, List
import uuid
import asyncio
import logging

from app.database import get_db, get_db_session
from app.models.user import User
from app.models.analysis_job import AnalysisJob
from app.routers.auth import get_current_active_user
from app.services.gmail_service import gmail_service
from app.services.threat_intel import transform_ti_for_storage
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])

@router.get(
    "/auth/url",
    summary="Get Gmail OAuth URL",
    description="Returns the Google OAuth authorization URL. Requires MFA to be enabled first.",
)
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
        # force_new=True to allow adding any account, not pre-filled to current user
        auth_url = gmail_service.get_auth_url(str(current_user.id), current_user.email, force_new=True)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting Gmail auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Gmail authorization URL"
        )

@router.get(
    "/auth/url/reconnect/{account_id}",
    summary="Get Gmail reconnect URL",
    description="Returns an OAuth URL pre-filled with the account's email for reconnecting an existing Gmail account.",
)
async def get_gmail_reconnect_url(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Get Gmail OAuth authorization URL specifically for reconnecting an existing account.
    
    This pre-fills the email address so the user doesn't have to select the account again.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA must be enabled before connecting Gmail. Enable MFA in Settings first."
        )
    
    from app.models.email_provider import EmailProvider
    
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID"
        )
    
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == account_uuid,
            EmailProvider.user_id == current_user.id,
            EmailProvider.provider_type == "gmail"
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    try:
        # Use login_hint to pre-fill the email, force_new=False to reconnect existing account
        auth_url = gmail_service.get_auth_url(
            str(current_user.id), 
            account.email_address, 
            force_new=False
        )
        return {"auth_url": auth_url, "email": account.email_address}
    except Exception as e:
        logger.error(f"Error getting Gmail reconnect URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Gmail authorization URL"
        )

@router.post(
    "/callback",
    summary="Gmail OAuth callback (JSON)",
    description="Handles Gmail OAuth callback from the frontend via POST with code and state in the body.",
)
async def gmail_auth_callback_post(
    code: str = Body(...),
    state: str = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback from frontend."""
    try:
        result = await gmail_service.handle_oauth_callback(code, state, str(current_user.id), db)
        if result.get("success"):
            return {
                "success": True, 
                "email": result.get("email"), 
                "account_id": result.get("account_id"),
                "is_new": result.get("is_new", True)
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to connect Gmail")}
    except Exception as e:
        logger.error(f"Gmail OAuth callback error: {e}")
        return {"success": False, "error": str(e)}

@router.get(
    "/callback",
    summary="Gmail OAuth callback (redirect)",
    description="Handles the OAuth redirect from Google. Returns an HTML page that posts a message to the opener window and self-closes.",
)
async def gmail_auth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback (redirect from Google)."""
    from fastapi.responses import HTMLResponse
    
    try:
        # Pass state as user_id for the callback handler
        result = await gmail_service.handle_oauth_callback(code, state, state, db)
        if result.get("success"):
            email = result.get("email")
            is_new = result.get("is_new", True)
            
            if is_new:
                message = f"New Gmail account ({email}) added successfully!"
            else:
                message = f"Gmail account ({email}) reconnected successfully!"
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Gmail Connected</title>
                <style>
                    body {{ font-family: system-ui, sans-serif; padding: 40px; text-align: center; }}
                    .message {{ font-size: 18px; color: #10b981; margin-bottom: 20px; }}
                    .close-hint {{ color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'gmail-connected', email: '{email}', is_new: {str(is_new).lower()} }}, '*');
                    }}
                    window.close();
                    setTimeout(() => {{ window.close(); }}, 100);
                </script>
                <div class="message">{message}</div>
                <div class="close-hint">You can close this window.</div>
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

@router.get(
    "/status",
    summary="Get Gmail connection status",
    description="Returns connected Gmail accounts, pending analysis queue, and threat counts.",
)
async def get_gmail_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get Gmail connection status for current user."""
    from app.database import get_mongodb_database
    from app.models.email_provider import EmailProvider
    from sqlalchemy import select
    
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
            if q.get("risk_score", 0) >= 70:
                threats_found += 1
    
    # Get all connected email accounts from EmailProvider table
    account_list = []
    async with get_db_session() as db:
        # First check EmailProvider (new multi-account system)
        result = await db.execute(
            select(EmailProvider).where(
                EmailProvider.user_id == current_user.id,
                EmailProvider.provider_type == "gmail",
                EmailProvider.is_active == True
            )
        )
        email_providers = result.scalars().all()
        
        for acc in email_providers:
            account_list.append({
                "id": str(acc.id),
                "email": acc.email_address,
                "provider_name": acc.provider_name,
                "is_connected": acc.is_connected,
                "connected_at": acc.created_at.isoformat() if acc.created_at else None,
                "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
            })
    
    # Also check legacy User table fields (backward compatibility)
    legacy_connected = bool(current_user.gmail_credentials) or bool(current_user.gmail_email)
    if legacy_connected:
        # Check if legacy email is already in account_list (avoid duplicates)
        legacy_email = current_user.gmail_email
        legacy_exists = any(acc.get("email") == legacy_email for acc in account_list)
        
        if not legacy_exists and legacy_email:
            account_list.append({
                "id": "legacy",
                "email": legacy_email,
                "provider_name": "Gmail (Legacy)",
                "is_connected": True,
                "connected_at": current_user.gmail_connected_at.isoformat() if current_user.gmail_connected_at else None,
                "last_sync_at": None,
                "is_legacy": True
            })
    
    return {
        "connected": len(account_list) > 0,
        "accounts": account_list,
        "emails_scanned": emails_scanned,
        "threats_found": threats_found,
        "queued": queue
    }

@router.get(
    "/queue",
    summary="Get Gmail analysis queue",
    description="Returns all queued, processing, and completed analysis items grouped by status.",
)
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

@router.post(
    "/queue/{message_id}/process",
    summary="Process queued email",
    description="Analyzes a specific queued email synchronously. Use `?force=true` to bypass cache and re-analyze.",
)
async def process_queue_item(
    message_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Process a specific queued email synchronously. Use ?force=true to bypass cache and re-analyze."""
    from app.database import get_mongodb_database
    from datetime import datetime, timezone
    
    mongodb = get_mongodb_database()
    
    existing = await mongodb.gmail_analysis_queue.find_one({
        "user_id": str(current_user.id),
        "message_id": message_id
    })
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found in queue"
        )
    
    source = existing.get("source", "gmail")
    
    if source == "upload":
        job_id = existing.get("job_id")
        if not job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload queue item missing job_id"
            )
        from app.tasks.analysis import analyze_email_task
        from app.models.analysis_job import AnalysisJob
        from sqlalchemy import select
        try:
            job_uuid = uuid.UUID(job_id)
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
        if job.status not in ("pending", "queued"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not pending (current status: {job.status})"
            )
        job.status = "queued"
        await db.commit()
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": str(current_user.id), "message_id": message_id},
            {"$set": {"status": "processing", "started_at": datetime.now(timezone.utc)}}
        )
        analyze_email_task.delay(job_id, None, str(current_user.id))
        return {"message": "Analysis started", "job_id": job_id}
    
    provider_id = existing.get("provider_id")
    
    from app.models.email_provider import EmailProvider
    
    if provider_id:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.id == uuid.UUID(provider_id))
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
        )
    else:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
            .limit(1)
        )
    gmail_provider = result.scalar_one_or_none()
    
    if not current_user.gmail_credentials and not gmail_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    
    if existing and existing.get("status") == "completed":
        return {
            "message": "Email already analyzed",
            "analysis_id": existing.get("analysis_id")
        }
    
    mongo_existing = await mongodb.analysis_results.find_one({
        "user_id": str(current_user.id),
        "gmail_message_id": message_id,
        "superseded": {"$ne": True}
    })
    
    if mongo_existing and not force:
        return {
            "message": "Email already analyzed",
            "analysis_id": str(mongo_existing.get("_id"))
        }
    
    if force and mongo_existing:
        await mongodb.analysis_results.update_one(
            {"_id": mongo_existing.get("_id")},
            {"$set": {"superseded": True}}
        )
        logger.info(f"Superseding old analysis for message {message_id} (force=true)")
    
    if existing and existing.get("status") == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis already in progress"
        )
    
    await mongodb.gmail_analysis_queue.update_one(
        {"user_id": str(current_user.id), "message_id": message_id},
        {"$set": {"status": "processing", "started_at": datetime.now(timezone.utc)}}
    )
    
    try:
        result = await process_gmail_email_sync(str(current_user.id), message_id, provider_id=provider_id, force=force)
        
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": str(current_user.id), "message_id": message_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
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
                "completed_at": datetime.now(timezone.utc),
                "error": str(e)
            }}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


async def process_gmail_email_sync(user_id: str, message_id: str, provider_id: str = None, force: bool = False) -> Dict[str, Any]:
    """Process a Gmail email synchronously (no Celery)."""
    from app.services.gmail_service import gmail_service
    from app.ml.email_parser import EmailParser
    from app.ml.risk_scorer import get_risk_scorer
    from app.services.threat_intel import get_threat_intel_service
    from app.database import get_mongodb_database
    from datetime import datetime, timezone
    import base64
    import logging
    
    logger = logging.getLogger(__name__)
    mongodb = get_mongodb_database()
    
    existing = await mongodb.analysis_results.find_one({
        "user_id": user_id,
        "gmail_message_id": message_id,
        "superseded": {"$ne": True}
    })
    
    if existing and not force:
        logger.info(f"Returning cached analysis for message {message_id}")
        return existing
    
    if existing and force:
        await mongodb.analysis_results.update_one(
            {"_id": existing.get("_id")},
            {"$set": {"superseded": True}}
        )
        logger.info(f"Superseded old analysis for {message_id} (force=true)")
    
    try:
        email_raw = await gmail_service.get_email_by_id(user_id, message_id, provider_id=provider_id)
        if not email_raw:
            raise Exception("Failed to fetch email from Gmail")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "Not Found" in error_msg or "Requested entity was not found" in error_msg:
            logger.warning(f"Message {message_id} not found in Gmail (possibly deleted), checking for any prior analysis...")
            
            any_prior = await mongodb.analysis_results.find_one({
                "user_id": user_id,
                "gmail_message_id": message_id
            })
            
            if any_prior:
                logger.info(f"Using prior analysis for deleted message {message_id}")
                return any_prior
            
            raise Exception(f"Message not found and no prior analysis available: {message_id}")
        
        raise Exception(f"Failed to fetch email from Gmail: {error_msg}")
    
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
        "threat_intelligence": transform_ti_for_storage(ti_result),
        "created_at": datetime.now(timezone.utc)
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
        analysis_id = f"fallback_{message_id}_{int(datetime.now(timezone.utc).timestamp())}"
        detailed_result["_id"] = analysis_id
        detailed_result["job_id"] = message_id
    
    # Create PostgreSQL AnalysisJob record for history/dashboard/report integration
    try:
        from sqlalchemy import select
        from app.database import get_db_session
        async with get_db_session() as db:
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
                    completed_at=datetime.now(timezone.utc)
                )
                db.add(job)
                await db.commit()
    except Exception as job_err:
        logger.warning(f"Failed to create AnalysisJob for Gmail: {job_err}")
    
    return detailed_result

@router.post(
    "/queue/clear",
    summary="Clear completed queue items",
    description="Removes all completed and failed items from the Gmail analysis queue.",
)
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

@router.delete(
    "/queue/{message_id}",
    summary="Delete queue item",
    description="Removes a specific item from the Gmail analysis queue.",
)
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

@router.post(
    "/disconnect",
    summary="Disconnect Gmail",
    description="Disconnects the Gmail account and revokes OAuth credentials for the current user.",
)
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

@router.get(
    "/emails",
    summary="List Gmail emails",
    description="Fetches emails from connected Gmail account(s) with pagination. If `provider_id` is specified, fetches from that account only.",
)
async def list_gmail_emails(
    max_results: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    q: str = None,
    provider_id: str = Query(default=None, description="Specific email provider/account ID to fetch from. If not provided, uses all connected accounts."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List emails from connected Gmail account(s) with optional search query.
    
    If provider_id is provided, fetches from that specific account.
    If provider_id is not provided, fetches from all connected accounts.
    """
    from app.models.email_provider import EmailProvider
    
    gmail_provider = None
    provider_ids = []
    
    if provider_id:
        # Fetch from specific account
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.id == uuid.UUID(provider_id))
            .where(EmailProvider.is_connected == True)
        )
        gmail_provider = result.scalar_one_or_none()
        if not gmail_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email provider not found or not connected"
            )
        provider_ids = [str(gmail_provider.id)]
    else:
        # Fetch from all connected accounts
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
        )
        all_providers = result.scalars().all()
        provider_ids = [str(p.id) for p in all_providers]
        
        if not provider_ids and not current_user.gmail_credentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gmail not connected"
            )
    
    try:
        page_token = None if page == 1 else str((page - 1) * max_results)
        
        # Fetch from primary provider
        if provider_ids or current_user.gmail_credentials:
            emails = await gmail_service.fetch_emails_paginated(
                str(current_user.id), 
                max_results=max_results,
                page_token=page_token,
                query=q,
                provider_id=provider_ids[0] if provider_ids else None
            )
            return emails
        else:
            return {"emails": [], "total_results": 0}
            
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch emails"
        )

@router.get(
    "/emails/search",
    summary="Search Gmail emails",
    description="Searches emails using Gmail search syntax (e.g., `from:sender`, `has:attachment`). Requires a non-empty query.",
)
async def search_gmail_emails(
    q: str,
    max_results: int = 50,
    page: int = 1,
    provider_id: str = Query(default=None, description="Specific email provider/account ID to search from."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Search emails using Gmail search syntax (advanced).
    
    If provider_id is provided, searches that specific account.
    If provider_id is not provided, searches all connected accounts.
    """
    from app.models.email_provider import EmailProvider
    
    gmail_provider = None
    provider_ids = []
    
    if provider_id:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.id == uuid.UUID(provider_id))
            .where(EmailProvider.is_connected == True)
        )
        gmail_provider = result.scalar_one_or_none()
        if not gmail_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email provider not found or not connected"
            )
        provider_ids = [str(gmail_provider.id)]
    else:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
        )
        all_providers = result.scalars().all()
        provider_ids = [str(p.id) for p in all_providers]
        
        if not provider_ids and not current_user.gmail_credentials:
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
            page_token=page_token,
            provider_id=provider_ids[0] if provider_ids else None
        )
        return result
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search emails"
        )

@router.get(
    "/emails/filter",
    summary="Filter Gmail emails",
    description="Filters emails using predefined criteria (date range, sender, subject, attachments).",
)
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
    provider_id: str = Query(default=None, description="Specific email provider/account ID to filter from."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Filter emails using predefined or custom filters.
    
    If provider_id is provided, filters that specific account.
    If provider_id is not provided, filters all connected accounts.
    """
    from app.models.email_provider import EmailProvider
    
    gmail_provider = None
    provider_ids = []
    
    if provider_id:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.id == uuid.UUID(provider_id))
            .where(EmailProvider.is_connected == True)
        )
        gmail_provider = result.scalar_one_or_none()
        if not gmail_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email provider not found or not connected"
            )
        provider_ids = [str(gmail_provider.id)]
    else:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
        )
        all_providers = result.scalars().all()
        provider_ids = [str(p.id) for p in all_providers]
        
        if not provider_ids and not current_user.gmail_credentials:
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
        
        logger.info(f"Gmail filter query built: '{query}'")
        
        page_token = None if page == 1 else str((page - 1) * max_results)
        result = await gmail_service.fetch_emails_paginated(
            str(current_user.id),
            max_results=max_results,
            page_token=page_token,
            query=query,
            provider_id=provider_ids[0] if provider_ids else None
        )
        
        logger.info(f"Gmail filter returned {len(result.get('emails', []))} emails for query: '{query}'")
        
        return {
            **result,
            "applied_filters": {
                "filter_type": filter_type,
                "has_attachments": has_attachments,
                "date_from": date_from,
                "date_to": date_to,
                "from_address": from_address,
                "subject": subject,
                "email_contains": email_contains,
                "provider_id": provider_id
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

@router.get(
    "/emails/query-builder",
    summary="Get Gmail query suggestions",
    description="Returns available Gmail search operators and example queries for building advanced searches.",
)
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

@router.post(
    "/emails/queue",
    summary="Queue emails for analysis",
    description="Adds emails to the analysis queue without starting analysis. Re-queues failed items.",
)
async def queue_gmail_emails(
    message_ids: List[str] = Body(..., embed=True),
    provider_id: str = Query(default=None, description="Specific email provider/account ID to queue from."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Add emails to analysis queue without starting analysis."""
    from app.models.email_provider import EmailProvider
    
    gmail_provider = None
    if provider_id:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.id == uuid.UUID(provider_id))
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
        )
        gmail_provider = result.scalar_one_or_none()
        if not gmail_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email provider not found or not connected"
            )
    else:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
            .limit(1)
        )
        gmail_provider = result.scalar_one_or_none()
    
    if not current_user.gmail_credentials and not gmail_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    
    from app.database import get_mongodb_database
    from datetime import datetime, timezone

    mongodb = get_mongodb_database()
    gmail_svc = gmail_service
    queued = []
    skipped_deleted = 0
    effective_provider_id = str(gmail_provider.id) if gmail_provider else None

    user_id_str = str(current_user.id)
    existing_docs = mongodb.gmail_analysis_queue.find({
        "user_id": user_id_str,
        "message_id": {"$in": message_ids}
    })
    existing_map = {}
    async for doc in existing_docs:
        existing_map[doc["message_id"]] = doc

    for msg_id in message_ids:
        existing = existing_map.get(msg_id)

        if existing:
            if existing.get("status") in ["pending", "processing"]:
                queued.append({"message_id": msg_id, "status": "already_queued"})
                continue
            elif existing.get("status") == "completed":
                queued.append({"message_id": msg_id, "status": "already_analyzed"})
                continue
            elif existing.get("status") == "failed":
                await mongodb.gmail_analysis_queue.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "status": "pending",
                        "provider_id": effective_provider_id,
                        "error": None,
                        "completed_at": None,
                    }}
                )
                queued.append({"message_id": msg_id, "status": "requeued"})
                continue

        try:
            email_data = await gmail_svc.get_email_headers(user_id_str, msg_id, effective_provider_id)
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                logger.warning(f"Skipping deleted message {msg_id} in queue scan")
                skipped_deleted += 1
                await asyncio.sleep(0.1)
                continue
            raise

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
            "user_id": user_id_str,
            "message_id": msg_id,
            "provider_id": effective_provider_id,
            "subject": subject,
            "from": sender,
            "to": recipient,
            "date": date,
            "snippet": snippet,
            "labels": labels,
            "status": "pending",
            "created_at": datetime.now(timezone.utc)
        }
        await mongodb.gmail_analysis_queue.insert_one(queue_doc)
        queued.append({"message_id": msg_id, "status": "queued"})
    
    queued_count = sum(1 for r in queued if r.get("status") in ["queued", "requeued"])
    return {
        "message": f"{queued_count} emails added to queue, {skipped_deleted} skipped (deleted from Gmail)",
        "queued": queued,
        "skipped_deleted": skipped_deleted
    }


@router.post(
    "/emails/analyze",
    summary="Analyze Gmail emails",
    description="Synchronously analyzes selected emails from Gmail. Skips already-analyzed or currently-processing items.",
)
async def analyze_gmail_emails(
    message_ids: List[str] = Body(..., embed=True),
    provider_id: str = Query(default=None, description="Specific email provider/account ID to analyze from."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze selected emails synchronously."""
    from app.models.email_provider import EmailProvider
    
    gmail_provider = None
    if provider_id:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.id == uuid.UUID(provider_id))
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
        )
        gmail_provider = result.scalar_one_or_none()
        if not gmail_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email provider not found or not connected"
            )
    else:
        result = await db.execute(
            select(EmailProvider)
            .where(EmailProvider.user_id == current_user.id)
            .where(EmailProvider.provider_type == "gmail")
            .where(EmailProvider.is_connected == True)
            .limit(1)
        )
        gmail_provider = result.scalar_one_or_none()
    
    if not current_user.gmail_credentials and not gmail_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    
    effective_provider_id = str(gmail_provider.id) if gmail_provider else None

    try:
        from app.database import get_mongodb_database
        from datetime import datetime, timezone

        mongodb = get_mongodb_database()

        gmail_svc = gmail_service
        results = []
        user_id_str = str(current_user.id)

        existing_docs = mongodb.gmail_analysis_queue.find({
            "user_id": user_id_str,
            "message_id": {"$in": message_ids}
        })
        existing_map = {}
        async for doc in existing_docs:
            existing_map[doc["message_id"]] = doc

        for msg_id in message_ids:
            existing = existing_map.get(msg_id)

            if existing:
                if existing.get("status") in ["pending", "processing"]:
                    results.append({"message_id": msg_id, "status": "already_queued"})
                    continue
                elif existing.get("status") == "completed":
                    results.append({
                        "message_id": msg_id,
                        "status": "already_analyzed",
                        "analysis_id": existing.get("analysis_id")
                    })
                    continue
                elif existing.get("status") == "failed":
                    await mongodb.gmail_analysis_queue.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "status": "processing",
                            "provider_id": effective_provider_id,
                            "error": None,
                            "started_at": datetime.now(timezone.utc)
                        }}
                    )
            
            try:
                email_data = await gmail_svc.get_email_headers(str(current_user.id), msg_id, effective_provider_id)
            except Exception as e:
                if "404" in str(e) or "Not Found" in str(e):
                    await mongodb.gmail_analysis_queue.update_one(
                        {"user_id": str(current_user.id), "message_id": msg_id},
                        {"$set": {
                            "status": "failed",
                            "error": "Message deleted from Gmail",
                            "completed_at": datetime.now(timezone.utc)
                        }}
                    )
                    results.append({"message_id": msg_id, "status": "skipped", "reason": "deleted from Gmail"})
                    continue
                raise
            
            subject = ""
            sender = ""
            if email_data and 'payload' in email_data:
                for header in email_data['payload'].get('headers', []):
                    if header.get('name') == 'Subject':
                        subject = header.get('value', '')
                    elif header.get('name') == 'From':
                        sender = header.get('value', '')
            
            if not existing:
                queue_doc = {
                    "user_id": str(current_user.id),
                    "message_id": msg_id,
                    "provider_id": effective_provider_id,
                    "subject": subject,
                    "from": sender,
                    "status": "processing",
                    "created_at": datetime.now(timezone.utc),
                    "started_at": datetime.now(timezone.utc)
                }
                await mongodb.gmail_analysis_queue.insert_one(queue_doc)
            
            try:
                result = await process_gmail_email_sync(str(current_user.id), msg_id, provider_id=effective_provider_id)
                
                await mongodb.gmail_analysis_queue.update_one(
                    {"user_id": str(current_user.id), "message_id": msg_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc),
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
                        "completed_at": datetime.now(timezone.utc),
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

@router.post(
    "/emails/{message_id}/safe",
    summary="Mark email as safe",
    description="Marks a Gmail email as safe (not phishing).",
)
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

@router.post(
    "/emails/{message_id}/phishing",
    summary="Report email as phishing",
    description="Reports a Gmail email as phishing via the Gmail API.",
)
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


# ─── Multi-Account Endpoints ──────────────────────────────────────────────────

@router.get(
    "/accounts",
    summary="Get connected email accounts",
    description="Returns all connected Gmail accounts for the current user with sync status.",
)
async def get_email_accounts(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get all connected email accounts for the current user."""
    from app.models.email_provider import EmailProvider
    from sqlalchemy import select
    
    async with get_db_session() as db:
        result = await db.execute(
            select(EmailProvider).where(
                EmailProvider.user_id == current_user.id,
                EmailProvider.provider_type == "gmail",
                EmailProvider.is_active == True
            ).order_by(EmailProvider.created_at.desc())
        )
        accounts = result.scalars().all()
    
    account_list = []
    for acc in accounts:
        account_list.append({
            "id": str(acc.id),
            "provider_type": acc.provider_type,
            "email": acc.email_address,
            "provider_name": acc.provider_name,
            "is_default": getattr(acc, 'is_default', False) if hasattr(acc, 'is_default') else False,
            "is_connected": acc.is_connected,
            "connected_at": acc.created_at.isoformat() if acc.created_at else None,
            "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
        })
    
    return {"accounts": account_list}


@router.post("/accounts")
async def add_email_account(
    code: str = Body(...),
    state: str = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Add a new email account via OAuth callback."""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA must be enabled before connecting email accounts"
        )
    
    try:
        result = await gmail_service.handle_oauth_callback(code, state, str(current_user.id), db)
        if result.get("success"):
            return {
                "success": True, 
                "email": result.get("email"),
                "account_id": result.get("account_id")
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to connect email account")}
    except Exception as e:
        logger.error(f"Error adding email account: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/accounts/{account_id}")
async def remove_email_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Remove a connected email account."""
    from app.models.email_provider import EmailProvider
    from sqlalchemy import select
    import uuid
    
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID"
        )
    
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == account_uuid,
            EmailProvider.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    account.is_active = False
    await db.commit()
    
    return {"message": "Account disconnected successfully"}


@router.post("/accounts/{account_id}/set-default")
async def set_default_account(
    account_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Set an account as the default for email operations."""
    from app.models.email_provider import EmailProvider
    from sqlalchemy import select, update
    import uuid
    
    try:
        account_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID"
        )
    
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == account_uuid,
            EmailProvider.user_id == current_user.id,
            EmailProvider.provider_type == "gmail"
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    if hasattr(account, 'is_default'):
        account.is_default = True
    await db.commit()
    
    return {"message": "Account set as default"}
