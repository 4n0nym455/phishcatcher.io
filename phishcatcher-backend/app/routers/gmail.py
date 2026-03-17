"""
Gmail Integration Router

This module provides API endpoints for Gmail integration including:
- OAuth authentication flow
- Email fetching and analysis
- Gmail account management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
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
    try:
        auth_url = gmail_service.get_auth_url(str(current_user.id))
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting Gmail auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Gmail authorization URL"
        )

@router.get("/auth/callback")
async def gmail_auth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle Gmail OAuth callback."""
    try:
        result = await gmail_service.handle_oauth_callback(code, state)
        if result.get("success"):
            return {
                "message": "Gmail account connected successfully",
                "email": result.get("email")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to connect Gmail account"
            )
    except Exception as e:
        logger.error(f"Gmail OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Gmail authorization"
        )

@router.get("/status")
async def get_gmail_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get Gmail connection status for current user."""
    return {
        "connected": bool(current_user.gmail_credentials),
        "email": current_user.gmail_email,
        "connected_at": current_user.gmail_connected_at,
        "auto_scan": current_user.gmail_auto_scan
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

@router.post("/scan")
async def scan_recent_emails(
    max_results: int = 10,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Scan recent emails for phishing threats."""
    try:
        emails = await gmail_service.fetch_recent_emails(str(current_user.id), max_results)
        
        # Count threats
        threats = [email for email in emails if email.get('analysis', {}).get('is_phishing', False)]
        
        return {
            "scanned": len(emails),
            "threats_found": len(threats),
            "emails": emails
        }
    except Exception as e:
        logger.error(f"Error scanning emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scan emails"
        )

@router.put("/auto-scan")
async def toggle_auto_scan(
    enabled: bool,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Toggle automatic email scanning."""
    try:
        current_user.gmail_auto_scan = enabled
        await db.commit()
        
        return {
            "message": f"Auto-scan {'enabled' if enabled else 'disabled'}",
            "auto_scan": current_user.gmail_auto_scan
        }
    except Exception as e:
        logger.error(f"Error toggling auto-scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update auto-scan settings"
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
