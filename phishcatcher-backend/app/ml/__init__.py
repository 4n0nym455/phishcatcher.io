"""
PhishCatcher Machine Learning Module

This module contains all ML-related functionality for phishing detection.
"""

from app.ml.email_parser import EmailParser
from app.ml.feature_extractor import FeatureExtractor
from app.ml.phishing_detector import PhishingDetector
from app.ml.risk_scorer import RiskScorer

__all__ = [
    "EmailParser",
    "FeatureExtractor",
    "PhishingDetector",
    "RiskScorer",
]
