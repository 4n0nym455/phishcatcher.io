"""
Celery Application Configuration

This module configures the Celery application for background task processing.
Uses Redis as both broker and result backend for low-latency task tracking.

Worker startup commands (per-queue prefetch strategy):
  # Analysis queue: prefetch 4 for I/O-bound threat intel calls
  celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 \\
      --queues=analysis --prefetch-multiplier=4 --hostname=analysis@%%h

  # Sync queue: prefetch 1 to avoid stalling on long-running Gmail syncs
  celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 \\
      --queues=sync --prefetch-multiplier=1 --hostname=sync@%%h

  # Default queue: general-purpose workers
  celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 \\
      --queues=default --prefetch-multiplier=2 --hostname=default@%%h
"""

from celery import Celery
from celery.signals import task_success, task_failure, task_retry
from datetime import datetime, timezone
from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "phishcatcher",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.analysis"]
)

# Celery configuration
# NOTE: worker_prefetch_multiplier=4 is the default for all queues.
# For per-queue prefetch, start separate workers with --prefetch-multiplier
# (see docstring above for recommended commands).
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=480,  # 8 minutes soft limit
    worker_prefetch_multiplier=4,  # Default; override per-worker via CLI
    task_acks_late=True,
    result_expires=86400,  # 24 hours
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    worker_disable_rate_limits=True,
)

# Task routes for different queues
celery_app.conf.task_routes = {
    "app.tasks.analysis.analyze_email_task": {"queue": "analysis"},
    "app.tasks.analysis.sync_gmail_task": {"queue": "sync"},
    "app.tasks.analysis.analyze_gmail_email_task": {"queue": "analysis"},
}

# Default queue
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# Task events for monitoring
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Handle task success — logged for observability.
    Task results are stored in Redis via Celery's result backend.
    MongoDB tracking is optional for historical analytics.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Task {sender.name} succeeded with result: {result}")
    
    # Optional: mirror to MongoDB for long-term analytics (non-blocking)
    if hasattr(sender, 'request') and sender.request.id:
        try:
            from app.database import get_mongodb_database
            mongodb = get_mongodb_database()
            mongodb.celery_tasks.update_one(
                {"task_id": sender.request.id},
                {"$set": {
                    "status": "success",
                    "result": result,
                    "completed_at": datetime.now(timezone.utc)
                }}
            )
        except Exception as e:
            logger.debug(f"MongoDB task tracking skipped: {e}")


@task_failure.connect
def task_failure_handler(sender=None, exception=None, **kwargs):
    """Handle task failure — logged for observability.
    Task errors are retrievable via Redis/Celery AsyncResult.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Task {sender.name} failed: {exception}")
    
    if hasattr(sender, 'request') and sender.request.id:
        try:
            from app.database import get_mongodb_database
            mongodb = get_mongodb_database()
            mongodb.celery_tasks.update_one(
                {"task_id": sender.request.id},
                {"$set": {
                    "status": "failed",
                    "error": str(exception),
                    "completed_at": datetime.now(timezone.utc)
                }}
            )
        except Exception as e:
            logger.debug(f"MongoDB task tracking skipped: {e}")


@task_retry.connect
def task_retry_handler(sender=None, reason=None, **kwargs):
    """Handle task retry."""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.warning(f"Task {sender.name} retrying: {reason}")
