"""
Password History Service

This module provides password history functionality to prevent password reuse.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.password_history import PasswordHistory
from app.services.security import verify_password

logger = logging.getLogger(__name__)


async def check_password_reuse(
    db: AsyncSession, 
    user: User, 
    new_password_hash: str, 
    history_limit: int = 5
) -> tuple[bool, str]:
    """
    Check if the new password has been used recently.
    
    Args:
        db: Database session
        user: User object
        new_password_hash: Hash of the new password
        history_limit: Number of previous passwords to check (default: 5)
        
    Returns:
        Tuple of (is_reused, error_message)
    """
    try:
        # Get recent password history
        result = await db.execute(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.created_at.desc())
            .limit(history_limit)
        )
        password_history = result.scalars().all()
        
        # Check against current password and recent history
        if verify_password(new_password_hash, user.password_hash):
            return True, "New password cannot be the same as your current password"
        
        for history_entry in password_history:
            if verify_password(new_password_hash, history_entry.password_hash):
                return True, "You cannot reuse a recent password"
        
        return False, ""
        
    except Exception as e:
        logger.error(f"Error checking password reuse for user {user.id}: {e}")
        # Allow password change if history check fails
        return False, ""


async def save_password_to_history(
    db: AsyncSession, 
    user: User, 
    old_password_hash: str
) -> None:
    """
    Save the old password to history before changing it.
    
    Args:
        db: Database session
        user: User object
        old_password_hash: Hash of the old password
    """
    try:
        # Create password history entry
        history_entry = PasswordHistory(
            user_id=user.id,
            password_hash=old_password_hash,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(history_entry)
        
        # Clean up old password history (keep only last 10)
        cleanup_result = await db.execute(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.created_at.desc())
            .offset(10)
        )
        old_entries = cleanup_result.scalars().all()
        
        for old_entry in old_entries:
            await db.delete(old_entry)
            
    except Exception as e:
        logger.error(f"Error saving password history for user {user.id}: {e}")
        # Don't fail the password change if history saving fails
