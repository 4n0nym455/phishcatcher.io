"""
PhishCatcher FastAPI Application

Main entry point for the PhishCatcher API.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings
from app.database import init_databases, close_databases, check_database_health
from app.routers import auth, analysis, providers, admin, health, gmail, notifications, security, email, activation, server_oauth, session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
        expose_headers=["X-Request-ID"]
    )
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else ["*.phishcatcher.io", "phishcatcher.io"]
    )
    
    # Session management middleware (added after CORS and trusted hosts)
    from app.database import get_redis_client
    from app.middleware.session_middleware import PureRedisSessionMiddleware, PureRedisActivityMiddleware
    
    # Add pure Redis-based session validation middleware
    redis_client = get_redis_client()
    app.add_middleware(PureRedisSessionMiddleware, redis_client=redis_client)
    app.add_middleware(PureRedisActivityMiddleware, redis_client=redis_client)


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
    
    # API v1 routes
    api_prefix = "/api/v1"
    
    # Authentication
    app.include_router(
        auth.router,
        prefix=f"{api_prefix}/auth",
        tags=["Authentication"]
    )
    
    # Session Management
    app.include_router(
        session.router,
        prefix=f"{api_prefix}/session",
        tags=["Session Management"]
    )
    
    # Analysis
    app.include_router(
        analysis.router,
        prefix=f"{api_prefix}/analysis",
        tags=["Analysis"]
    )
    
    # Email Providers
    app.include_router(
        providers.router,
        prefix=f"{api_prefix}/providers",
        tags=["Email Providers"]
    )
    
    # Admin
    app.include_router(
        admin.router,
        prefix=f"{api_prefix}/admin",
        tags=["Admin"]
    )
    
    # Gmail Integration
    app.include_router(
        gmail.router,
        prefix=f"{api_prefix}",
        tags=["Gmail"]
    )
    
    # Security
    app.include_router(
        security.router,
        prefix=f"{api_prefix}",
        tags=["Security"]
    )
    
    # Email Services
    app.include_router(
        email.router,
        prefix=f"{api_prefix}",
        tags=["Email"]
    )
    
    # Account Activation
    app.include_router(
        activation.router,
        prefix=f"{api_prefix}",
        tags=["Activation"]
    )
    
    # Server-Side OAuth
    app.include_router(
        server_oauth.router,
        prefix=f"{api_prefix}",
        tags=["Server-OAuth"]
    )
    
    # Notifications
    app.include_router(
        notifications.router,
        prefix=f"{api_prefix}/notifications",
        tags=["Notifications"]
    )
    
    # Task Monitoring
    from app.routers import tasks as task_router
    app.include_router(
        task_router.router,
        prefix=f"{api_prefix}",
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
        "status": "operational",
        "documentation": "/docs"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    db_health = await check_database_health()
    
    all_healthy = all(db_health.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "databases": db_health,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
