"""
Email Analyzer Service

This module provides comprehensive email analysis for phishing detection,
combining ML models with Threat Intelligence APIs.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.services.threat_intel import get_threat_intel_service
from app.ml.text_classifier import get_text_classifier
from app.ml.phishing_detector import get_phishing_detector
from app.ml.ensemble_detector import get_ensemble_detector
from app.ml.email_parser import EmailParser

logger = logging.getLogger(__name__)


class EmailAnalyzer:
    """
    Comprehensive email analyzer combining ML and Threat Intelligence.
    
    Analysis flow:
    1. Parse email with EmailParser
    2. Extract URLs and attachment hashes
    3. Run Threat Intelligence checks (async)
    4. Run ML classifiers (text + feature)
    5. Combine results using ensemble weighting
    """
    
    def __init__(self):
        self.threat_intel = get_threat_intel_service()
        self.text_classifier = get_text_classifier()
        self.feature_detector = get_phishing_detector()
        self.ensemble_detector = get_ensemble_detector()
    
    def analyze_email(self, raw_email: bytes) -> Dict[str, Any]:
        """
        Analyze a raw email for phishing.
        
        Args:
            raw_email: Raw email bytes
            
        Returns:
            Comprehensive analysis result
        """
        try:
            parser = EmailParser(raw_email)
            parsed_email = parser.parse()
            
            headers = parsed_email.get('headers', {})
            body = parsed_email.get('body', {})
            links = parsed_email.get('links', [])
            attachments = parsed_email.get('attachments', [])
            
            sender_email = headers.get('from_address', '')
            urls = [link.get('url', '') for link in links if link.get('url')]
            attachment_hashes = [
                a.get('hash_sha256', a.get('hash_md5', ''))
                for a in attachments
                if a.get('hash_sha256') or a.get('hash_md5')
            ]
            
            result = self.ensemble_detector.analyze(
                parsed_email=parsed_email,
                sender_email=sender_email,
                urls=urls,
                attachment_hashes=attachment_hashes
            )
            
            result['parsed_email'] = {
                'subject': headers.get('subject', ''),
                'sender': sender_email,
                'urls_found': len(urls),
                'attachments_found': len(attachments)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Email analysis error: {e}")
            return {
                'is_phishing': False,
                'phishing_probability': 0.0,
                'risk_category': 'error',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def analyze_content(
        self,
        subject: str,
        body: str,
        sender_email: str,
        urls: Optional[List[str]] = None,
        attachment_hashes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze email content without raw email bytes.
        
        Args:
            subject: Email subject
            body: Email body (text)
            sender_email: Sender email address
            urls: Optional list of URLs
            attachment_hashes: Optional list of attachment hashes
            
        Returns:
            Analysis result
        """
        urls = urls or []
        attachment_hashes = attachment_hashes or []
        
        parsed_email = {
            'headers': {
                'subject': subject,
                'from_address': sender_email,
                'sender_domain': self._extract_domain(sender_email),
                'authentication_results': {}
            },
            'body': {
                'text': body,
                'text_length': len(body),
                'has_text': bool(body),
                'html': '',
                'html_length': 0,
                'has_html': False
            },
            'links': [],
            'attachments': [],
            'metadata': {
                'is_multipart': False,
                'received_count': 0
            }
        }
        
        result = self.ensemble_detector.analyze(
            parsed_email=parsed_email,
            sender_email=sender_email,
            urls=urls,
            attachment_hashes=attachment_hashes
        )
        
        result['parsed_email'] = {
            'subject': subject,
            'sender': sender_email,
            'urls_found': len(urls),
            'attachments_found': len(attachment_hashes)
        }
        
        return result
    
    @staticmethod
    def _extract_domain(email: str) -> str:
        """Extract domain from email."""
        if '@' in email:
            return email.split('@')[1].lower()
        return ''
    
    @staticmethod
    def _extract_urls_from_text(text: str) -> List[str]:
        """Extract URLs from text content."""
        url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            re.IGNORECASE
        )
        return url_pattern.findall(text)


_email_analyzer_instance: Optional[EmailAnalyzer] = None


def get_email_analyzer() -> EmailAnalyzer:
    """Get singleton instance of email analyzer."""
    global _email_analyzer_instance
    if _email_analyzer_instance is None:
        _email_analyzer_instance = EmailAnalyzer()
    return _email_analyzer_instance


def analyze_email_content(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Use get_email_analyzer().analyze_content() instead.
    """
    analyzer = get_email_analyzer()
    
    subject = email_data.get('subject', '')
    body = email_data.get('body', '')
    from_email = email_data.get('from', '')
    
    urls = email_data.get('urls', [])
    if not urls:
        urls = analyzer._extract_urls_from_text(body)
    
    return analyzer.analyze_content(
        subject=subject,
        body=body,
        sender_email=from_email,
        urls=urls
    )