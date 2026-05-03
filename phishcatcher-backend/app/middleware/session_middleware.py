"""
Pure Redis Session Middleware

Validates user sessions using only Redis native operations.
Acts as a soft-check — enriches request.state with session info but
never blocks requests. Hard auth is handled by the get_current_user
dependency in routers (single source of truth).

Public endpoints are configured via app.config.PUBLIC_PATHS.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
import redis.asyncio as redis
from app.core.session_manager import get_session_manager
from app.services.security import verify_token
from app.core.logging import get_request_logger
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

DEFAULT_PUBLIC_PATHS = [
    "/auth/login",
    "/auth/verify-otp",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/register",
    "/health",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/favicon.ico",
    "/static/",
    "/redoc",
]


def get_public_paths() -> list[str]:
    """Get list of paths that skip session validation."""
    try:
        from app.config import get_settings
        settings = get_settings()
        extra = settings.model_config.get("public_paths", [])
        return list(set(DEFAULT_PUBLIC_PATHS + extra))
    except Exception:
        return DEFAULT_PUBLIC_PATHS


class RequestIDMiddleware:
    """Injects a unique request ID into request.state for correlation."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request.state.request_id = str(uuid.uuid4())[:8]
        request.state.logger = get_request_logger(__name__, request.state.request_id)
        await self.app(scope, receive, send)


class PureRedisSessionMiddleware:
    """Middleware to validate user sessions using only Redis native operations.

    This is a soft validation layer:
    - If token is valid and session exists → adds session_info to request.state
    - If token is missing, invalid, or session expired → silently passes through
    - Hard auth rejection is delegated to get_current_user dependency
    """

    def __init__(self, app: ASGIApp, redis_client: redis.Redis):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from app.database import get_redis_client
        from app.core.session_manager import get_session_manager

        redis_client = get_redis_client()
        session_manager = get_session_manager(redis_client)

        request = Request(scope)
        skip_paths = get_public_paths()

        if any(request.url.path.startswith(path) for path in skip_paths):
            await self.app(scope, receive, send)
            return

        credentials: HTTPAuthorizationCredentials = await security(request)

        if not credentials:
            await self.app(scope, receive, send)
            return

        try:
            payload = verify_token(credentials.credentials)
            if not payload:
                await self.app(scope, receive, send)
                return

            user_id = payload.get("sub")
            if not user_id:
                await self.app(scope, receive, send)
                return

            session_id = payload.get("sid")
            if not session_id:
                await self.app(scope, receive, send)
                return

            is_valid, reason = await session_manager.is_session_valid(user_id, session_id)

            if is_valid:
                await session_manager.update_activity(user_id, session_id)
                session_info = await session_manager.get_session_info(user_id, session_id)
                request.state.session_info = session_info
                request.state.user_id = user_id
                request.state.session_id = session_id
            else:
                logger.info(f"Session check (soft) for user {user_id}: {reason}")

        except Exception as e:
            logger.debug(f"Session middleware soft-check skipped: {e}")

        await self.app(scope, receive, send)


class PureRedisActivityMiddleware:
    """Lightweight activity tracking middleware.

    Logs request metadata for authenticated endpoints.
    Session activity TTL updates are handled by PureRedisSessionMiddleware.
    """

    def __init__(self, app: ASGIApp, redis_client: redis.Redis):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        skip_paths = get_public_paths()

        if any(request.url.path.startswith(path) for path in skip_paths):
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
