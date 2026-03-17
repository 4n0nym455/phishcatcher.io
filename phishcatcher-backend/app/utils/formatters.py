"""
Formatting Utilities

Common formatting functions for the application.
"""

from datetime import datetime
from typing import Optional


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if size_bytes < 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    
    return f"{size_bytes:.1f} PB"


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object to string.
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return "N/A"
    
    return dt.strftime(format_str)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 0:
        return "0s"
    
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds:.0f}s"
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes > 0:
        return f"{hours}h {remaining_minutes}m"
    return f"{hours}h"


def format_number(num: int, precision: int = 0) -> str:
    """
    Format large numbers with K, M, B suffixes.
    
    Args:
        num: Number to format
        precision: Decimal precision
        
    Returns:
        Formatted number string
    """
    if num < 1000:
        return str(num)
    
    for suffix in ['K', 'M', 'B', 'T']:
        num /= 1000
        if num < 1000:
            return f"{num:.{precision}f}{suffix}"
    
    return f"{num:.{precision}f}T"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.
    
    Args:
        text: Original string
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def mask_string(text: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """
    Mask string showing only first and last visible characters.
    
    Args:
        text: Original string
        visible_chars: Number of characters to show at start and end
        mask_char: Character to use for masking
        
    Returns:
        Masked string
    """
    if len(text) <= visible_chars * 2:
        return mask_char * len(text)
    
    return text[:visible_chars] + mask_char * (len(text) - visible_chars * 2) + text[-visible_chars:]
