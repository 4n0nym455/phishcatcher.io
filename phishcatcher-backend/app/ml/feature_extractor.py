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
    
    # Financial keywords
    FINANCIAL_KEYWORDS = [
        'bank', 'credit card', 'payment', 'invoice', 'transaction', 'refund',
        'billing', 'subscription', 'paypal', 'money', 'transfer'
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
        """Extract features from email body content."""
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
        
        # Urgency keywords
        features['urgency_keywords_count'] = sum(1 for kw in self.URGENCY_KEYWORDS if kw in content)
        
        # Suspicious phrases
        features['suspicious_phrases_count'] = sum(1 for phrase in self.SUSPICIOUS_PHRASES if phrase in content)
        
        # Financial keywords
        features['financial_keywords_count'] = sum(1 for kw in self.FINANCIAL_KEYWORDS if kw in content)
        
        # Grammar and spelling indicators
        features['exclamation_count'] = content.count('!')
        features['question_count'] = content.count('?')
        features['dollar_count'] = content.count('$')
        features['all_caps_ratio'] = len(re.findall(r'[A-Z]', content)) / max(len(content), 1)
        
        # Form-related features (phishing often has forms)
        features['has_form'] = 1.0 if '<form' in html.lower() else 0.0
        features['has_password_input'] = 1.0 if 'type="password"' in html.lower() else 0.0
        
        # Script-related features
        features['has_script'] = 1.0 if '<script' in html.lower() else 0.0
        features['has_iframe'] = 1.0 if '<iframe' in html.lower() else 0.0
        
        # External resources
        features['external_images'] = len(re.findall(r'<img[^>]+src=["\']https?://', html, re.IGNORECASE))
        
        return features
    
    def _extract_link_features(self, links: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract features from links."""
        features = {}
        
        # Basic counts
        features['total_links'] = len(links)
        features['unique_domains'] = len(set(link['domain'] for link in links))
        
        if not links:
            features['suspicious_links_ratio'] = 0.0
            features['ip_based_links'] = 0.0
            features['shortened_links'] = 0.0
            features['suspicious_tld_links'] = 0.0
            return features
        
        # Suspicious link indicators
        suspicious_count = 0
        ip_based_count = 0
        shortened_count = 0
        suspicious_tld_count = 0
        
        for link in links:
            if link.get('is_ip_address'):
                ip_based_count += 1
                suspicious_count += 1
            
            if link.get('is_shortened'):
                shortened_count += 1
                suspicious_count += 1
            
            if link.get('has_suspicious_tld'):
                suspicious_tld_count += 1
                suspicious_count += 1
            
            if link.get('has_at_symbol'):
                suspicious_count += 1
            
            if link.get('has_hex_chars'):
                suspicious_count += 1
        
        features['suspicious_links'] = suspicious_count
        features['suspicious_links_ratio'] = suspicious_count / len(links)
        features['ip_based_links'] = ip_based_count
        features['shortened_links'] = shortened_count
        features['suspicious_tld_links'] = suspicious_tld_count
        
        # Average URL length (phishing URLs tend to be longer)
        if links:
            features['avg_url_length'] = sum(link.get('url_length', 0) for link in links) / len(links)
        else:
            features['avg_url_length'] = 0.0
        
        return features
    
    def _extract_attachment_features(self, attachments: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract features from attachments."""
        features = {}
        
        features['has_attachments'] = 1.0 if attachments else 0.0
        features['attachment_count'] = len(attachments)
        
        if not attachments:
            features['executable_attachments'] = 0.0
            features['script_attachments'] = 0.0
            features['office_attachments'] = 0.0
            features['pdf_attachments'] = 0.0
            features['archive_attachments'] = 0.0
            features['total_attachment_size'] = 0.0
            return features
        
        # Count by type
        executable_count = sum(1 for a in attachments if a.get('is_executable', False))
        script_count = sum(1 for a in attachments if a.get('is_script', False))
        office_count = sum(1 for a in attachments if a.get('is_office_doc', False))
        pdf_count = sum(1 for a in attachments if a.get('is_pdf', False))
        archive_count = sum(1 for a in attachments if a.get('is_archive', False))
        
        features['executable_attachments'] = executable_count
        features['script_attachments'] = script_count
        features['office_attachments'] = office_count
        features['pdf_attachments'] = pdf_count
        features['archive_attachments'] = archive_count
        
        # Total attachment size
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
        """Get list of all feature names."""
        # Return a sample of feature names for model training
        return [
            'spf_pass', 'dkim_pass', 'dmarc_pass', 'spf_fail', 'dkim_fail', 'dmarc_fail',
            'reply_to_mismatch', 'domain_mismatch', 'subject_length', 'subject_has_exclamation',
            'subject_has_dollar', 'subject_all_caps_words', 'text_length', 'html_length',
            'has_html', 'has_text', 'html_to_text_ratio', 'urgency_keywords_count',
            'suspicious_phrases_count', 'financial_keywords_count', 'exclamation_count',
            'question_count', 'dollar_count', 'all_caps_ratio', 'has_form', 'has_password_input',
            'has_script', 'has_iframe', 'external_images', 'total_links', 'unique_domains',
            'suspicious_links', 'suspicious_links_ratio', 'ip_based_links', 'shortened_links',
            'suspicious_tld_links', 'avg_url_length', 'has_attachments', 'attachment_count',
            'executable_attachments', 'script_attachments', 'office_attachments',
            'pdf_attachments', 'archive_attachments', 'total_attachment_size',
            'avg_attachment_size', 'is_multipart', 'received_count', 'hop_count',
            'suspicious_hop_count'
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
