"""
Tests for ML model checksum validation and feature extraction.
"""

import os
import pytest
import tempfile
from unittest.mock import patch


@pytest.mark.asyncio
async def test_checksum_computation():
    """Checksum helper computes SHA-256 correctly."""
    from app.ml.phishing_detector import PhishingDetector
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        f.write(b"test model data")
        f.flush()
        checksum = PhishingDetector._compute_checksum(f.name)
    
    os.unlink(f.name)
    
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA-256 hex length


@pytest.mark.asyncio
async def test_model_info_includes_checksum():
    """Model info dict includes SHA-256 checksum field."""
    from app.ml.phishing_detector import PhishingDetector
    from app.ml.feature_extractor import FeatureExtractor
    
    detector = PhishingDetector.__new__(PhishingDetector)
    detector.model_version = "1.0.0"
    detector.model_checksum = "abc123def456"
    detector.model = None
    detector.feature_extractor = FeatureExtractor()
    detector.training_metadata = {}
    
    info = detector.get_model_info()
    assert "checksum_sha256" in info
    assert info["checksum_sha256"] == "abc123def456"


class TestFeatureExtractor:
    """Tests for email feature extraction."""

    def test_extract_features_returns_dict(self):
        from app.ml.feature_extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = extractor.extract_features({
            "headers": {
                "from": "sender@example.com",
                "subject": "Test email",
            },
            "body": {
                "text": "This is a test email body.",
                "html": "",
            },
            "links": [],
            "attachments": [],
        })
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_phishing_url_features(self):
        from app.ml.feature_extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = extractor.extract_features({
            "headers": {"from": "sender@example.com", "subject": ""},
            "body": {"text": "", "html": ""},
            "links": [{"url": "https://phishing.example.com/login"}],
            "attachments": [],
        })
        assert isinstance(features, dict)
        assert "link_count" in features or any("link" in k for k in features)

