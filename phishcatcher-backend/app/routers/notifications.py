from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification, NotificationType
from app.routers.auth import get_current_user, get_current_active_user
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
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

# In-memory storage for push subscriptions (in production, use Redis or database)
push_subscriptions = {}

@router.post("/subscribe")
async def subscribe_to_notifications(
    subscription: NotificationSubscription,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Subscribe to push notifications"""
    try:
        # Store subscription for user
        push_subscriptions[current_user.id] = subscription.dict()
        
        # Save user notification preferences if not exists
        if not hasattr(current_user, 'notification_preferences'):
            current_user.notification_preferences = {
                "security_alerts": True,
                "phishing_detections": True,
                "system_updates": False,
                "marketing_emails": False
            }
            db.commit()
        
        return {"message": "Successfully subscribed to notifications"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe: {str(e)}"
        )

@router.post("/unsubscribe")
async def unsubscribe_from_notifications(
    current_user: User = Depends(get_current_active_user)
):
    """Unsubscribe from push notifications"""
    try:
        # Remove subscription for user
        if current_user.id in push_subscriptions:
            del push_subscriptions[current_user.id]
        
        return {"message": "Successfully unsubscribed from notifications"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe: {str(e)}"
        )

@router.post("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences"""
    try:
        current_user.notification_preferences = preferences.dict()
        db.commit()
        
        return {"message": "Notification preferences updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )

@router.get("/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user)
):
    """Get current notification preferences"""
    try:
        preferences = getattr(current_user, 'notification_preferences', {
            "security_alerts": True,
            "phishing_detections": True,
            "system_updates": False,
            "marketing_emails": False
        })
        
        return preferences
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preferences: {str(e)}"
        )

@router.get("/notifications")
async def get_user_notifications(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user notifications"""
    try:
        query = db.query(Notification).filter(
            Notification.user_id == current_user.id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        notifications = query.order_by(
            Notification.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            NotificationResponse(
                id=notif.id,
                type=notif.type.value,
                title=notif.title,
                message=notif.message,
                is_read=notif.is_read,
                created_at=notif.created_at,
                data=notif.data
            )
            for notif in notifications
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification.is_read = True
        db.commit()
        
        return {"message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )

@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    try:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        ).update({"is_read": True})
        
        db.commit()
        
        return {"message": "All notifications marked as read"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )

# Helper function to send push notification
async def send_push_notification(user_id: int, title: str, message: str, notification_type: str = "info", data: dict = None):
    """Send push notification to user"""
    if user_id not in push_subscriptions:
        return False
    
    subscription = push_subscriptions[user_id]
    
    # In a real implementation, you would use a service like Firebase Cloud Messaging
    # or Web Push Protocol libraries
    try:
        # This is a placeholder - implement actual push notification sending
        print(f"Sending push notification to user {user_id}: {title} - {message}")
        return True
    except Exception as e:
        print(f"Failed to send push notification: {e}")
        return False

# Helper function to create in-app notification
def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    data: dict = None
):
    """Create notification in database"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        data=data or {}
    )
    
    db.add(notification)
    db.commit()
    
    return notification
