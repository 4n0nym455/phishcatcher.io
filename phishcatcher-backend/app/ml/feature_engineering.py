"""
Feature Engineering Module

This module provides engineered features for email phishing detection:
- URL-based features: count, IP-based URLs, domain entropy, suspicious TLDs
- Text-based indicators: urgency keywords, phishing phrases
- Structural features: HTML vs plain text, special characters
"""

import re
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from collections import Counter

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Engineer features from email content for phishing detection."""
    
    # Urgency keywords commonly used in phishing
    URGENCY_KEYWORDS = [
        'urgent', 'immediate', 'action required', 'verify now', 'account suspended',
        'limited time', 'expires soon', 'confirm now', 'update required',
        'security alert', 'unusual activity', 'suspicious activity', 'verify account',
        'click here', 'act now', 'don\'t delay', 'final notice', 'warning',
        'deadline', 'last chance', 'expiring', 'terminate', 'suspend'
    ]
    
    # Phishing-specific phrases
    PHISHING_PHRASES = [
        'verify your identity', 'confirm your password', 'update your information',
        'suspended account', 'unauthorized access', 'security breach',
        'login attempt', 'password expired', 'account locked', 'verify your account',
        'unusual sign-in', 'suspicious activity', 'confirm your identity',
        'update payment', 'billing information', 'confirm your email',
        'click below', 'login now', 'sign in immediately'
    ]
    
    # Financial keywords
    FINANCIAL_KEYWORDS = [
        'bank', 'credit card', 'payment', 'invoice', 'transaction', 'refund',
        'billing', 'subscription', 'paypal', 'money', 'transfer', 'account',
        'balance', 'withdraw', 'deposit', 'ssn', 'social security', 'routing',
        'wire transfer', 'western union', 'gift card', 'bitcoin', 'cryptocurrency'
    ]
    
    # Suspicious TLDs
    SUSPICIOUS_TLDS = [
        'tk', 'ml', 'ga', 'cf', 'gq', 'xyz', 'top', 'click', 'link', 'work',
        'loan', 'online', 'site', 'club', 'win', 'download', 'bid', 'review',
        'country', 'kim', 'racing', 'science', 'party', 'cricket', 'science',
        'accountant', 'dating', 'stream', 'watch', 'ninja', 'vip', 'fail'
    ]
    
    # Brand impersonation keywords
    BRAND_KEYWORDS = [
        'amazon', 'paypal', 'netflix', 'microsoft', 'apple', 'google',
        'facebook', 'instagram', 'twitter', 'linkedin', 'bank of america',
        'wells fargo', 'chase', 'citibank', 'american express', 'visa', 'mastercard',
        'dropbox', 'icloud', 'adobe', 'shopify', 'uber', 'lyft', 'github',
        'whatsapp', 'telegram', 'discord', 'slack', 'zoom'
    ]
    
    def __init__(self):
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
            re.IGNORECASE
        )
        self.feature_names = self._get_feature_names()
    
    def extract_all_features(
        self,
        subject: str,
        body: str,
        html: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Extract all engineered features from email.
        
        Args:
            subject: Email subject
            body: Email body (plain text)
            html: Optional HTML content
            raw_text: Optional raw text before preprocessing
            
        Returns:
            Dictionary of feature names and values
        """
        features = {}
        
        text_content = f"{subject} {body}".lower()
        
        features.update(self._extract_url_features(text_content))
        
        features.update(self._extract_text_indicators(text_content))
        
        features.update(self._extract_structural_features(subject, body, html))
        
        features.update(self._extract_sender_features(text_content))
        
        return features
    
    def _extract_url_features(self, text: str) -> Dict[str, float]:
        """Extract URL-based features."""
        features = {}
        
        urls = self.url_pattern.findall(text)
        features['url_count'] = len(urls)
        
        ip_based_count = 0
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
                    ip_based_count += 1
            except Exception:
                pass
        features['url_ip_based_count'] = ip_based_count
        features['url_has_ip_based'] = 1.0 if ip_based_count > 0 else 0.0
        
        domains = []
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                if domain:
                    domains.append(domain)
            except Exception:
                pass
        
        if domains:
            all_domains_str = ''.join(domains)
            features['url_domain_entropy'] = self._calculate_entropy(all_domains_str)
        else:
            features['url_domain_entropy'] = 0.0
        
        suspicious_tld_count = 0
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                if '.' in domain:
                    tld = domain.split('.')[-1].lower()
                    if tld in self.SUSPICIOUS_TLDS:
                        suspicious_tld_count += 1
            except Exception:
                pass
        features['url_suspicious_tld_count'] = suspicious_tld_count
        features['url_has_suspicious_tld'] = 1.0 if suspicious_tld_count > 0 else 0.0
        
        suspicious_count = sum(1 for url in urls if self._is_suspicious_url(url))
        features['url_suspicious_count'] = suspicious_count
        features['url_suspicious_ratio'] = suspicious_count / max(len(urls), 1)
        
        url_lengths = [len(url) for url in urls]
        features['url_avg_length'] = sum(url_lengths) / max(len(url_lengths), 1) if url_lengths else 0.0
        features['url_max_length'] = max(url_lengths) if url_lengths else 0.0
        
        return features
    
    def _is_suspicious_url(self, url: str) -> bool:
        """Check if URL has suspicious characteristics."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            suspicious_patterns = [
                r'\d{8,}',  # Long number sequences
                r'[a-zA-Z]{20,}',  # Long domain names
                r'bit\.ly|tinyurl|goo\.gl|t\.co',  # URL shorteners
                r'@',  # URL with @
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return True
            
            return False
        except Exception:
            return False
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        counter = Counter(text)
        length = len(text)
        
        entropy = 0.0
        for count in counter.values():
            probability = count / length
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _extract_text_indicators(self, text: str) -> Dict[str, float]:
        """Extract text-based indicator features."""
        features = {}
        
        urgency_count = sum(1 for kw in self.URGENCY_KEYWORDS if kw in text)
        features['text_urgency_keyword_count'] = urgency_count
        features['text_has_urgency_keywords'] = 1.0 if urgency_count > 0 else 0.0
        
        phrase_count = sum(1 for phrase in self.PHISHING_PHRASES if phrase in text)
        features['text_phishing_phrase_count'] = phrase_count
        features['text_has_phishing_phrases'] = 1.0 if phrase_count > 0 else 0.0
        
        financial_count = sum(1 for kw in self.FINANCIAL_KEYWORDS if kw in text)
        features['text_financial_keyword_count'] = financial_count
        features['text_has_financial_keywords'] = 1.0 if financial_count > 0 else 0.0
        
        brand_count = sum(1 for brand in self.BRAND_KEYWORDS if brand in text)
        features['text_brand_keyword_count'] = brand_count
        features['text_has_brand_keywords'] = 1.0 if brand_count > 0 else 0.0
        
        features['text_exclamation_count'] = text.count('!')
        features['text_question_count'] = text.count('?')
        features['text_dollar_count'] = text.count('$')
        
        features['text_all_caps_words'] = len(re.findall(r'\b[A-Z]{3,}\b', text))
        
        words = text.split()
        if words:
            word_lengths = [len(w) for w in words]
            features['text_avg_word_length'] = sum(word_lengths) / len(word_lengths)
        else:
            features['text_avg_word_length'] = 0.0
        
        features['text_unique_word_ratio'] = len(set(words)) / max(len(words), 1)
        
        return features
    
    def _extract_structural_features(
        self,
        subject: str,
        body: str,
        html: Optional[str]
    ) -> Dict[str, float]:
        """Extract structural features."""
        features = {}
        
        features['struct_subject_length'] = len(subject)
        features['struct_body_length'] = len(body)
        features['struct_total_length'] = len(subject) + len(body)
        
        features['struct_has_html'] = 1.0 if html and len(html) > 0 else 0.0
        
        if html:
            features['struct_html_length'] = len(html)
            features['struct_html_to_text_ratio'] = len(html) / max(len(body), 1)
            features['struct_has_form'] = 1.0 if '<form' in html.lower() else 0.0
            features['struct_has_input'] = 1.0 if '<input' in html.lower() else 0.0
            features['struct_has_script'] = 1.0 if '<script' in html.lower() else 0.0
            features['struct_has_iframe'] = 1.0 if '<iframe' in html.lower() else 0.0
            features['struct_has_hidden'] = 1.0 if 'display:none' in html.lower() or 'visibility:hidden' in html.lower() else 0.0
        else:
            features['struct_html_length'] = 0.0
            features['struct_html_to_text_ratio'] = 0.0
            features['struct_has_form'] = 0.0
            features['struct_has_input'] = 0.0
            features['struct_has_script'] = 0.0
            features['struct_has_iframe'] = 0.0
            features['struct_has_hidden'] = 0.0
        
        special_chars = re.findall(r'[^a-zA-Z0-9\s]', body)
        features['struct_special_char_count'] = len(special_chars)
        features['struct_special_char_ratio'] = len(special_chars) / max(len(body), 1)
        
        num_count = len(re.findall(r'\d+', body))
        features['struct_digit_count'] = num_count
        features['struct_digit_ratio'] = num_count / max(len(body), 1)
        
        if body:
            lines = body.split('\n')
            features['struct_line_count'] = len(lines)
            features['struct_empty_line_ratio'] = sum(1 for l in lines if not l.strip()) / max(len(lines), 1)
        else:
            features['struct_line_count'] = 0.0
            features['struct_empty_line_ratio'] = 0.0
        
        generic_greetings = ['dear customer', 'dear user', 'dear member', 'dear client', 'dear user']
        features['struct_generic_greeting'] = 1.0 if any(g in body.lower() for g in generic_greetings) else 0.0
        
        return features
    
    def _extract_sender_features(self, text: str) -> Dict[str, float]:
        """Extract sender-related features."""
        features = {}
        
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        emails = email_pattern.findall(text)
        
        features['sender_email_count'] = len(emails)
        
        if emails:
            first_email = emails[0]
            domain = first_email.split('@')[1] if '@' in first_email else ''
            
            features['sender_domain_has_number'] = 1.0 if any(c.isdigit() for c in domain) else 0.0
            
            if '.' in domain:
                tld = domain.split('.')[-1]
                features['sender_suspicious_tld'] = 1.0 if tld in self.SUSPICIOUS_TLDS else 0.0
            else:
                features['sender_suspicious_tld'] = 0.0
            
            features['sender_domain_entropy'] = self._calculate_entropy(domain)
        else:
            features['sender_domain_has_number'] = 0.0
            features['sender_suspicious_tld'] = 0.0
            features['sender_domain_entropy'] = 0.0
        
        return features
    
    def _get_feature_names(self) -> List[str]:
        """Get list of all feature names."""
        return [
            # URL features
            'url_count', 'url_ip_based_count', 'url_has_ip_based',
            'url_domain_entropy', 'url_suspicious_tld_count', 'url_has_suspicious_tld',
            'url_suspicious_count', 'url_suspicious_ratio', 'url_avg_length', 'url_max_length',
            
            # Text indicators
            'text_urgency_keyword_count', 'text_has_urgency_keywords',
            'text_phishing_phrase_count', 'text_has_phishing_phrases',
            'text_financial_keyword_count', 'text_has_financial_keywords',
            'text_brand_keyword_count', 'text_has_brand_keywords',
            'text_exclamation_count', 'text_question_count', 'text_dollar_count',
            'text_all_caps_words', 'text_avg_word_length', 'text_unique_word_ratio',
            
            # Structural features
            'struct_subject_length', 'struct_body_length', 'struct_total_length',
            'struct_has_html', 'struct_html_length', 'struct_html_to_text_ratio',
            'struct_has_form', 'struct_has_input', 'struct_has_script',
            'struct_has_iframe', 'struct_has_hidden',
            'struct_special_char_count', 'struct_special_char_ratio',
            'struct_digit_count', 'struct_digit_ratio',
            'struct_line_count', 'struct_empty_line_ratio', 'struct_generic_greeting',
            
            # Sender features
            'sender_email_count', 'sender_domain_has_number',
            'sender_suspicious_tld', 'sender_domain_entropy'
        ]
    
    def get_feature_vector(
        self,
        subject: str,
        body: str,
        html: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> List[float]:
        """
        Get feature vector as a list.
        
        Args:
            subject: Email subject
            body: Email body
            html: Optional HTML content
            raw_text: Optional raw text
            
        Returns:
            List of feature values
        """
        features = self.extract_all_features(subject, body, html, raw_text)
        return [features.get(name, 0.0) for name in self.feature_names]
    
    def get_feature_importance_names(self) -> List[str]:
        """Get feature names for model."""
        return self.feature_names.copy()


def extract_features(
    subject: str,
    body: str,
    html: Optional[str] = None
) -> Dict[str, float]:
    """
    Quick feature extraction function.
    
    Usage:
        features = extract_features("Subject", "Email body", html_content)
    """
    engineer = FeatureEngineer()
    return engineer.extract_all_features(subject, body, html)