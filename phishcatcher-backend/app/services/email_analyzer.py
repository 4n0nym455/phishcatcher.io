"""
Email Analyzer Service

This module provides email content analysis for phishing detection.
"""

import re
from typing import Dict, Any

def analyze_email_content(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze email content for phishing indicators.
    
    Args:
        email_data: Dictionary containing email content (subject, body, from, etc.)
    
    Returns:
        Dictionary with analysis results including phishing indicators
    """
    subject = email_data.get('subject', '')
    body = email_data.get('body', '')
    from_email = email_data.get('from', '')
    
    # Basic phishing indicators
    indicators = {
        'suspicious_links': _check_suspicious_links(body),
        'urgent_language': _check_urgent_language(subject + ' ' + body),
        'suspicious_sender': _check_suspicious_sender(from_email),
        'attachment_risk': _check_attachment_risk(body),
        'brand_impersonation': _check_brand_impersonation(subject + ' ' + body),
    }
    
    # Calculate risk score
    risk_score = sum(indicators.values()) / len(indicators)
    
    # Determine if it's phishing
    is_phishing = risk_score > 0.5  # Threshold can be adjusted
    
    return {
        'is_phishing': is_phishing,
        'risk_score': risk_score,
        'indicators': indicators,
        'analysis': {
            'suspicious_elements': [k for k, v in indicators.items() if v],
            'confidence': 'high' if risk_score > 0.7 else 'medium' if risk_score > 0.3 else 'low'
        }
    }

def _check_suspicious_links(text: str) -> float:
    """Check for suspicious links in email content."""
    suspicious_patterns = [
        r'http[s]?://bit\.ly',
        r'http[s]?://tinyurl\.com',
        r'http[s]?://goo\.gl',
        r'http[s]?://t\.co',
        r'click here',
        r'verify now',
        r'urgent action',
        r'account suspended',
        r'limited time',
    ]
    
    score = 0.0
    for pattern in suspicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 0.2
    
    return min(score, 1.0)

def _check_urgent_language(text: str) -> float:
    """Check for urgent or threatening language."""
    urgent_words = [
        'urgent', 'immediate', 'action required', 'suspend', 'terminate',
        'expire', 'limited time', 'act now', 'verify immediately', 'warning'
    ]
    
    count = sum(1 for word in urgent_words if word in text.lower())
    return min(count * 0.1, 1.0)

def _check_suspicious_sender(email: str) -> float:
    """Check if sender email looks suspicious."""
    suspicious_indicators = [
        r'\d+@',  # Numbers in email
        r'noreply@',  # Generic noreply
        r'.+@.*\.tk$',  # Suspicious TLDs
        r'.+@.*\.ml$',
        r'.+@.*\.ga$',
        r'@.*\d{3,}',  # Domains with many numbers
    ]
    
    score = 0.0
    for pattern in suspicious_indicators:
        if re.search(pattern, email, re.IGNORECASE):
            score += 0.3
    
    return min(score, 1.0)

def _check_attachment_risk(text: str) -> float:
    """Check for risky attachment mentions."""
    risky_attachments = [
        '.exe', '.zip', '.rar', '.scr', '.bat', '.com', '.pif',
        'invoice', 'receipt', 'payment', 'document', 'shipping'
    ]
    
    count = sum(1 for ext in risky_attachments if ext in text.lower())
    return min(count * 0.2, 1.0)

def _check_brand_impersonation(text: str) -> float:
    """Check for brand impersonation attempts."""
    brands = [
        'amazon', 'paypal', 'netflix', 'microsoft', 'apple', 'google',
        'facebook', 'instagram', 'twitter', 'linkedin', 'bank', 'wells fargo',
        'chase', 'citibank', 'american express'
    ]
    
    # Check if brand names appear with suspicious context
    suspicious_contexts = [
        'verify your account', 'update payment', 'suspended account',
        'unusual activity', 'security alert', 'billing issue'
    ]
    
    score = 0.0
    text_lower = text.lower()
    
    for brand in brands:
        if brand in text_lower:
            for context in suspicious_contexts:
                if context in text_lower:
                    score += 0.3
                    break
    
    return min(score, 1.0)
