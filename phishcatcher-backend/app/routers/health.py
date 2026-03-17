"""
Health Router

This module provides health check endpoints for monitoring and load balancers.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from app.database import check_database_health
from app.config import get_settings

router = APIRouter()


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    db_health = await check_database_health()
    
    all_healthy = all(db_health.values())
    
    if all_healthy:
        return {
            "status": "ready",
            "databases": db_health,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "status": "not_ready",
            "databases": db_health,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/detailed")
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
        # This is a simple check - in production you'd want to ping workers
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
        "timestamp": datetime.utcnow().isoformat()
    }
