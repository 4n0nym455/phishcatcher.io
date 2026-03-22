"""
Notifications Router - fixed version

Fixed:
  - Replaced sync 'Session' with async 'AsyncSession'
  - Replaced db.query(...).filter(...).all() with await db.execute(select(...))
  - All db operations now properly awaited
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification, NotificationType
from app.routers.auth import get_current_user, get_current_active_user
from pydantic import BaseModel

router = APIRouter()


class NotificationSubscription(BaseModel):
    endpoint: str
    keys: dict
    user_agent: Optional[str] = None


class NotificationPreferences(BaseModel):
    security_alerts: bool = True
    phishing_detections: bool = True
    system_updates: bool = False
    marketing_emails: bool = False


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    data: Optional[dict] = None


push_subscriptions = {}


@router.post("/subscribe")
async def subscribe_to_notifications(
    subscription: NotificationSubscription,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        push_subscriptions[str(current_user.id)] = subscription.dict()
        if not current_user.notification_preferences:
            current_user.notification_preferences = {
                "security_alerts": True,
                "phishing_detections": True,
                "system_updates": False,
                "marketing_emails": False
            }
            await db.commit()
        return {"message": "Successfully subscribed to notifications"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to subscribe: {str(e)}")


@router.post("/unsubscribe")
async def unsubscribe_from_notifications(current_user: User = Depends(get_current_active_user)):
    try:
        push_subscriptions.pop(str(current_user.id), None)
        return {"message": "Successfully unsubscribed from notifications"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to unsubscribe: {str(e)}")


@router.post("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        current_user.notification_preferences = preferences.dict()
        await db.commit()
        return {"message": "Notification preferences updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update preferences: {str(e)}")


@router.get("/preferences")
async def get_notification_preferences(current_user: User = Depends(get_current_active_user)):
    try:
        preferences = current_user.notification_preferences or {
            "security_alerts": True,
            "phishing_detections": True,
            "system_updates": False,
            "marketing_emails": False
        }
        return preferences
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get preferences: {str(e)}")


@router.get("/notifications")
async def get_user_notifications(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # FIX: use async select() instead of sync db.query()
        query = select(Notification).where(Notification.user_id == current_user.id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        notifications = result.scalars().all()

        return [
            NotificationResponse(
                id=notif.id,
                type=notif.type,
                title=notif.title,
                message=notif.message,
                is_read=notif.is_read,
                created_at=notif.created_at,
                data=notif.data
            )
            for notif in notifications
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get notifications: {str(e)}")


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        notification.is_read = True
        await db.commit()
        return {"message": "Notification marked as read"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to mark as read: {str(e)}")


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        await db.execute(
            update(Notification)
            .where(Notification.user_id == current_user.id, Notification.is_read == False)
            .values(is_read=True)
        )
        await db.commit()
        return {"message": "All notifications marked as read"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to mark all as read: {str(e)}")


async def send_push_notification(user_id: str, title: str, message: str, notification_type: str = "info", data: dict = None):
    if user_id not in push_subscriptions:
        return False
    try:
        logger.info(f"Push notification → user {user_id}: {title}")
        return True
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


async def create_notification(
    db: AsyncSession,
    user_id,
    notification_type: NotificationType,
    title: str,
    message: str,
    data: dict = None
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        data=data or {}
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


import logging
logger = logging.getLogger(__name__)