"""
Feature Extractor Module

This module extracts ML features from parsed email data for phishing detection.
"""

import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract ML features from parsed email data."""
    
    # Urgency keywords commonly used in phishing
    URGENCY_KEYWORDS = [
        'urgent', 'immediate', 'action required', 'verify now', 'account suspended',
        'limited time', 'expires soon', 'confirm now', 'update required',
        'security alert', 'unusual activity', 'suspicious activity', 'verify account',
        'click here', 'act now', 'don\'t delay', 'final notice', 'warning'
    ]
    
    # Suspicious phrases
    SUSPICIOUS_PHRASES = [
        'verify your identity', 'confirm your password', 'update your information',
        'suspended account', 'unauthorized access', 'security breach',
        'login attempt', 'password expired', 'account locked'
    ]
    
    # Brand impersonation keywords
    BRAND_KEYWORDS = [
        'amazon', 'paypal', 'netflix', 'microsoft', 'apple', 'google',
        'facebook', 'instagram', 'twitter', 'linkedin', 'bank of america',
        'wells fargo', 'chase', 'citibank', 'american express', 'visa', 'mastercard'
    ]
    
    # Suspicious TLDs (now handled by TI, but keep for local heuristic)
    SUSPICIOUS_TLDS = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.click', '.link']
    
    # Financial keywords (ML-only detection - reputation handled by TI)
    FINANCIAL_KEYWORDS = [
        'bank', 'credit card', 'payment', 'invoice', 'transaction', 'refund',
        'billing', 'subscription', 'paypal', 'money', 'transfer', 'account',
        'balance', 'withdraw', 'deposit', 'ssn', 'social security'
    ]
    
    def __init__(self):
        """Initialize feature extractor."""
        self.feature_names = self._get_feature_names()
    
    def extract_features(self, parsed_email: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract all features from parsed email.
        
        Args:
            parsed_email: Parsed email data from EmailParser
            
        Returns:
            Dictionary of feature names and values
        """
        features = {}
        
        # Extract header features
        features.update(self._extract_header_features(parsed_email.get('headers', {})))
        
        # Extract content features
        features.update(self._extract_content_features(parsed_email.get('body', {})))
        
        # Extract link features
        features.update(self._extract_link_features(parsed_email.get('links', [])))
        
        # Extract attachment features
        features.update(self._extract_attachment_features(parsed_email.get('attachments', [])))
        
        # Extract metadata features
        features.update(self._extract_metadata_features(parsed_email.get('metadata', {})))
        
        return features
    
    def _extract_header_features(self, headers: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from email headers."""
        features = {}
        
        # Authentication results
        auth_results = headers.get('authentication_results', {})
        features['spf_pass'] = 1.0 if auth_results.get('spf') == 'pass' else 0.0
        features['dkim_pass'] = 1.0 if auth_results.get('dkim') == 'pass' else 0.0
        features['dmarc_pass'] = 1.0 if auth_results.get('dmarc') == 'pass' else 0.0
        
        # Authentication failures are strong phishing indicators
        features['spf_fail'] = 1.0 if auth_results.get('spf') == 'fail' else 0.0
        features['dkim_fail'] = 1.0 if auth_results.get('dkim') == 'fail' else 0.0
        features['dmarc_fail'] = 1.0 if auth_results.get('dmarc') == 'fail' else 0.0
        
        # Reply-to mismatch
        features['reply_to_mismatch'] = 1.0 if headers.get('reply_to_mismatch', False) else 0.0
        
        # Domain features
        sender_domain = headers.get('sender_domain', '')
        return_path_domain = headers.get('return_path_domain', '')
        features['domain_mismatch'] = 1.0 if sender_domain != return_path_domain and return_path_domain else 0.0
        
        # Subject features
        subject = headers.get('subject', '')
        features['subject_length'] = len(subject)
        features['subject_has_exclamation'] = 1.0 if '!' in subject else 0.0
        features['subject_has_dollar'] = 1.0 if '$' in subject else 0.0
        features['subject_all_caps_words'] = len(re.findall(r'\b[A-Z]{3,}\b', subject))
        
        return features
    
    def _extract_content_features(self, body: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from email body content (ML-only features)."""
        features = {}
        
        text = body.get('text', '')
        html = body.get('html', '')
        content = f"{text} {html}".lower()
        
        # Content length features
        features['text_length'] = body.get('text_length', 0)
        features['html_length'] = body.get('html_length', 0)
        features['has_html'] = 1.0 if body.get('has_html', False) else 0.0
        features['has_text'] = 1.0 if body.get('has_text', False) else 0.0
        
        # HTML to text ratio (phishing often has high HTML ratio)
        if features['text_length'] > 0:
            features['html_to_text_ratio'] = features['html_length'] / features['text_length']
        else:
            features['html_to_text_ratio'] = 0.0
        
        # Urgency keywords (ML-only detection)
        features['urgency_keywords_count'] = sum(1 for kw in self.URGENCY_KEYWORDS if kw in content)
        features['urgency_keywords_present'] = 1.0 if features['urgency_keywords_count'] > 0 else 0.0
        
        # Suspicious phrases (ML-only detection)
        features['suspicious_phrases_count'] = sum(1 for phrase in self.SUSPICIOUS_PHRASES if phrase in content)
        features['suspicious_phrases_present'] = 1.0 if features['suspicious_phrases_count'] > 0 else 0.0
        
        # Financial keywords (ML-only detection)
        features['financial_keywords_count'] = sum(1 for kw in self.FINANCIAL_KEYWORDS if kw in content)
        features['financial_keywords_present'] = 1.0 if features['financial_keywords_count'] > 0 else 0.0
        
        # Brand impersonation detection (ML-only)
        features['brand_keywords_count'] = sum(1 for brand in self.BRAND_KEYWORDS if brand in content)
        features['brand_keywords_present'] = 1.0 if features['brand_keywords_count'] > 0 else 0.0
        
        # Grammar and spelling indicators
        features['exclamation_count'] = content.count('!')
        features['question_count'] = content.count('?')
        features['dollar_count'] = content.count('$')
        features['all_caps_ratio'] = len(re.findall(r'[A-Z]', content)) / max(len(content), 1)
        
        # Form-related features (phishing often has forms)
        features['has_form'] = 1.0 if '<form' in html.lower() else 0.0
        features['has_password_input'] = 1.0 if 'type="password"' in html.lower() else 0.0
        features['has_input_fields'] = 1.0 if '<input' in html.lower() else 0.0
        
        # Script-related features
        features['has_script'] = 1.0 if '<script' in html.lower() else 0.0
        features['has_iframe'] = 1.0 if '<iframe' in html.lower() else 0.0
        features['has_onerror'] = 1.0 if 'onerror' in html.lower() else 0.0
        features['has_onload'] = 1.0 if 'onload' in html.lower() else 0.0
        
        # External resources (count only, reputation handled by TI)
        features['external_images'] = len(re.findall(r'<img[^>]+src=["\']https?://', html, re.IGNORECASE))
        features['external_resources'] = len(re.findall(r'(src|href)=["\']https?://', html, re.IGNORECASE))
        
        # Hidden elements detection
        features['has_hidden_elements'] = 1.0 if 'display:none' in html.lower() or 'visibility:hidden' in html.lower() else 0.0
        
        # Link text vs actual URL mismatch indicators
        features['has_mailto'] = 1.0 if 'mailto:' in content else 0.0
        
        # Greeting analysis
        generic_greetings = ['dear customer', 'dear user', 'dear member', 'dear client']
        features['generic_greeting'] = 1.0 if any(g in content for g in generic_greetings) else 0.0
        
        # Call to action analysis
        cta_phrases = ['click below', 'click here', 'login now', 'sign in', 'verify account']
        features['cta_phrase_count'] = sum(1 for cta in cta_phrases if cta in content)
        
        # Prize/lottery indicators
        prize_keywords = ['won', 'winner', 'prize', 'lottery', 'claim now', 'congratulations']
        features['prize_indicators'] = sum(1 for kw in prize_keywords if kw in content)
        
        return features
    
    def _extract_link_features(self, links: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extract ML features from links (count-based, reputation handled by TI).
        
        Note: Link reputation features removed - handled by Threat Intelligence APIs.
        """
        features = {}
        
        # Basic counts (ML-only features)
        features['total_links'] = len(links)
        features['unique_domains'] = len(set(link['domain'] for link in links if link.get('domain')))
        
        if not links:
            features['links_per_domain_ratio'] = 0.0
            features['avg_domain_length'] = 0.0
            return features
        
        # Link distribution features
        if features['unique_domains'] > 0:
            features['links_per_domain_ratio'] = features['total_links'] / features['unique_domains']
        else:
            features['links_per_domain_ratio'] = 0.0
        
        # Average domain length in links
        domains = [link.get('domain', '') for link in links if link.get('domain')]
        features['avg_domain_length'] = sum(len(d) for d in domains) / max(len(domains), 1)
        
        return features
    
    def _extract_attachment_features(self, attachments: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extract ML features from attachments.
        
        Note: File hash reputation is handled by Threat Intelligence APIs (VirusTotal).
        """
        features = {}
        
        # Basic attachment presence features
        features['has_attachments'] = 1.0 if attachments else 0.0
        features['attachment_count'] = len(attachments)
        
        if not attachments:
            features['multiple_attachments'] = 0.0
            features['total_attachment_size'] = 0.0
            features['avg_attachment_size'] = 0.0
            return features
        
        # Count-based features (type info handled by TI)
        features['multiple_attachments'] = 1.0 if len(attachments) > 1 else 0.0
        
        # Total attachment size (suspiciously large attachments can be phishing)
        features['total_attachment_size'] = sum(a.get('size', 0) for a in attachments)
        features['avg_attachment_size'] = features['total_attachment_size'] / len(attachments)
        
        return features
    
    def _extract_metadata_features(self, metadata: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from email metadata."""
        features = {}
        
        features['is_multipart'] = 1.0 if metadata.get('is_multipart', False) else 0.0
        features['received_count'] = metadata.get('received_count', 0)
        
        # Number of hops (too many or too few can be suspicious)
        hops = metadata.get('received_count', 0)
        features['hop_count'] = hops
        features['suspicious_hop_count'] = 1.0 if hops == 0 or hops > 10 else 0.0
        
        return features
    
    def _get_feature_names(self) -> List[str]:
        """Get list of all feature names (46 features - matches trained model)."""
        return [
            # Header features (12)
            'spf_pass', 'dkim_pass', 'dmarc_pass', 'spf_fail', 'dkim_fail', 'dmarc_fail',
            'reply_to_mismatch', 'domain_mismatch', 'subject_length', 'subject_has_exclamation',
            'subject_has_dollar', 'subject_all_caps_words',
            # Content features (26)
            'text_length', 'html_length', 'has_html', 'has_text', 'html_to_text_ratio',
            'urgency_keywords_count', 'urgency_keywords_present',
            'suspicious_phrases_count', 'suspicious_phrases_present',
            'financial_keywords_count', 'financial_keywords_present',
            'brand_keywords_count', 'brand_keywords_present',
            'exclamation_count', 'question_count', 'dollar_count', 'all_caps_ratio',
            'has_form', 'has_password_input', 'has_input_fields',
            'has_script', 'has_iframe', 'has_onerror', 'has_onload',
            'external_images', 'external_resources',
            # Link features (4)
            'total_links', 'unique_domains', 'links_per_domain_ratio', 'avg_domain_length',
            # Attachment features (3)
            'has_attachments', 'attachment_count', 'multiple_attachments',
            # Metadata features (1)
            'is_multipart'
        ]
    
    def get_feature_vector(self, parsed_email: Dict[str, Any]) -> List[float]:
        """
        Get feature vector as a list for ML model input.
        
        Args:
            parsed_email: Parsed email data
            
        Returns:
            List of feature values in consistent order
        """
        features = self.extract_features(parsed_email)
        return [features.get(name, 0.0) for name in self.feature_names]
