"""
Validation Utilities

Common validation functions for the application.
"""

import re
from typing import Tuple, Optional
from urllib.parse import urlparse


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 255:
        return False, "Email too long (max 255 characters)"
    
    return True, None


def validate_url(url: str, allowed_schemes: list = None) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed schemes (default: http, https)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    try:
        parsed = urlparse(url)
        
        if not parsed.scheme:
            return False, "URL must have a scheme (http/https)"
        
        if parsed.scheme not in allowed_schemes:
            return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"
        
        if not parsed.netloc:
            return False, "URL must have a domain"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def validate_file_extension(filename: str, allowed_extensions: list) -> Tuple[bool, Optional[str]]:
    """
    Validate file extension.
    
    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions (with or without dot)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    # Normalize extensions
    allowed = [ext.lower().lstrip('.') for ext in allowed_extensions]
    
    # Get file extension
    if '.' not in filename:
        return False, "File has no extension"
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    if ext not in allowed:
        return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


def validate_file_size(size_bytes: int, max_size_mb: int) -> Tuple[bool, Optional[str]]:
    """
    Validate file size.
    
    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if size_bytes < 0:
        return False, "Invalid file size"
    
    max_bytes = max_size_mb * 1024 * 1024
    
    if size_bytes > max_bytes:
        return False, f"File too large. Max size: {max_size_mb}MB"
    
    return True, None


def is_valid_ip_address(ip: str) -> bool:
    """
    Check if string is a valid IP address.
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid IP address
    """
    import ipaddress
    
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is private.
    
    Args:
        ip: IP address string
        
    Returns:
        True if private IP address
    """
    import ipaddress
    
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.replace('..', '')
    filename = filename.replace('/', '')
    filename = filename.replace('\\', '')
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255 - len(ext) - 1] + '.' + ext if ext else name[:255]
    
    return filename
