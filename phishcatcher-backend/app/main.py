"""
PhishCatcher FastAPI Application

Main entry point for the PhishCatcher API.
"""

import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the backend directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.database import init_databases, close_databases, check_database_health
from app.routers import auth, analysis, providers, admin, health, gmail, notifications, security, email, activation, session, ml
from app.core.logging import setup_logging

# Configure structured logging
settings = get_settings()
setup_logging(
    level=settings.LOG_LEVEL,
    format_type=settings.LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# Centralized API version prefix
API_PREFIX = f"/api/{settings.API_VERSION}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting up PhishCatcher API...")
    await init_databases()
    logger.info("PhishCatcher API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PhishCatcher API...")
    await close_databases()
    logger.info("PhishCatcher API shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Machine Learning-Based Email Phishing Analysis System",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Add middleware
    _add_middleware(app)
    
    # Add exception handlers
    _add_exception_handlers(app)    
    # Include routers
    _include_routers(app)
    
    return app


def _add_middleware(app: FastAPI):
    """Add middleware to the application."""
    settings = get_settings()
    
    # CORS - Parse string values to lists
    cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []
    cors_methods = settings.CORS_ALLOW_METHODS.split(",") if settings.CORS_ALLOW_METHODS else ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers = settings.CORS_ALLOW_HEADERS.split(",") if settings.CORS_ALLOW_HEADERS else ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
        expose_headers=["X-Request-ID", "X-Idempotency-Replayed"]
    )
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else ["*.phishcatcher.io", "phishcatcher.io"]
    )
    
    # API version header
    from starlette.types import ASGIApp, Scope, Receive, Send
    from starlette.responses import Response

    class APIVersionMiddleware:
        """Injects X-API-Version header into every response."""
        def __init__(self, app: ASGIApp):
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            async def send_with_header(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"x-api-version"] = settings.API_VERSION.encode()
                    message["headers"] = list(headers.items())
                await send(message)

            await self.app(scope, receive, send_with_header)

    app.add_middleware(APIVersionMiddleware)
    
    # Request ID (must be first to tag all subsequent middleware/logs)
    from app.middleware.session_middleware import (
        RequestIDMiddleware,
        PureRedisSessionMiddleware,
        PureRedisActivityMiddleware,
    )
    app.add_middleware(RequestIDMiddleware)
    
    # Session management middleware (added after CORS and trusted hosts)
    from app.database import get_redis_client
    
    # Add pure Redis-based session validation middleware
    redis_client = get_redis_client()
    app.add_middleware(PureRedisSessionMiddleware, redis_client=redis_client)
    app.add_middleware(PureRedisActivityMiddleware, redis_client=redis_client)
    
    # Idempotency middleware (must run after session middleware for user_id)
    from app.middleware.idempotency_middleware import IdempotencyMiddleware
    app.add_middleware(IdempotencyMiddleware)


def _add_exception_handlers(app: FastAPI):
    """Add exception handlers to the application."""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        # Clean up errors to make them JSON serializable
        cleaned_errors = []
        for error in exc.errors():
            cleaned_error = error.copy()
            if 'ctx' in cleaned_error and 'error' in cleaned_error['ctx']:
                # Convert the error object to a string
                cleaned_error['ctx']['error'] = str(cleaned_error['ctx']['error'])
            if 'input' in cleaned_error and isinstance(cleaned_error['input'], bytes):
                # Convert bytes input to string
                cleaned_error['input'] = cleaned_error['input'].decode('utf-8', errors='replace')
            cleaned_errors.append(cleaned_error)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": cleaned_errors
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error"
            }
        )


def _include_routers(app: FastAPI):
    """Include API routers."""
    
    # Health check (no authentication required)
    app.include_router(
        health.router,
        prefix="/health",
        tags=["Health"]
    )
    
    # Authentication
    app.include_router(
        auth.router,
        prefix=f"{API_PREFIX}/auth",
        tags=["Authentication"]
    )
    
    # Session Management
    app.include_router(
        session.router,
        prefix=f"{API_PREFIX}/session",
        tags=["Session Management"]
    )
    
    # Analysis
    app.include_router(
        analysis.router,
        prefix=f"{API_PREFIX}/analysis",
        tags=["Analysis"]
    )
    
    # ML Predictions
    app.include_router(
        ml.router,
        prefix=f"{API_PREFIX}/ml",
        tags=["ML Prediction"]
    )
    
    # Email Providers
    app.include_router(
        providers.router,
        prefix=f"{API_PREFIX}/providers",
        tags=["Email Providers"]
    )
    
    # Admin
    app.include_router(
        admin.router,
        prefix=f"{API_PREFIX}/admin",
        tags=["Admin"]
    )
    
    # Gmail Integration
    app.include_router(
        gmail.router,
        prefix=f"{API_PREFIX}",
        tags=["Gmail"]
    )
    
    # Security
    app.include_router(
        security.router,
        prefix=f"{API_PREFIX}",
        tags=["Security"]
    )
    
    # Email Services
    app.include_router(
        email.router,
        prefix=f"{API_PREFIX}",
        tags=["Email"]
    )
    
    # Account Activation
    app.include_router(
        activation.router,
        prefix=f"{API_PREFIX}",
        tags=["Activation"]
    )
    
    # Notifications
    app.include_router(
        notifications.router,
        prefix=f"{API_PREFIX}/notifications",
        tags=["Notifications"]
    )
    
    # Task Monitoring
    from app.routers import tasks as task_router
    app.include_router(
        task_router.router,
        prefix=f"{API_PREFIX}",
        tags=["Tasks"]
    )


# Create application instance
app = create_application()


@app.get("/")
async def root():
    """Root endpoint."""
    settings = get_settings()
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": settings.API_VERSION,
        "status": "operational",
        "documentation": "/docs" if settings.DEBUG else "disabled in production",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    db_health = await check_database_health()
    
    all_healthy = all(db_health.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "databases": db_health,
        "api_version": settings.API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
