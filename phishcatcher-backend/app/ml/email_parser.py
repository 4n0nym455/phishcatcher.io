"""
Email Parser Module

This module provides comprehensive email parsing functionality to extract
all relevant information from email files including headers, body, links,
and attachments.
"""

import re
import hashlib
import base64
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime, parseaddr
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class EmailParser:
    """Parse email files and extract all relevant data."""
    
    # URL regex pattern
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
        re.IGNORECASE
    )
    
    # URL shorteners
    URL_SHORTENERS = {
        'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'short.link',
        'is.gd', 'buff.ly', 'adf.ly', 'shorturl.at', 'rebrand.ly',
        'bl.ink', 'short.io', 'cutt.ly', 'rb.gy'
    }
    
    # Suspicious TLDs
    SUSPICIOUS_TLDS = {
        '.tk', '.ml', '.ga', '.cf', '.gq',  # Free domains
        '.xyz', '.top', '.click', '.link', '.work'  # Commonly abused
    }
    
    # Executable file extensions
    EXECUTABLE_EXTENSIONS = {
        '.exe', '.dll', '.bat', '.cmd', '.sh', '.jar', '.py', '.js',
        '.vbs', '.wsf', '.ps1', '.app', '.dmg', '.pkg', '.deb', '.rpm'
    }
    
    # Script extensions
    SCRIPT_EXTENSIONS = {
        '.js', '.vbs', '.wsf', '.ps1', '.py', '.rb', '.pl', '.sh',
        '.bat', '.cmd', '.php', '.asp', '.aspx', '.jsp'
    }
    
    def __init__(self, raw_email: bytes):
        """
        Initialize parser with raw email bytes.
        
        Args:
            raw_email: Raw email content as bytes
        """
        self.raw_email = raw_email
        self.msg = message_from_bytes(raw_email, policy=policy.default)
        self._body_text: Optional[str] = None
        self._body_html: Optional[str] = None
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse email and extract all relevant data.
        
        Returns:
            Dictionary containing parsed email data
        """
        try:
            return {
                'headers': self._extract_headers(),
                'body': self._extract_body_content(),
                'links': self._extract_links(),
                'attachments': self._extract_attachments(),
                'metadata': self._extract_metadata()
            }
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            raise
    
    def _extract_headers(self) -> Dict[str, Any]:
        """Extract and parse email headers."""
        headers = {}
        
        # Basic headers
        headers['from'] = self.msg.get('From', '')
        headers['from_address'] = self._extract_email_address(headers['from'])
        headers['from_name'] = self._extract_display_name(headers['from'])
        
        headers['to'] = self.msg.get('To', '')
        headers['to_addresses'] = self._extract_email_addresses(headers['to'])
        
        headers['cc'] = self.msg.get('Cc', '')
        headers['cc_addresses'] = self._extract_email_addresses(headers['cc'])
        
        headers['subject'] = self.msg.get('Subject', '')
        headers['date'] = self.msg.get('Date', '')
        headers['message_id'] = self.msg.get('Message-ID', '')
        headers['reply_to'] = self.msg.get('Reply-To', '')
        headers['return_path'] = self.msg.get('Return-Path', '')
        
        # Authentication headers
        headers['authentication_results'] = self._parse_authentication_results(
            self.msg.get('Authentication-Results', '')
        )
        headers['received_spf'] = self.msg.get('Received-SPF', '')
        headers['dkim_signature'] = self.msg.get('DKIM-Signature', '')
        
        # Check for reply-to mismatch
        headers['reply_to_mismatch'] = self._check_reply_to_mismatch(headers)
        
        # Extract sender domain
        headers['sender_domain'] = self._extract_domain(headers['from_address'])
        
        # Extract return path domain
        headers['return_path_domain'] = self._extract_domain(
            self._extract_email_address(headers['return_path'])
        )
        
        return headers
    
    def _extract_body_content(self) -> Dict[str, Any]:
        """Extract body content (both text and HTML)."""
        body = {
            'text': '',
            'html': '',
            'text_length': 0,
            'html_length': 0,
            'has_html': False,
            'has_text': False
        }
        
        if self.msg.is_multipart():
            for part in self.msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get_content_disposition()
                
                # Skip attachments
                if content_disposition == 'attachment':
                    continue
                
                if content_type == 'text/plain' and not body['text']:
                    body['text'] = self._decode_payload(part)
                    body['has_text'] = True
                elif content_type == 'text/html' and not body['html']:
                    body['html'] = self._decode_payload(part)
                    body['has_html'] = True
        else:
            content_type = self.msg.get_content_type()
            if content_type == 'text/plain':
                body['text'] = self._decode_payload(self.msg)
                body['has_text'] = True
            elif content_type == 'text/html':
                body['html'] = self._decode_payload(self.msg)
                body['has_html'] = True
        
        body['text_length'] = len(body['text'])
        body['html_length'] = len(body['html'])
        
        # Store for later use
        self._body_text = body['text']
        self._body_html = body['html']
        
        return body
    
    def _extract_links(self) -> List[Dict[str, Any]]:
        """Extract all links from email body."""
        links = []
        seen_urls = set()
        
        # Search in both text and HTML bodies
        content = f"{self._body_text or ''} {self._body_html or ''}"
        
        # Find all URLs
        urls = self.URL_PATTERN.findall(content)
        
        for url in urls:
            # Clean URL
            url = url.strip('<>"\'')
            
            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            link_info = {
                'url': url,
                'domain': domain,
                'path': parsed.path,
                'query': parsed.query,
                'is_ip_address': self._is_ip_address(domain),
                'is_shortened': self._is_url_shortener(domain),
                'has_suspicious_tld': self._has_suspicious_tld(domain),
                'has_at_symbol': '@' in url,
                'has_hex_chars': self._has_excessive_hex(url),
                'url_length': len(url),
                'domain_age_indicator': None  # Would need external API
            }
            
            links.append(link_info)
        
        return links
    
    def _extract_attachments(self) -> List[Dict[str, Any]]:
        """Extract attachment information."""
        attachments = []
        
        if not self.msg.is_multipart():
            return attachments
        
        for part in self.msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename() or 'unnamed'
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True) or b''
                
                attachment_info = {
                    'filename': filename,
                    'content_type': content_type,
                    'size': len(payload),
                    'extension': self._get_file_extension(filename),
                    'hash_md5': hashlib.md5(payload).hexdigest(),
                    'hash_sha1': hashlib.sha1(payload).hexdigest(),
                    'hash_sha256': hashlib.sha256(payload).hexdigest(),
                    'is_executable': self._is_executable(filename),
                    'is_script': self._is_script(filename),
                    'is_office_doc': self._is_office_document(filename),
                    'is_pdf': filename.lower().endswith('.pdf'),
                    'is_archive': self._is_archive(filename)
                }
                
                attachments.append(attachment_info)
        
        return attachments
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract email metadata."""
        received_headers = self.msg.get_all('Received', [])
        
        metadata = {
            'is_multipart': self.msg.is_multipart(),
            'content_type': self.msg.get_content_type(),
            'received_count': len(received_headers),
            'has_attachments': len(self._extract_attachments()) > 0,
            'total_links': len(self._extract_links()),
            'unique_domains': len(set(link['domain'] for link in self._extract_links())),
        }
        
        # Extract hop information from Received headers
        if received_headers:
            metadata['hops'] = self._parse_received_headers(received_headers)
        
        return metadata
    
    def _decode_payload(self, part) -> str:
        """Decode email part payload to string."""
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ''
            
            # Try UTF-8 first
            try:
                return payload.decode('utf-8', errors='ignore')
            except UnicodeDecodeError:
                pass
            
            # Try other encodings
            charset = part.get_content_charset()
            if charset:
                try:
                    return payload.decode(charset, errors='ignore')
                except (UnicodeDecodeError, LookupError):
                    pass
            
            # Fallback to latin-1
            return payload.decode('latin-1', errors='ignore')
        except Exception as e:
            logger.warning(f"Error decoding payload: {e}")
            return ''
    
    def _extract_email_address(self, header_value: str) -> str:
        """Extract email address from header value."""
        if not header_value:
            return ''
        _, address = parseaddr(header_value)
        return address.lower()
    
    def _extract_email_addresses(self, header_value: str) -> List[str]:
        """Extract multiple email addresses from header value."""
        if not header_value:
            return []
        
        addresses = []
        for part in header_value.split(','):
            _, address = parseaddr(part.strip())
            if address:
                addresses.append(address.lower())
        return addresses
    
    def _extract_display_name(self, header_value: str) -> str:
        """Extract display name from header value."""
        if not header_value:
            return ''
        name, _ = parseaddr(header_value)
        return name
    
    def _extract_domain(self, email_address: str) -> str:
        """Extract domain from email address."""
        if '@' in email_address:
            return email_address.split('@')[1].lower()
        return ''
    
    def _parse_authentication_results(self, header_value: str) -> Dict[str, str]:
        """Parse Authentication-Results header."""
        results = {
            'spf': None,
            'dkim': None,
            'dmarc': None
        }
        
        if not header_value:
            return results
        
        header_lower = header_value.lower()
        
        # Check SPF
        if 'spf=pass' in header_lower:
            results['spf'] = 'pass'
        elif 'spf=fail' in header_lower:
            results['spf'] = 'fail'
        elif 'spf=neutral' in header_lower:
            results['spf'] = 'neutral'
        
        # Check DKIM
        if 'dkim=pass' in header_lower:
            results['dkim'] = 'pass'
        elif 'dkim=fail' in header_lower:
            results['dkim'] = 'fail'
        
        # Check DMARC
        if 'dmarc=pass' in header_lower:
            results['dmarc'] = 'pass'
        elif 'dmarc=fail' in header_lower:
            results['dmarc'] = 'fail'
        
        return results
    
    def _check_reply_to_mismatch(self, headers: Dict[str, Any]) -> bool:
        """Check if reply-to address differs from from address."""
        from_addr = headers.get('from_address', '')
        reply_to = headers.get('reply_to', '')
        
        if not reply_to:
            return False
        
        reply_to_addr = self._extract_email_address(reply_to)
        return from_addr != reply_to_addr
    
    def _is_ip_address(self, hostname: str) -> bool:
        """Check if hostname is an IP address."""
        import ipaddress
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False
    
    def _is_url_shortener(self, domain: str) -> bool:
        """Check if domain is a URL shortener."""
        return domain.lower() in self.URL_SHORTENERS
    
    def _has_suspicious_tld(self, domain: str) -> bool:
        """Check if domain has a suspicious TLD."""
        domain_lower = domain.lower()
        return any(domain_lower.endswith(tld) for tld in self.SUSPICIOUS_TLDS)
    
    def _has_excessive_hex(self, url: str) -> bool:
        """Check if URL has excessive hex encoding."""
        hex_pattern = re.compile(r'%[0-9a-fA-F]{2}')
        hex_count = len(hex_pattern.findall(url))
        return hex_count > 3
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename."""
        if '.' in filename:
            return filename.lower().split('.')[-1]
        return ''
    
    def _is_executable(self, filename: str) -> bool:
        """Check if file is executable."""
        ext = self._get_file_extension(filename)
        return f'.{ext}' in self.EXECUTABLE_EXTENSIONS
    
    def _is_script(self, filename: str) -> bool:
        """Check if file is a script."""
        ext = self._get_file_extension(filename)
        return f'.{ext}' in self.SCRIPT_EXTENSIONS
    
    def _is_office_document(self, filename: str) -> bool:
        """Check if file is an Office document."""
        office_exts = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
        ext = self._get_file_extension(filename)
        return f'.{ext}' in office_exts
    
    def _is_archive(self, filename: str) -> bool:
        """Check if file is an archive."""
        archive_exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
        ext = self._get_file_extension(filename)
        return f'.{ext}' in archive_exts
    
    def _parse_received_headers(self, received_headers: List[str]) -> List[Dict[str, str]]:
        """Parse Received headers to extract hop information."""
        hops = []
        
        for header in received_headers[:5]:  # Limit to first 5 hops
            hop_info = {
                'from': None,
                'by': None,
                'with': None,
                'date': None
            }
            
            # Extract 'from' server
            from_match = re.search(r'from\s+(\S+)', header, re.IGNORECASE)
            if from_match:
                hop_info['from'] = from_match.group(1)
            
            # Extract 'by' server
            by_match = re.search(r'by\s+(\S+)', header, re.IGNORECASE)
            if by_match:
                hop_info['by'] = by_match.group(1)
            
            # Extract protocol
            with_match = re.search(r'with\s+(\S+)', header, re.IGNORECASE)
            if with_match:
                hop_info['with'] = with_match.group(1)
            
            hops.append(hop_info)
        
        return hops
