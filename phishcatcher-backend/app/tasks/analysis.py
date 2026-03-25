"""
Analysis Tasks

This module contains Celery tasks for email analysis and Gmail sync.
"""

import logging
from datetime import datetime
from typing import Optional

from app.tasks.celery_app import celery_app
from app.ml.email_parser import EmailParser
from app.ml.risk_scorer import get_risk_scorer
from app.database import get_mongodb_database
from app.config import get_settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_email_task(self, job_id: str, raw_email_bytes: bytes, 
                       user_id: Optional[str] = None):
    """
    Celery task for analyzing an email.
    
    Args:
        job_id: Analysis job ID
        raw_email_bytes: Raw email content as bytes
        user_id: User ID who initiated the analysis
    """
    logger.info(f"Starting analysis task for job {job_id}")
    
    try:
        # Update job status to processing
        _update_job_status(job_id, "processing", progress_percent=10, 
                          current_step="Parsing email")
        
        # Parse email
        parser = EmailParser(raw_email_bytes)
        parsed_email = parser.parse()
        
        _update_job_status(job_id, "processing", progress_percent=30,
                          current_step="Analyzing content")
        
        # Run risk analysis
        risk_scorer = get_risk_scorer()
        analysis_result = risk_scorer.analyze(parsed_email)
        
        _update_job_status(job_id, "processing", progress_percent=70,
                          current_step="Saving results")
        
        # Save detailed results to MongoDB
        mongodb = get_mongodb_database()
        detailed_result = {
            "job_id": job_id,
            "user_id": user_id,
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
        
        result_doc = mongodb.analysis_results.insert_one(detailed_result)
        mongodb_result_id = str(result_doc.inserted_id)
        
        # Update job with results
        _update_job_status(
            job_id=job_id,
            status="completed",
            progress_percent=100,
            current_step="Analysis complete",
            risk_score=analysis_result["risk_score"],
            threat_category=analysis_result["threat_category"],
            confidence=analysis_result["confidence"],
            findings_count=analysis_result["findings_count"],
            critical_findings=analysis_result["critical_findings"],
            high_findings=analysis_result["high_findings"],
            medium_findings=analysis_result["medium_findings"],
            low_findings=analysis_result["low_findings"],
            mongodb_result_id=mongodb_result_id
        )
        
        logger.info(f"Analysis completed for job {job_id}. Risk score: {analysis_result['risk_score']}")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "risk_score": analysis_result["risk_score"],
            "threat_category": analysis_result["threat_category"]
        }
        
    except Exception as exc:
        logger.error(f"Analysis failed for job {job_id}: {exc}")
        
        # Update job status to failed
        _update_job_status(
            job_id=job_id,
            status="failed",
            error_message=str(exc),
            retry_count=self.request.retries
        )
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying analysis for job {job_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
        raise


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def sync_gmail_task(self, provider_id: str, user_id: str, max_emails: int = 100):
    """
    Celery task for syncing emails from Gmail.
    
    Args:
        provider_id: Email provider ID
        user_id: User ID
        max_emails: Maximum emails to sync
    """
    import asyncio
    from app.services.gmail import GmailServiceFactory
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database import get_db_session
    from app.models.email_provider import EmailProvider
    from app.models.analysis_job import AnalysisJob
    
    logger.info(f"Starting Gmail sync for provider {provider_id}")
    
    async def _sync():
        async with get_db_session() as db:
            # Get provider
            result = await db.execute(
                select(EmailProvider).where(EmailProvider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider or not provider.is_active:
                logger.warning(f"Provider {provider_id} not found or inactive")
                return {"status": "error", "message": "Provider not found or inactive"}
            
            # Create Gmail service
            gmail_service = GmailServiceFactory.from_provider(provider)
            
            if not gmail_service.is_token_valid():
                logger.warning(f"Invalid token for provider {provider_id}")
                return {"status": "error", "message": "Invalid or expired token"}
            
            try:
                # Fetch emails
                fetch_result = await gmail_service.fetch_emails(
                    max_results=max_emails,
                    query=provider.sync_filter or 'in:inbox'
                )
                
                emails = fetch_result.get('emails', [])
                logger.info(f"Fetched {len(emails)} emails from Gmail")
                
                # Create analysis jobs for new emails
                analysis_jobs_created = 0
                
                for email_data in emails:
                    # Check if email already analyzed
                    existing = await db.execute(
                        select(AnalysisJob).where(
                            AnalysisJob.provider_id == provider_id,
                            AnalysisJob.external_message_id == email_data['id']
                        )
                    )
                    
                    if existing.scalar_one_or_none():
                        continue
                    
                    # Create analysis job
                    job = AnalysisJob(
                        user_id=user_id,
                        source_type="gmail",
                        provider_id=provider_id,
                        external_message_id=email_data['id'],
                        file_name=email_data.get('headers', {}).get('subject', 'No Subject'),
                        status="pending"
                    )
                    
                    db.add(job)
                    await db.flush()
                    
                    # Queue analysis task
                    raw_email = email_data.get('raw')
                    if raw_email:
                        analyze_email_task.delay(str(job.id), raw_email, user_id)
                        analysis_jobs_created += 1
                
                # Update provider last sync
                provider.last_sync_at = datetime.utcnow()
                provider.is_connected = True
                provider.connection_error = None
                
                await db.commit()
                
                logger.info(f"Gmail sync completed. Created {analysis_jobs_created} analysis jobs")
                
                return {
                    "status": "success",
                    "emails_fetched": len(emails),
                    "analysis_jobs_created": analysis_jobs_created
                }
                
            except Exception as e:
                logger.error(f"Gmail sync error: {e}")
                provider.is_connected = False
                provider.connection_error = str(e)
                provider.last_error_at = datetime.utcnow()
                await db.commit()
                raise
    
    try:
        return asyncio.run(_sync())
    except Exception as exc:
        logger.error(f"Sync failed for provider {provider_id}: {exc}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        raise


def _update_job_status(job_id: str, status: str, **kwargs):
    """
    Update analysis job status in database.
    
    This is a synchronous helper function for Celery tasks.
    """
    import asyncio
    from sqlalchemy import select, update
    from app.database import get_db_session
    from app.models.analysis_job import AnalysisJob
    
    async def _update():
        async with get_db_session() as db:
            update_data = {"status": status}
            
            if status == "processing":
                update_data["started_at"] = datetime.utcnow()
            elif status in ["completed", "failed"]:
                update_data["completed_at"] = datetime.utcnow()
            
            # Add additional fields
            for key, value in kwargs.items():
                if hasattr(AnalysisJob, key):
                    update_data[key] = value
            
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == job_id)
                .values(**update_data)
            )
            await db.commit()
    
    try:
        asyncio.run(_update())
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
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
        
        mongodb.analysis_results.insert_one(detailed_result)
        
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": user_id, "message_id": message_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "analysis_id": str(detailed_result["_id"]),
                "risk_score": analysis_result["risk_score"],
                "threat_category": analysis_result["threat_category"]
            }}
        )
        
        logger.info(f"Gmail analysis completed for message {message_id}. Risk score: {analysis_result['risk_score']}")
        
        return {
            "status": "completed",
            "message_id": message_id,
            "risk_score": analysis_result["risk_score"],
            "threat_category": analysis_result["threat_category"]
        }
    
    try:
        return asyncio.run(_analyze())
    except Exception as exc:
        logger.error(f"Gmail analysis failed for message {message_id}: {exc}")
        try:
            from app.database import get_mongodb_database
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
