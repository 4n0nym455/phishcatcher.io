"""
Fully Redis-based Session Management Module

Handles session tracking using only Redis native operations - no custom expiration logic.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()


class PureRedisSessionManager:
    """Manages user sessions using only Redis native operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def create_session(self, user_id: str, user_email: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Create a new session - Redis handles all expiration automatically."""
        session_key = f"session:{user_id}"
        current_time = datetime.utcnow()
        
        session_data = {
            "user_id": user_id,
            "user_email": user_email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": current_time.isoformat(),
            "login_time": current_time.isoformat()
        }
        
        # Store session with 2-minute TTL - Redis handles expiration automatically
        session_duration = settings.SESSION_MAX_DURATION_MINUTES * 60  # 2 minutes in seconds
        await self.redis.setex(
            session_key,
            session_duration,
            json.dumps(session_data)
        )
        
        return session_data
    
    async def update_activity(self, user_id: str) -> bool:
        """Update user activity - simply refresh the session TTL."""
        session_key = f"session:{user_id}"
        
        # Check if session exists
        session_data = await self.redis.get(session_key)
        if not session_data:
            return False
        
        # Refresh session TTL to extend it - Redis handles this natively
        session_duration = settings.SESSION_MAX_DURATION_MINUTES * 60  # 2 minutes in seconds
        await self.redis.expire(session_key, session_duration)
        
        return True
    
    async def is_session_valid(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Check if session is valid - Redis key existence is the only check needed."""
        session_key = f"session:{user_id}"
        
        # Redis TTL handles expiration automatically
        # If key exists, session is valid; if not, it's expired
        session_data = await self.redis.get(session_key)
        
        if not session_data:
            return False, "Session not found or expired"
        
        return True, None
    
    async def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session information including Redis TTL data."""
        session_key = f"session:{user_id}"
        
        session_data = await self.redis.get(session_key)
        if not session_data:
            return None
        
        try:
            session = json.loads(session_data)
            current_time = datetime.utcnow()
            
            # Get TTL from Redis - this is the authoritative source
            session_ttl = await self.redis.ttl(session_key)
            
            # Calculate remaining time
            remaining_session_minutes = max(0, session_ttl // 60) if session_ttl > 0 else 0
            
            # Calculate session age
            login_time = datetime.fromisoformat(session["login_time"])
            session_age_minutes = int((current_time - login_time).total_seconds() / 60)
            
            return {
                **session,
                "remaining_session_minutes": remaining_session_minutes,
                "session_ttl_seconds": session_ttl,
                "session_age_minutes": session_age_minutes,
                "max_duration_minutes": settings.SESSION_MAX_DURATION_MINUTES
            }
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    async def destroy_session(self, user_id: str) -> bool:
        """Destroy a user's session - simple Redis delete."""
        session_key = f"session:{user_id}"
        
        # Redis handles deletion cleanly
        deleted = await self.redis.delete(session_key)
        
        return deleted > 0
    
    async def extend_session(self, user_id: str) -> bool:
        """Extend session - simply refresh the TTL."""
        session_key = f"session:{user_id}"
        
        session_data = await self.redis.get(session_key)
        if not session_data:
            return False
        
        try:
            session = json.loads(session_data)
            current_time = datetime.utcnow()
            
            # Update last activity time
            session["last_activity"] = current_time.isoformat()
            
            # Store with fresh TTL - Redis handles expiration
            session_duration = settings.SESSION_MAX_DURATION_MINUTES * 60  # 2 minutes in seconds
            await self.redis.setex(
                session_key,
                session_duration,
                json.dumps(session)
            )
            
            return True
            
        except (json.JSONDecodeError, KeyError):
            await self.destroy_session(user_id)
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Redis handles cleanup automatically - just return active count."""
        # Get all session keys
        session_keys = await self.redis.keys("session:*")
        
        # Count active sessions (Redis TTL handles expiration automatically)
        active_count = 0
        for session_key in session_keys:
            if await self.redis.exists(session_key):
                active_count += 1
        
        return active_count
    
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        session_keys = await self.redis.keys("session:*")
        return len(session_keys)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        session_keys = await self.redis.keys("session:*")
        
        return {
            "total_sessions": len(session_keys),
            "active_sessions": len([key for key in session_keys if await self.redis.exists(key)]),
            "max_duration_minutes": settings.SESSION_MAX_DURATION_MINUTES,
            "inactivity_minutes": settings.SESSION_INACTIVITY_MINUTES,
            "session_management": "pure_redis"
        }


# Global session manager instance
_session_manager: Optional[PureRedisSessionManager] = None


def get_session_manager(redis_client: redis.Redis) -> PureRedisSessionManager:
    """Get or create pure Redis session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = PureRedisSessionManager(redis_client)
    return _session_manager
