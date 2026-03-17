"""
Email Providers Router

This module handles email provider integration endpoints including:
- Gmail OAuth connection
- List connected providers
- Sync emails
- Disconnect providers
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.email_provider import EmailProvider
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.email_provider import (
    EmailProviderCreate, EmailProviderResponse, EmailProviderUpdate,
    EmailProviderList, GmailConnectRequest, SyncRequest, SyncResponse,
    ProviderHealth, GmailAuthUrl
)
from app.routers.auth import get_current_active_user
from app.services.gmail import GmailService, GmailServiceFactory
from app.services.security import encrypt_data, decrypt_data
from app.tasks.analysis import sync_gmail_task

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/gmail/auth-url")
async def get_gmail_auth_url():
    """Get Gmail OAuth authorization URL."""
    import secrets
    state = secrets.token_urlsafe(32)
    auth_url = GmailService.get_authorization_url(state)
    
    return {"auth_url": auth_url, "state": state}


@router.post("/gmail/connect", response_model=EmailProviderResponse)
async def connect_gmail(
    connect_data: GmailConnectRequest,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Connect Gmail account using OAuth code."""
    try:
        # Exchange code for tokens
        token_data = GmailService.exchange_code_for_tokens(code)
        
        # Check if provider already exists
        result = await db.execute(
            select(EmailProvider).where(
                EmailProvider.user_id == current_user.id,
                EmailProvider.email_address == token_data['email']
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing provider
            existing.access_token = encrypt_data(token_data['access_token'])
            existing.refresh_token = encrypt_data(token_data['refresh_token']) if token_data.get('refresh_token') else existing.refresh_token
            existing.token_expires_at = token_data.get('expires_at')
            existing.is_connected = True
            existing.connection_error = None
            provider = existing
        else:
            # Create new provider
            provider = EmailProvider(
                user_id=current_user.id,
                provider_type="gmail",
                provider_name=connect_data.provider_name or token_data.get('name', 'Gmail'),
                email_address=token_data['email'],
                access_token=encrypt_data(token_data['access_token']),
                refresh_token=encrypt_data(token_data['refresh_token']) if token_data.get('refresh_token') else None,
                token_expires_at=token_data.get('expires_at'),
                sync_enabled=connect_data.sync_enabled,
                sync_folder=connect_data.sync_folder,
                max_emails_per_sync=connect_data.max_emails_per_sync,
                is_connected=True
            )
            db.add(provider)
        
        await db.flush()
        
        # Log connection
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            action=AuditAction.PROVIDER_CONNECTED,
            resource_type="email_provider",
            resource_id=provider.id,
            status="success",
            details={"provider_type": "gmail", "email": token_data['email']}
        )
        db.add(audit_log)
        await db.commit()
        
        logger.info(f"Gmail connected for {current_user.email}: {token_data['email']}")
        
        return provider
        
    except Exception as e:
        logger.error(f"Gmail connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Gmail: {str(e)}"
        )


@router.get("", response_model=EmailProviderList)
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List connected email providers."""
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.user_id == current_user.id,
            EmailProvider.is_active == True
        )
    )
    providers = result.scalars().all()
    
    return EmailProviderList(
        items=[
            EmailProviderResponse(
                id=str(p.id),
                provider_type=p.provider_type,
                provider_name=p.provider_name,
                email_address=p.email_address,
                sync_enabled=p.sync_enabled,
                last_sync_at=p.last_sync_at,
                is_active=p.is_active,
                is_connected=p.is_connected,
                sync_folder=p.sync_folder,
                max_emails_per_sync=p.max_emails_per_sync,
                created_at=p.created_at
            )
            for p in providers
        ],
        total=len(providers)
    )


@router.get("/{provider_id}", response_model=EmailProviderResponse)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get provider details."""
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == provider_id,
            EmailProvider.user_id == current_user.id
        )
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    return provider


@router.put("/{provider_id}", response_model=EmailProviderResponse)
async def update_provider(
    provider_id: str,
    update_data: EmailProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update provider settings."""
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == provider_id,
            EmailProvider.user_id == current_user.id
        )
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Update fields
    if update_data.provider_name is not None:
        provider.provider_name = update_data.provider_name
    if update_data.sync_enabled is not None:
        provider.sync_enabled = update_data.sync_enabled
    if update_data.sync_folder is not None:
        provider.sync_folder = update_data.sync_folder
    if update_data.sync_filter is not None:
        provider.sync_filter = update_data.sync_filter
    if update_data.max_emails_per_sync is not None:
        provider.max_emails_per_sync = update_data.max_emails_per_sync
    if update_data.sync_frequency_minutes is not None:
        provider.sync_frequency_minutes = update_data.sync_frequency_minutes
    
    await db.commit()
    
    return provider


@router.post("/{provider_id}/sync", response_model=SyncResponse)
async def sync_provider(
    provider_id: str,
    sync_request: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger email sync for a provider."""
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == provider_id,
            EmailProvider.user_id == current_user.id
        )
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    if not provider.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not connected"
        )
    
    # Queue sync task
    sync_task = sync_gmail_task.delay(
        provider_id=str(provider.id),
        user_id=str(current_user.id),
        max_emails=sync_request.max_emails
    )
    
    # Log sync start
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.PROVIDER_SYNC_STARTED,
        resource_type="email_provider",
        resource_id=provider.id,
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"Sync started for provider {provider_id}")
    
    return SyncResponse(
        provider_id=str(provider.id),
        sync_job_id=sync_task.id,
        status="queued",
        message="Sync job queued successfully",
        emails_queued=0
    )


@router.get("/{provider_id}/health", response_model=ProviderHealth)
async def check_provider_health(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check provider connection health."""
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == provider_id,
            EmailProvider.user_id == current_user.id
        )
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    is_token_valid = False
    
    if provider.provider_type == "gmail" and provider.is_connected:
        try:
            gmail_service = GmailServiceFactory.from_provider(provider)
            is_token_valid = gmail_service.is_token_valid()
        except Exception as e:
            logger.warning(f"Token validation failed for provider {provider_id}: {e}")
    
    return ProviderHealth(
        provider_id=str(provider.id),
        is_connected=provider.is_connected,
        is_token_valid=is_token_valid,
        last_error=provider.connection_error,
        last_error_at=provider.last_error_at
    )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Disconnect and delete a provider."""
    result = await db.execute(
        select(EmailProvider).where(
            EmailProvider.id == provider_id,
            EmailProvider.user_id == current_user.id
        )
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Stop push notifications if enabled
    if provider.webhook_enabled and provider.provider_type == "gmail":
        try:
            gmail_service = GmailServiceFactory.from_provider(provider)
            await gmail_service.stop_push_notifications(provider.webhook_resource_id)
        except Exception as e:
            logger.warning(f"Failed to stop push notifications: {e}")
    
    # Soft delete
    provider.is_active = False
    
    # Log disconnection
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=AuditAction.PROVIDER_DISCONNECTED,
        resource_type="email_provider",
        resource_id=provider.id,
        status="success"
    )
    db.add(audit_log)
    await db.commit()
    
    logger.info(f"Provider {provider_id} disconnected by {current_user.email}")
