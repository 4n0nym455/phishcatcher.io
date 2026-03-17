"""
Pure Redis Session Middleware

Validates user sessions using only Redis native operations.
"""

import time
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis
from app.core.session_manager import get_session_manager
from app.services.security import verify_token
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


class PureRedisSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to validate user sessions using only Redis native operations."""
    
    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.redis = redis_client
        self.session_manager = get_session_manager(redis_client)
    
    async def dispatch(self, request: Request, call_next):
        # Skip session validation for certain endpoints
        skip_paths = [
            "/auth/login",
            "/auth/verify-otp",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/auth/register",
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static/"
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get authorization header
        credentials: HTTPAuthorizationCredentials = await security(request)
        
        if not credentials:
            return await call_next(request)
        
        try:
            # Decode token to get user ID
            payload = verify_token(credentials.credentials)
            if payload is None:
                return await call_next(request)
            
            user_id = payload.get("sub")
            
            if not user_id:
                return await call_next(request)
            
            # Check session validity - Redis handles everything
            is_valid, reason = await self.session_manager.is_session_valid(user_id)
            
            if not is_valid:
                logger.warning(f"Session invalid for user {user_id}: {reason}")
                
                # Return 401 for expired sessions
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": "Session expired",
                        "reason": reason,
                        "code": "SESSION_EXPIRED"
                    }
                )
            
            # Update activity - simply refresh TTL
            await self.session_manager.update_activity(user_id)
            
            # Add session info to request state
            session_info = await self.session_manager.get_session_info(user_id)
            request.state.session_info = session_info
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            # Continue with request if validation fails (don't break the app)
        
        return await call_next(request)


class PureRedisActivityMiddleware(BaseHTTPMiddleware):
    """Middleware to track user activity using only Redis native operations."""
    
    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.redis = redis_client
        self.session_manager = get_session_manager(redis_client)
    
    async def dispatch(self, request: Request, call_next):
        # Skip activity tracking for certain endpoints
        skip_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/static/"
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get authorization header
        credentials: HTTPAuthorizationCredentials = await security(request)
        
        if credentials:
            try:
                # Decode token to get user ID
                payload = verify_token(credentials.credentials)
                if payload is None:
                    return await call_next(request)
                
                user_id = payload.get("sub")
                
                if user_id:
                    # Update activity using Redis TTL (non-blocking)
                    try:
                        await self.session_manager.update_activity(user_id)
                    except Exception as e:
                        logger.error(f"Failed to update activity: {e}")
                        
            except Exception as e:
                logger.debug(f"Activity tracking error: {e}")
        
        return await call_next(request)
