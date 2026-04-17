"""
Analysis Tasks

This module contains Celery tasks for email analysis.
Simplified and properly handling sync/async operations.
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional

from celery import Task
from celery.signals import task_success, task_failure, task_retry

from app.tasks.celery_app import celery_app
from app.ml.email_parser import EmailParser
from app.ml.phishing_detector import get_phishing_detector
from app.services.threat_intel import get_threat_intel_service, transform_ti_for_storage
from app.database import get_mongodb_database
from app.config import get_settings
from app.models.analysis_job import AnalysisJob

logger = logging.getLogger(__name__)


def _update_job_status(job_id: str, status: str, **kwargs):
    """Update job status in PostgreSQL."""
    try:
        from app.database import get_db_session
        from sqlalchemy import select
        import uuid
        
        async def _update():
            async with get_db_session() as db:
                result = await db.execute(
                    select(AnalysisJob).where(AnalysisJob.id == uuid.UUID(job_id))
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = status
                    for key, value in kwargs.items():
                        if hasattr(job, key):
                            setattr(job, key, value)
                    await db.commit()
        
        asyncio.run(_update())
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")


def _save_to_mongodb(collection_name: str, document: dict) -> str:
    """Save document to MongoDB (sync wrapper)."""
    mongodb = get_mongodb_database()
    collection = mongodb[collection_name]
    
    if asyncio.get_event_loop().is_running():
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(collection.insert_one(document))
    else:
        result = asyncio.run(collection.insert_one(document))
    
    return str(result.inserted_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_email_task(self: Task, job_id: str, raw_email_bytes: bytes, 
                       user_id: Optional[str] = None):
    """
    Celery task for analyzing an email.
    
    Workflow:
    1. Parse email
    2. Run ML prediction
    3. Run Threat Intelligence
    4. Combine results and save
    """
    logger.info(f"Starting analysis for job {job_id}")
    settings = get_settings()
    
    try:
        _update_job_status(job_id, "processing", progress_percent=5, 
                          current_step="Parsing email")
        
        parser = EmailParser(raw_email_bytes)
        parsed_email = parser.parse()
        
        headers = parsed_email.get('headers', {})
        links = parsed_email.get('links', [])
        attachments = parsed_email.get('attachments', [])
        
        sender_email = headers.get('from', '')
        urls = [link.get('url', '') for link in links if link.get('url')]
        attachment_hashes = [a.get('hash', '') for a in attachments if a.get('hash')]
        
        _update_job_status(job_id, "processing", progress_percent=20,
                          current_step="Running ML analysis")
        
        detector = get_phishing_detector()
        ml_result = detector.predict(parsed_email)
        ml_score = ml_result.get('phishing_probability', 0.0)
        
        logger.info(f"ML done for {job_id}: prob={ml_score}")
        
        _update_job_status(job_id, "processing", progress_percent=40,
                          current_step="Running threat intelligence")
        
        threat_intel = get_threat_intel_service()
        try:
            ti_result = asyncio.run(threat_intel.analyze_email_threats(
                sender_email=sender_email,
                urls=urls,
                attachment_hashes=attachment_hashes
            ))
            ti_score = ti_result.get('overall_risk_score', 0.0) / 100.0
            ti_confidence = ti_result.get('confidence', 0.5)
        except Exception as e:
            logger.warning(f"TI failed for {job_id}: {e}")
            ti_result = {'overall_risk_score': 0, 'confidence': 0.5, 'indicators': [], 'warnings': [str(e)]}
            ti_score = 0.0
            ti_confidence = 0.5
        
        _update_job_status(job_id, "processing", progress_percent=80,
                          current_step="Calculating score")
        
        final_score = (settings.ML_WEIGHT * ml_score) + (settings.TI_WEIGHT * ti_score)
        
        if final_score >= 0.8:
            category = 'phishing'
        elif final_score >= 0.6:
            category = 'suspicious'
        elif final_score >= 0.4:
            category = 'caution'
        else:
            category = 'safe'
        
        confidence = (ml_result.get('confidence', 0.5) * settings.ML_WEIGHT + 
                      ti_confidence * settings.TI_WEIGHT)
        
        findings = _generate_findings(parsed_email, ml_result, ti_result)
        
        detailed_result = {
            "job_id": job_id,
            "user_id": user_id,
            "email_metadata": {
                "subject": headers.get("subject"),
                "sender": headers.get("from"),
                "recipient": headers.get("to"),
                "date": headers.get("date"),
                "message_id": headers.get("message_id")
            },
            "risk_assessment": {
                "overall_score": int(final_score * 100),
                "category": category,
                "confidence": confidence
            },
            "ml_analysis": {
                "phishing_probability": ml_score,
                "confidence": ml_result.get('confidence', 0.5),
                "model_used": ml_result.get('model_used', 'xgboost')
            },
            "threat_intelligence": transform_ti_for_storage(ti_result),
            "findings": findings,
            "links_analyzed": links,
            "attachments_analyzed": attachments,
            "created_at": datetime.utcnow()
        }
        
        mongodb_result_id = _save_to_mongodb("analysis_results", detailed_result)
        
        critical = sum(1 for f in findings if f.get('severity') == 'critical')
        high = sum(1 for f in findings if f.get('severity') == 'high')
        
        _update_job_status(
            job_id=job_id,
            status="completed",
            progress_percent=100,
            current_step="Complete",
            risk_score=int(final_score * 100),
            threat_category=category,
            confidence=confidence,
            findings_count=len(findings),
            critical_findings=critical,
            high_findings=high,
            mongodb_result_id=mongodb_result_id,
            ml_score=ml_score,
            ti_score=ti_score
        )
        
        logger.info(f"Analysis completed for {job_id}. Score: {final_score:.2f}")
        
        return {"job_id": job_id, "status": "completed", "risk_score": int(final_score * 100)}
        
    except Exception as exc:
        logger.error(f"Analysis failed for {job_id}: {exc}")
        _update_job_status(job_id, "failed", error_message=str(exc), retry_count=self.request.retries)
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        raise


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_gmail_task(self: Task, user_id: str, message_id: str):
    """Analyze a Gmail email."""
    logger.info(f"Starting Gmail analysis for message {message_id}")
    settings = get_settings()
    
    async def _analyze():
        from app.services.gmail_service import gmail_service
        
        email_raw = await gmail_service.get_email_by_id(user_id, message_id)
        if not email_raw:
            return {"status": "error", "message": "Failed to fetch email"}
        
        import base64
        raw_bytes = base64.urlsafe_b64decode(email_raw['raw'])
        
        parser = EmailParser(raw_bytes)
        parsed_email = parser.parse()
        
        headers = parsed_email.get('headers', {})
        links = parsed_email.get('links', [])
        attachments = parsed_email.get('attachments', [])
        
        sender_email = headers.get('from', '')
        urls = [link.get('url', '') for link in links if link.get('url')]
        
        detector = get_phishing_detector()
        ml_result = detector.predict(parsed_email)
        ml_score = ml_result.get('phishing_probability', 0.0)
        
        threat_intel = get_threat_intel_service()
        try:
            ti_result = await threat_intel.analyze_email_threats(
                sender_email=sender_email,
                urls=urls,
                attachment_hashes=attachment_hashes
            )
            ti_score = ti_result.get('overall_risk_score', 0.0) / 100.0
        except Exception as e:
            logger.warning(f"TI failed: {e}")
            ti_result = {'overall_risk_score': 0, 'indicators': [], 'warnings': []}
            ti_score = 0.0
        
        final_score = (settings.ML_WEIGHT * ml_score) + (settings.TI_WEIGHT * ti_score)
        
        if final_score >= 0.8:
            category = 'phishing'
        elif final_score >= 0.6:
            category = 'suspicious'
        elif final_score >= 0.4:
            category = 'caution'
        else:
            category = 'safe'
        
        findings = _generate_findings(parsed_email, ml_result, ti_result)
        
        mongodb = get_mongodb_database()
        detailed_result = {
            "job_id": message_id,
            "user_id": user_id,
            "source": "gmail",
            "gmail_message_id": message_id,
            "email_metadata": {
                "subject": headers.get("subject"),
                "sender": headers.get("from"),
                "date": headers.get("date")
            },
            "risk_assessment": {
                "overall_score": int(final_score * 100),
                "category": category
            },
            "ml_analysis": {"phishing_probability": ml_score},
            "threat_intelligence": transform_ti_for_storage(ti_result),
            "findings": findings,
            "created_at": datetime.utcnow()
        }
        
        result = await mongodb.analysis_results.insert_one(detailed_result)
        analysis_id = str(result.inserted_id)
        
        await mongodb.gmail_analysis_queue.update_one(
            {"user_id": user_id, "message_id": message_id},
            {"$set": {"status": "completed", "completed_at": datetime.utcnow(), "analysis_id": analysis_id}}
        )
        
        logger.info(f"Gmail analysis done for {message_id}")
        return {"status": "completed", "message_id": message_id}
    
    try:
        return asyncio.run(_analyze())
    except Exception as exc:
        logger.error(f"Gmail analysis failed for {message_id}: {exc}")
        
        async def _handle_error():
            mongodb = get_mongodb_database()
            await mongodb.gmail_analysis_queue.update_one(
                {"user_id": user_id, "message_id": message_id},
                {"$set": {"status": "failed", "error": str(exc)}}
            )
        
        try:
            asyncio.run(_handle_error())
        except Exception:
            pass
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        raise


def _generate_findings(parsed_email: dict, ml_result: dict, ti_result: dict) -> list:
    """Generate findings from analysis results."""
    findings = []
    finding_id = 0
    
    headers = parsed_email.get('headers', {})
    auth_results = headers.get('authentication_results', {})
    
    if ml_result.get('phishing_probability', 0) > 0.7:
        finding_id += 1
        severity = 'critical' if ml_result.get('phishing_probability', 0) > 0.9 else 'high'
        findings.append({
            'id': f'F{finding_id:03d}',
            'type': 'ml_detection',
            'severity': severity,
            'title': 'ML Phishing Detection',
            'description': f"Model detected {ml_result['phishing_probability']*100:.1f}% phishing probability"
        })
    
    if ti_result.get('indicators'):
        for indicator in ti_result['indicators'][:3]:
            finding_id += 1
            findings.append({
                'id': f'F{finding_id:03d}',
                'type': 'threat_intel',
                'severity': 'high',
                'title': 'Threat Intelligence Match',
                'description': indicator
            })
    
    if auth_results:
        if 'fail' in auth_results.get('spf', '').lower():
            finding_id += 1
            findings.append({
                'id': f'F{finding_id:03d}',
                'type': 'authentication',
                'severity': 'high',
                'title': 'SPF Failed',
                'description': 'Email failed SPF authentication'
            })
        if 'fail' in auth_results.get('dkim', '').lower():
            finding_id += 1
            findings.append({
                'id': f'F{finding_id:03d}',
                'type': 'authentication',
                'severity': 'medium',
                'title': 'DKIM Failed',
                'description': 'Email DKIM signature invalid'
            })
    
    return findings


@celery_app.task(name="analysis.sync_gmail")
def sync_gmail_task(provider_id: str, user_id: str, max_emails: int = 50):
    """Sync emails from Gmail provider."""
    logger.info(f"Starting Gmail sync for provider {provider_id}")
    
    async def _sync():
        from app.services.gmail_service import gmail_service
        from app.database import get_db_session
        from sqlalchemy import select
        from app.models.email_provider import EmailProvider
        import uuid
        
        async with get_db_session() as db:
            result = await db.execute(
                select(EmailProvider).where(EmailProvider.id == provider_id)
            )
            provider = result.scalar_one_or_none()
            
            if not provider or not provider.is_active:
                return {"status": "error", "message": "Provider not found"}
            
            credentials = await gmail_service.get_gmail_credentials(user_id)
            if not credentials:
                return {"status": "error", "message": "Invalid credentials"}
            
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=credentials)
            
            results = service.users().messages().list(
                userId='me', maxResults=max_emails, q='in:inbox'
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages")
            
            mongodb = get_mongodb_database()
            for msg in messages:
                await mongodb.gmail_analysis_queue.update_one(
                    {"user_id": user_id, "message_id": msg['id']},
                    {"$setOnInsert": {
                        "user_id": user_id,
                        "message_id": msg['id'],
                        "status": "pending",
                        "created_at": datetime.utcnow()
                    }},
                    upsert=True
                )
            
            return {"status": "completed", "emails_found": len(messages)}
    
    return asyncio.run(_sync())