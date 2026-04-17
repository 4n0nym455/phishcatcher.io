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
from bs4 import BeautifulSoup
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
        """
        Extract body content from the actual email message.
        
        IMPORTANT: This method ONLY extracts content from the main message body.
        It ignores:
        - Embedded calendar/ICS content
        - Alternative MIME parts (multipart/related)
        - Inline attachments
        
        This prevents embedded content links from polluting the link extraction.
        """
        body = {
            'text': '',
            'html': '',
            'text_length': 0,
            'html_length': 0,
            'has_html': False,
            'has_text': False
        }
        
        content_type = self.msg.get_content_type()
        
        # Handle multipart messages - only extract from the main body
        if self.msg.is_multipart():
            # For multipart, iterate through parts but ONLY take the first
            # text/plain and text/html we encounter (these are the body)
            # Skip any additional parts (embedded content, calendar, etc.)
            for part in self.msg.walk():
                part_content_type = part.get_content_type()
                part_disposition = part.get_content_disposition()
                
                # Skip attachments and inline content
                if part_disposition in ('attachment', 'inline'):
                    continue
                
                # Skip calendar/ICS content
                if part_content_type in ('text/calendar', 'text/x-vcalendar', 
                                         'application/ics', 'text/calendar'):
                    continue
                
                # Skip multipart/* types (these are containers, not content)
                if part_content_type.startswith('multipart/'):
                    continue
                
                # Extract main body content only
                if part_content_type == 'text/plain' and not body['text']:
                    body['text'] = self._decode_payload(part)
                    body['has_text'] = True
                elif part_content_type == 'text/html' and not body['html']:
                    body['html'] = self._decode_payload(part)
                    body['has_html'] = True
        else:
            # Non-multipart message
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
    
    # Non-actionable domains that should be filtered
    NON_ACTIONABLE_DOMAINS = frozenset({
        'fonts.googleapis.com',
        'fonts.gstatic.com',
    })
    
    # Non-actionable URL path patterns (email infrastructure/tracking links)
    # NOTE: Password reset links are intentionally NOT filtered - they're important for security analysis
    NON_ACTIONABLE_PATTERNS = frozenset({
        'unsubscribe',
        'opt-out',
        'optout',
        'email-preference',
        'email_preference',
        'manage_subscription',
        'notification_settings',
        'email-settings',
        'email_settings',
        'notification/unsubscribe',
        'list-unsubscribe',
        'one-click-unsubscribe',
        '/email/',  # Email tracking/unsubscribe paths
        '/unsubscribe',
        '/notification/',
    })
    
    # Tracking URL parameter prefixes to remove
    TRACKING_PARAMS = frozenset({
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'utm_id', 'utm_cid',
        'ref', 'referer', 'referrer',
        'affiliate', 'aff_id', 'affiliate_id',
        'partner', 'partner_id',
        'campaign_id', 'cid',
        'mc_cid', 'mc_eid',
        's_cid',
        'oly_enc_id', 'oly_anon_id',
        '_hsenc', '_hsmi', 'hsCtaTracking',
        'mkt_tok',
        'trk', 'trkInfo',
        'vero_id',
        'nr_email_referer',
        'action_method',
    })
    
    def _clean_url(self, url: str) -> str:
        """
        Remove tracking parameters from URL while keeping the original link intact.
        
        Removes: utm_*, ref, affiliate, tracking tokens, etc.
        Keeps: user_id, code, token (if they appear to be authentication)
        """
        parsed = urlparse(url)
        
        # Check if this is a blocked URL pattern (unsubscribe, etc.)
        url_lower = url.lower()
        for pattern in self.NON_ACTIONABLE_PATTERNS:
            if pattern.lower() in url_lower:
                return None  # Signal to skip this URL
        
        # Parse query parameters
        params = {}
        problematic_params = set()
        
        if parsed.query:
            param_pairs = parsed.query.split('&')
            for param in param_pairs:
                if '=' in param:
                    key = param.split('=')[0].lower()
                    # Remove tracking parameters
                    if key in self.TRACKING_PARAMS:
                        problematic_params.add(key)
                    elif key.startswith('tk=') or key.startswith('_tk=') or key.startswith('token='):
                        # But keep actual auth tokens for important links
                        if any(x in url_lower for x in ['password', 'reset', 'confirm', 'verify']):
                            params[key] = param.split('=', 1)[1] if '=' in param else ''
                    else:
                        params[key] = param.split('=', 1)[1] if '=' in param else ''
        
        # Reconstruct URL without tracking params
        clean_query = '&'.join(f"{k}={v}" for k, v in params.items() if v or k in ['code', 'user_id', 'id'])
        
        if clean_query:
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}{parsed.fragment if parsed.fragment else ''}"
        else:
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}{parsed.fragment if parsed.fragment else ''}"
        
        return clean_url
    
    def _is_actionable_url(self, url: str, domain: str) -> bool:
        """
        Check if a URL is actionable (user-clickable for phishing analysis).
        
        Filters out:
        - Unsubscribe links
        - Email tracking pixels
        - Preference center links
        - Other email infrastructure URLs
        - URLs with only tracking parameters
        """
        url_lower = url.lower()
        domain_lower = domain.lower()
        
        # Check domain against blocked domains
        if any(blocked in domain_lower for blocked in self.NON_ACTIONABLE_DOMAINS):
            return False
        
        # Check URL path against blocked patterns
        for pattern in self.NON_ACTIONABLE_PATTERNS:
            if pattern.lower() in url_lower:
                return False
        
        # Skip zoom.us unsubscribe/email infrastructure (but keep meeting links)
        if 'zoom.us' in domain_lower:
            # Filter these patterns
            if any(p in url_lower for p in ['/email/', '/unsubscribe']):
                return False
            # Meeting links (with /w/, /webinar/) are primary actions - keep them
        
        # Skip common email marketing tracking domains
        tracking_domains = {
            'mailgun.org', 'sendgrid.net', 'sparkpost.com', 'mailchimp.com',
            'amazonses.com', 'postmarkapp.com', 'mandrillapp.com',
            'intercom-mail', 'crisp.chat',
        }
        if any(td in domain_lower for td in tracking_domains):
            return False
        
        # Skip URLs that are ONLY tracking (no meaningful content)
        parsed = urlparse(url)
        if parsed.query:
            query_lower = parsed.query.lower()
            tracking_only = all(
                param.split('=')[0].lower() in self.TRACKING_PARAMS 
                for param in parsed.query.split('&') 
                if param and '=' in param
            )
            if tracking_only and not any(x in url_lower for x in ['password', 'reset', 'confirm', 'verify', 'subscribe']):
                return False
        
        return True
    
    def _extract_links(self) -> List[Dict[str, Any]]:
        """
        Extract actionable links from email body only.
        
        IMPORTANT: Only extracts links from <a> tags in the rendered HTML.
        Does NOT extract URLs from:
        - Plain text content
        - JSON-LD/microdata
        - Meta tags
        - HTML comments
        - Embedded content (ICS, calendar)
        
        Filters out:
        - Unsubscribe links
        - Tracking-only URLs
        - Email infrastructure links
        
        Also extracts URLs from query parameters (e.g., Gmail redirects:
        google.com/url?q=http://actual-site.com)
        """
        links = []
        seen_base_urls = set()  # Track base URLs to avoid duplicates
        
        # Query parameter names that may contain the actual URL
        URL_CONTAINING_PARAMS = {'q', 'url', 'link', 'target', 'redir', 'redirect', 'dest', 'destination', 'u', 'goto'}
        
        def _extract_urls_from_param_value(param_value: str) -> List[str]:
            """Extract URLs from a parameter value (could be comma-separated or encoded)."""
            extracted = []
            # Try to find URLs in the value
            url_matches = self.URL_PATTERN.findall(param_value)
            for url in url_matches:
                if url.startswith('http://') or url.startswith('https://'):
                    extracted.append(url)
            return extracted
        
        def _process_url(href: str, display_text: str = None) -> Optional[Dict]:
            """Process a single URL and return link info if actionable."""
            if not href or not (href.startswith('http://') or href.startswith('https://')):
                return None
            
            clean_url = self._clean_url(href)
            if clean_url is None:
                return None
            
            parsed = urlparse(clean_url)
            domain = parsed.netloc.lower()
            
            # Check if this is a redirect URL (contains another URL in query params)
            embedded_urls = []
            if parsed.query:
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        key = key.lower()
                        value = value.strip()
                        if key in URL_CONTAINING_PARAMS and value:
                            # Decode URL-encoded value
                            from urllib.parse import unquote
                            decoded = unquote(value)
                            embedded_urls.extend(_extract_urls_from_param_value(decoded))
            
            # Also check for encoded URLs in fragment
            if parsed.fragment and not parsed.query:
                from urllib.parse import unquote
                decoded_fragment = unquote(parsed.fragment)
                embedded_urls.extend(_extract_urls_from_param_value(decoded_fragment))
            
            # Process the main URL
            if not self._is_actionable_url(clean_url, domain):
                return None
            
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if base_url in seen_base_urls:
                return None
            seen_base_urls.add(base_url)
            
            link_info = {
                'url': clean_url,
                'domain': domain,
                'path': parsed.path,
                'query': parsed.query,
                'display_text': display_text if display_text else None,
                'is_ip_address': self._is_ip_address(domain),
                'is_shortened': self._is_url_shortener(domain),
                'has_suspicious_tld': self._has_suspicious_tld(domain),
                'has_at_symbol': '@' in clean_url,
                'has_hex_chars': self._has_excessive_hex(clean_url),
                'url_length': len(clean_url),
                'domain_age_indicator': None
            }
            
            return link_info
        
        # ==========================================
        # Extract ONLY from <a> tags in HTML body
        # This ensures we only get visible clickable links
        # ==========================================
        if self._body_html:
            try:
                soup = BeautifulSoup(self._body_html, 'html.parser')
                
                # Extract only <a> tags with href attributes
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href'].strip()
                    display_text = a_tag.get_text(strip=True)
                    
                    # Process the main URL
                    link_info = _process_url(href, display_text)
                    if link_info:
                        links.append(link_info)
                        
                        # Also check if this URL contains embedded URLs (like Gmail redirects)
                        parsed = urlparse(href)
                        if parsed.query:
                            for param in parsed.query.split('&'):
                                if '=' in param:
                                    key, value = param.split('=', 1)
                                    key = key.lower()
                                    value = value.strip()
                                    if key in URL_CONTAINING_PARAMS and value:
                                        from urllib.parse import unquote
                                        decoded = unquote(value)
                                        embedded_urls = _extract_urls_from_param_value(decoded)
                                        for emb_url in embedded_urls:
                                            emb_link = _process_url(emb_url, f"Embedded: {emb_url[:50]}...")
                                            if emb_link and emb_link['url'] not in [l['url'] for l in links]:
                                                links.append(emb_link)
                        
            except Exception as e:
                logger.warning(f"Error parsing HTML for links: {e}")
        
        # NOTE: We intentionally do NOT extract from plain text
        # Only <a> tags represent actual clickable links in the email
        
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
