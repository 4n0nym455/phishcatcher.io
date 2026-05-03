"""
Fully Redis-based Session Management Module

Supports multiple concurrent sessions per user.
Keys: session:{user_id}:{session_id}
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()


class PureRedisSessionManager:
    """Manages user sessions using only Redis native operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def _session_key(self, user_id: str, session_id: str) -> str:
        return f"session:{user_id}:{session_id}"
    
    def _user_sessions_key(self, user_id: str) -> str:
        return f"user_sessions:{user_id}"
    
    async def create_session(self, user_id: str, user_email: str, ip_address: str, user_agent: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session. Returns session_data including the session_id."""
        session_id = session_id or str(uuid.uuid4())
        session_key = self._session_key(user_id, session_id)
        current_time = datetime.now(timezone.utc)
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "user_email": user_email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": current_time.isoformat(),
            "login_time": current_time.isoformat(),
            "last_activity": current_time.isoformat(),
        }
        
        session_duration = settings.SESSION_MAX_DURATION_MINUTES * 60
        await self.redis.setex(session_key, session_duration, json.dumps(session_data))
        
        # Track session_id in user's session set
        await self.redis.sadd(self._user_sessions_key(user_id), session_id)
        await self.redis.expire(self._user_sessions_key(user_id), session_duration)
        
        return session_data
    
    async def update_activity(self, user_id: str, session_id: str) -> bool:
        """Update user activity - refresh the session TTL and update last_activity."""
        session_key = self._session_key(user_id, session_id)
        
        session_data = await self.redis.get(session_key)
        if not session_data:
            return False
        
        try:
            session = json.loads(session_data)
            current_time = datetime.now(timezone.utc)
            session["last_activity"] = current_time.isoformat()
            
            session_duration = settings.SESSION_MAX_DURATION_MINUTES * 60
            await self.redis.setex(session_key, session_duration, json.dumps(session))
            await self.redis.expire(self._user_sessions_key(user_id), session_duration)
            
            return True
        except (json.JSONDecodeError, KeyError):
            return False
    
    async def is_session_valid(self, user_id: str, session_id: str) -> tuple[bool, Optional[str]]:
        """Check if session is valid."""
        session_key = self._session_key(user_id, session_id)
        
        session_data = await self.redis.get(session_key)
        if not session_data:
            return False, "Session not found or expired"
        
        return True, None
    
    async def get_session_info(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information including Redis TTL data."""
        session_key = self._session_key(user_id, session_id)
        
        session_data = await self.redis.get(session_key)
        if not session_data:
            return None
        
        try:
            session = json.loads(session_data)
            current_time = datetime.now(timezone.utc)
            
            session_ttl = await self.redis.ttl(session_key)
            remaining_session_minutes = max(0, session_ttl // 60) if session_ttl > 0 else 0
            
            login_time = datetime.fromisoformat(session["login_time"])
            session_age_minutes = int((current_time - login_time).total_seconds() / 60)
            
            last_activity_time = datetime.fromisoformat(session["last_activity"])
            last_activity_minutes_ago = int((current_time - last_activity_time).total_seconds() / 60)
            
            return {
                **session,
                "remaining_session_minutes": remaining_session_minutes,
                "session_ttl_seconds": session_ttl,
                "session_age_minutes": session_age_minutes,
                "last_activity_minutes_ago": last_activity_minutes_ago,
                "max_duration_minutes": settings.SESSION_MAX_DURATION_MINUTES
            }
            
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    async def destroy_session(self, user_id: str, session_id: str) -> bool:
        """Destroy a specific session."""
        session_key = self._session_key(user_id, session_id)
        
        deleted = await self.redis.delete(session_key)
        await self.redis.srem(self._user_sessions_key(user_id), session_id)
        
        return deleted > 0
    
    async def destroy_all_user_sessions(self, user_id: str) -> int:
        """Destroy all sessions for a user (e.g., password change)."""
        sessions_key = self._user_sessions_key(user_id)
        session_ids = await self.redis.smembers(sessions_key)
        
        deleted = 0
        for sid in session_ids:
            if isinstance(sid, bytes):
                sid = sid.decode()
            key = self._session_key(user_id, sid)
            deleted += await self.redis.delete(key)
        
        await self.redis.delete(sessions_key)
        return deleted
    
    async def extend_session(self, user_id: str, session_id: str) -> bool:
        """Extend session - refresh the TTL."""
        session_key = self._session_key(user_id, session_id)
        
        session_data = await self.redis.get(session_key)
        if not session_data:
            return False
        
        try:
            session = json.loads(session_data)
            current_time = datetime.now(timezone.utc)
            
            session["last_activity"] = current_time.isoformat()
            
            session_duration = settings.SESSION_MAX_DURATION_MINUTES * 60
            await self.redis.setex(session_key, session_duration, json.dumps(session))
            await self.redis.expire(self._user_sessions_key(user_id), session_duration)
            
            return True
            
        except (json.JSONDecodeError, KeyError):
            await self.destroy_session(user_id, session_id)
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user."""
        sessions_key = self._user_sessions_key(user_id)
        session_ids = await self.redis.smembers(sessions_key)
        
        sessions = []
        for sid in session_ids:
            if isinstance(sid, bytes):
                sid = sid.decode()
            info = await self.get_session_info(user_id, sid)
            if info:
                sessions.append(info)
        
        return sessions
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions across all users (admin)."""
        user_sessions_keys = await self.redis.keys("user_sessions:*")
        
        all_sessions = []
        for key in user_sessions_keys:
            if isinstance(key, bytes):
                key = key.decode()
            user_id = key.replace("user_sessions:", "")
            sessions = await self.get_user_sessions(user_id)
            all_sessions.extend(sessions)
        
        return all_sessions
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove stale user_sessions sets that point to expired sessions."""
        user_sessions_keys = await self.redis.keys("user_sessions:*")
        
        cleaned = 0
        for key in user_sessions_keys:
            if isinstance(key, bytes):
                key = key.decode()
            user_id = key.replace("user_sessions:", "")
            session_ids = await self.redis.smembers(key)
            
            for sid in session_ids:
                if isinstance(sid, bytes):
                    sid = sid.decode()
                if not await self.redis.exists(self._session_key(user_id, sid)):
                    await self.redis.srem(key, sid)
                    cleaned += 1
        
        return cleaned
    
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        session_keys = await self.redis.keys("session:*:*")
        return len(session_keys)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        session_keys = await self.redis.keys("session:*:*")
        
        return {
            "total_sessions": len(session_keys),
            "active_sessions": len([key for key in session_keys if await self.redis.exists(key)]),
            "max_duration_minutes": settings.SESSION_MAX_DURATION_MINUTES,
            "inactivity_minutes": settings.SESSION_INACTIVITY_MINUTES,
            "session_management": "pure_redis"
        }


# Global session manager instance
_session_manager: Optional[PureRedisSessionManager] = None
_session_manager_redis_id: Optional[int] = None


def get_session_manager(redis_client: redis.Redis) -> PureRedisSessionManager:
    """Get or create pure Redis session manager instance."""
    global _session_manager, _session_manager_redis_id
    client_id = id(redis_client)
    if _session_manager is None or _session_manager_redis_id != client_id:
        _session_manager = PureRedisSessionManager(redis_client)
        _session_manager_redis_id = client_id
    return _session_manager
