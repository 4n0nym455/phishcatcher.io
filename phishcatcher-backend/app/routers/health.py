"""
Health Router

This module provides health check endpoints for monitoring and load balancers.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.database import check_database_health
from app.config import get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Basic health check response."""
    status: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Readiness probe response."""
    status: str
    databases: Dict[str, bool]
    timestamp: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    status: str
    components: Dict[str, Any]
    version: str
    environment: str
    timestamp: str


@router.get(
    "",
    summary="Basic health check",
    description="Returns the basic health status of the API. Suitable for simple uptime checks.",
    response_model=HealthResponse,
    responses={
        200: {"description": "API is running and healthy"},
    },
)
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Checks if the API is ready to receive traffic by verifying all database connections.",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "API is ready (all databases connected)"},
        503: {"description": "API is not ready (one or more databases disconnected)"},
    },
)
async def readiness_check():
    """Readiness probe for Kubernetes."""
    db_health = await check_database_health()
    
    all_healthy = all(db_health.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "databases": db_health,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns whether the process is alive. Used by Kubernetes to determine if the container should be restarted.",
    response_model=HealthResponse,
)
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/detailed",
    summary="Detailed health check",
    description="Returns comprehensive health status including databases, ML model, and task queue configuration.",
    response_model=DetailedHealthResponse,
)
async def detailed_health_check():
    """Detailed health check with component status."""
    settings = get_settings()
    db_health = await check_database_health()
    
    # Check ML model
    try:
        from app.ml.phishing_detector import get_phishing_detector
        detector = get_phishing_detector()
        ml_status = {
            "status": "healthy" if detector.is_trained() else "untrained",
            "version": detector.model_version,
            "is_trained": detector.is_trained()
        }
    except Exception as e:
        ml_status = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Celery
    try:
        from app.tasks.celery_app import celery_app
        celery_status = {"status": "configured"}
    except Exception as e:
        celery_status = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    all_healthy = (
        all(db_health.values()) and 
        ml_status["status"] in ["healthy", "untrained"] and
        celery_status["status"] == "configured"
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            "databases": db_health,
            "ml_model": ml_status,
            "task_queue": celery_status
        },
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
