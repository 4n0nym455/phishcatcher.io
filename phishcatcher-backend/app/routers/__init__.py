"""
PhishCatcher API Routers

This module contains all API route handlers.
"""

from app.routers import auth, analysis, providers, admin, health, ml

__all__ = ["auth", "analysis", "providers", "admin", "health", "ml"]
