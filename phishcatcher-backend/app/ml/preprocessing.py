"""
Preprocessing Module

This module provides text preprocessing functions for email phishing detection.
Implements:
- Lowercasing
- URL replacement with token "URL"
- Removal of non-alphabetic characters
- Whitespace normalization
"""

import re
import logging
from typing import List, Optional, Dict, Any
from html import unescape

logger = logging.getLogger(__name__)


class EmailPreprocessor:
    """Preprocessor for email text content."""
    
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
        re.IGNORECASE
    )
    
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    def __init__(self, preserve_urls: bool = True):
        """
        Initialize preprocessor.
        
        Args:
            preserve_urls: If True, replace URLs with "URL" token; if False, remove entirely
        """
        self.preserve_urls = preserve_urls
    
    def preprocess_text(self, text: str) -> str:
        """
        Apply full preprocessing pipeline to text.
        
        Steps:
        1. Unescape HTML entities
        2. Lowercase
        3. Replace URLs with token
        4. Replace email addresses with token
        5. Remove non-alphabetic characters (keep spaces)
        6. Normalize whitespace
        
        Args:
            text: Raw email text
            
        Returns:
            Preprocessed text
        """
        if not text or not isinstance(text, str):
            return ""
        
        text = unescape(text)
        
        text = text.lower()
        
        if self.preserve_urls:
            text = self.URL_PATTERN.sub(" URL ", text)
        else:
            text = self.URL_PATTERN.sub("", text)
        
        text = self.EMAIL_PATTERN.sub(" EMAIL ", text)
        
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        
        text = re.sub(r'\s+', ' ', text)
        
        text = text.strip()
        
        return text
    
    def preprocess_subject(self, subject: str) -> str:
        """Preprocess email subject line."""
        return self.preprocess_text(subject)
    
    def preprocess_body(self, body: str) -> str:
        """Preprocess email body."""
        return self.preprocess_text(body)
    
    def preprocess_email_full(
        self,
        subject: str,
        body: str,
        combine: bool = True
    ) -> Dict[str, str]:
        """
        Preprocess entire email.
        
        Args:
            subject: Email subject
            body: Email body
            combine: If True, return combined text; if False, return separate
            
        Returns:
            Dictionary with preprocessed subject, body, and optionally combined
        """
        result = {
            'subject': self.preprocess_subject(subject),
            'body': self.preprocess_body(body)
        }
        
        if combine:
            result['combined'] = f"{result['subject']} {result['body']}"
        
        return result
    
    def preprocess_dataset(self, texts: List[str]) -> List[str]:
        """
        Preprocess a list of texts.
        
        Args:
            texts: List of raw text strings
            
        Returns:
            List of preprocessed texts
        """
        return [self.preprocess_text(text) for text in texts]


class HTMLPreprocessor:
    """Preprocessor specifically for HTML email content."""
    
    def __init__(self):
        self.email_preprocessor = EmailPreprocessor()
    
    def extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML."""
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = unescape(text)
        
        return text.strip()
    
    def preprocess_html_email(
        self,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> str:
        """
        Preprocess HTML email.
        
        Args:
            subject: Email subject
            html_body: HTML body
            text_body: Optional plain text version
            
        Returns:
            Preprocessed text
        """
        if text_body:
            body = text_body
        else:
            body = self.extract_text_from_html(html_body)
        
        return self.email_preprocessor.preprocess_email_full(subject, body)['combined']


def preprocess_text(text: str) -> str:
    """
    Quick preprocessing function for single text.
    
    Usage:
        cleaned = preprocess_text(raw_email)
    """
    processor = EmailPreprocessor()
    return processor.preprocess_text(text)


def preprocess_emails(texts: List[str]) -> List[str]:
    """
    Quick preprocessing for multiple texts.
    
    Usage:
        cleaned_list = preprocess_emails(raw_emails)
    """
    processor = EmailPreprocessor()
    return processor.preprocess_dataset(texts)