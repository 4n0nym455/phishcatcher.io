"""
PhishCatcher Celery Tasks

This module contains all background task definitions.
"""

from app.tasks.analysis import analyze_email_task, sync_gmail_task

__all__ = ["analyze_email_task", "sync_gmail_task"]
