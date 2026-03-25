"""
Gmail Integration Router

This module provides API endpoints for Gmail integration including:
- OAuth authentication flow
- Email fetching and analysis
- Gmail account management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, Body
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging

from app.database import get_db
from app.models.user import User
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
    async for q in mongodb.gmail_analysis_queue.find({"user_id": str(current_user.id), "status": "pending"}):
        queue.append({"message_id": q["message_id"], "subject": q.get("subject", ""), "from": q.get("from", "")})
    
    return {
        "connected": bool(current_user.gmail_credentials),
        "email": current_user.gmail_email,
        "connected_at": current_user.gmail_connected_at,
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
            "status": q.get("status", "pending"),
            "created_at": q.get("created_at"),
            "completed_at": q.get("completed_at"),
            "analysis_id": q.get("analysis_id"),
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
            "overall_score": analysis_result["risk_score"],
            "category": analysis_result["threat_category"],
            "confidence": analysis_result["confidence"]
        },
        "findings": analysis_result["findings"],
        "links_analyzed": parsed_email.get("links", []),
        "attachments_analyzed": parsed_email.get("attachments", []),
        "risk_factors": analysis_result["risk_factors"],
        "ml_prediction": analysis_result["ml_prediction"],
        "created_at": datetime.utcnow()
    }
    
    result = mongodb.analysis_results.insert_one(detailed_result)
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
    max_results: int = 20,
    page: int = 1,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """List emails from connected Gmail account."""
    if not current_user.gmail_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    try:
        start = (page - 1) * max_results
        emails = await gmail_service.fetch_emails_paginated(
            str(current_user.id), 
            max_results=max_results,
            page_token=None if page == 1 else str(start)
        )
        return emails
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch emails"
        )

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
            email_data = await gmail_svc.get_email_by_id(str(current_user.id), msg_id)
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
