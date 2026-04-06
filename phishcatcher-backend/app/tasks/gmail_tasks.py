"""
Gmail-related Celery tasks.

This module contains Celery tasks for Gmail integration including
email syncing and analysis.
"""

from app.tasks.celery_app import celery_app
from celery import Task
import logging

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callback support."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(f"Task {task_id} retrying: {exc}")


@celery_app.task(bind=True, base=CallbackTask, max_retries=3, default_retry_delay=60, name="gmail_tasks.fetch_emails")
def fetch_emails_task(self, user_id: str, max_results: int = 50):
    """
    Celery task to fetch emails from Gmail.
    
    Args:
        user_id: User ID who owns the Gmail account
        max_results: Maximum number of emails to fetch
    """
    import asyncio
    from app.services.gmail_service import gmail_service
    from app.database import get_mongodb_database
    from datetime import datetime
    
    logger.info(f"Starting Gmail fetch for user {user_id}")
    
    async def _fetch():
        mongodb = get_mongodb_database()
        
        emails = await gmail_service.fetch_recent_emails(user_id, max_results)
        
        # Store fetched emails
        for email in emails:
            email["user_id"] = user_id
            email["fetched_at"] = datetime.utcnow()
            await mongodb.gmail_fetched_emails.insert_one(email)
        
        return {"fetched": len(emails), "user_id": user_id}
    
    try:
        return asyncio.run(_fetch())
    except Exception as exc:
        logger.error(f"Gmail fetch failed: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        raise


@celery_app.task(bind=True, base=CallbackTask, max_retries=3, default_retry_delay=60, name="gmail_tasks.analyze_email")
def analyze_gmail_email_task(self, user_id: str, message_id: str):
    """
    Celery task for analyzing a Gmail email.
    
    Args:
        user_id: User ID who owns the Gmail account
        message_id: Gmail message ID to analyze
    """
    import asyncio
    from app.services.gmail_service import gmail_service
    from app.ml.email_parser import EmailParser
    from app.ml.risk_scorer import get_risk_scorer
    from app.database import get_mongodb_database
    from datetime import datetime
    import base64
    
    logger.info(f"Starting Gmail analysis task for message {message_id}")
    
    async def _analyze():
        email_raw = await gmail_service.get_email_by_id(user_id, message_id)
        if not email_raw:
            return {"status": "error", "message": "Failed to fetch email from Gmail"}
        
        raw_bytes = base64.urlsafe_b64decode(email_raw['raw'])
        
        parser = EmailParser(raw_bytes)
        parsed_email = parser.parse()
        
        risk_scorer = get_risk_scorer()
        analysis_result = risk_scorer.analyze(parsed_email)
        
        mongodb = get_mongodb_database()
        detailed_result = {
            "job_id": message_id,
            "user_id": user_id,
            "source": "gmail",
            "gmail_message_id": message_id,
            "email_metadata": {
                "subject": parsed_email.get("headers", {}).get("subject"),
                "sender": parsed_email.get("headers", {}).get("from"),
                "recipient": parsed_email.get("headers", {}).get("to"),
                "date": parsed_email.get("headers", {}).get("date"),
                "message_id": parsed_email.get("headers", {}).get("message_id")
            },
            "risk_assessment": {
                "overall_score": analysis_result["risk_score"],
                "category": analysis_result["threat_category"],
                "confidence": analysis_result["confidence"]
            },
            "findings": analysis_result["findings"],
            "links_analyzed": parsed_email.get("links", []),
            "attachments_analyzed": parsed_email.get("attachments", []),
            "risk_factors": analysis_result["risk_factors"],
            "ml_prediction": analysis_result["ml_prediction"],
            "created_at": datetime.utcnow()
        }
        
        result = await mongodb.analysis_results.insert_one(detailed_result)
        
        # Update queue status
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": user_id, "message_id": message_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "analysis_id": str(result.inserted_id),
                "risk_score": analysis_result["risk_score"],
                "threat_category": analysis_result["threat_category"]
            }}
        )
        
        logger.info(f"Gmail analysis completed for message {message_id}. Risk score: {analysis_result['risk_score']}")
        
        return {
            "status": "completed",
            "message_id": message_id,
            "risk_score": analysis_result["risk_score"],
            "threat_category": analysis_result["threat_category"],
            "analysis_id": str(result.inserted_id)
        }
    
    try:
        return asyncio.run(_analyze())
    except Exception as exc:
        logger.error(f"Gmail analysis failed for message {message_id}: {exc}")
        
        # Update queue status to failed
        try:
            mongodb = get_mongodb_database()
            mongodb.gmail_analysis_queue.update_one(
                {"user_id": user_id, "message_id": message_id},
                {"$set": {
                    "status": "failed",
                    "completed_at": datetime.utcnow(),
                    "error": str(exc)
                }}
            )
        except Exception as update_error:
            logger.error(f"Failed to update queue status: {update_error}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        raise


@celery_app.task(name="gmail_tasks.batch_analyze")
def batch_analyze_emails_task(user_id: str, message_ids: list):
    """
    Celery task to analyze multiple Gmail emails.
    
    Args:
        user_id: User ID who owns the Gmail account
        message_ids: List of Gmail message IDs to analyze
    """
    results = []
    
    for msg_id in message_ids:
        task = analyze_gmail_email_task.delay(user_id, msg_id)
        results.append({
            "message_id": msg_id,
            "task_id": task.id
        })
    
    return {
        "queued": len(results),
        "tasks": results
    }


@celery_app.task(name="gmail_tasks.sync_gmail")
def sync_gmail_task(user_id: str):
    """
    Celery task to sync Gmail account.
    
    Args:
        user_id: User ID who owns the Gmail account
    """
    return fetch_emails_task.delay(user_id, 100).id
