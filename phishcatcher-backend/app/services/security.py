"""
Security Service

This module provides security-related functions including:
- Password hashing and verification (bcrypt with SHA-256 pre-hash)
- JWT token creation and verification
- OTP generation and verification
- Encryption/decryption for sensitive data
"""

import secrets
import string
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
import bcrypt
from cryptography.fernet import Fernet
import pyotp
import qrcode
from io import BytesIO
import base64

from app.config import get_settings

# Encryption key for sensitive data (should be loaded from secure storage)
_fernet: Optional[Fernet] = None


def get_fernet() -> Fernet:
    """Get or create Fernet instance for encryption."""
    global _fernet
    if _fernet is None:
        settings = get_settings()
        # Derive key from SECRET_KEY (must be 32 bytes for Fernet)
        import base64
        import hashlib
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        )
        _fernet = Fernet(key)
    return _fernet


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data."""
    fernet = get_fernet()
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_data.encode()).decode()


# Password Management
def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with SHA-256 pre-hash.
    
    This approach first hashes the password with SHA-256 to avoid bcrypt's 72-byte limit,
    then applies bcrypt to the hash.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    # First, hash the password with SHA-256 to get a fixed-length hash
    sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
    
    # Then hash the SHA-256 hash with bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(sha256_hash, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    # First, hash the plain password with SHA-256
    sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).digest()
    
    # Then verify with bcrypt
    return bcrypt.checkpw(sha256_hash, hashed_password.encode('utf-8'))


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength according to policy.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    settings = get_settings()
    
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if settings.PASSWORD_REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if settings.PASSWORD_REQUIRE_SPECIAL:
        special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
    
    return True, None


# JWT Token Management
def create_mfa_session_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT MFA session token.
    
    Args:
        data: Data to encode in token
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT MFA session token
    """
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default 15 minutes for MFA
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "mfa_session"
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT access token
    """
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Data to encode in token
        
    Returns:
        JWT refresh token
    """
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        **data,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str, token_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type (access/refresh/mfa_session)
        
    Returns:
        Decoded token payload or None if invalid
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Verify token type if specified
        if token_type and payload.get("type") != token_type:
            return None
        
        return payload
    except JWTError:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get token expiration time.
    
    Args:
        token: JWT token
        
    Returns:
        Expiration datetime or None
    """
    payload = verify_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None


# OTP Management
def generate_otp(length: int = 6) -> str:
    """
    Generate a secure random OTP with alphanumeric characters for better security.
    
    Args:
        length: OTP length (default 6)
        
    Returns:
        Random OTP string with alphanumeric characters
    """
    # Use alphanumeric characters for better security than just digits
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def verify_otp(provided_otp: str, expected_otp: str, max_attempts: int = 3) -> bool:
    """
    Verify an OTP with timing-safe comparison.
    
    Args:
        provided_otp: OTP provided by user
        expected_otp: Expected OTP
        max_attempts: Maximum allowed attempts
        
    Returns:
        True if OTP is valid
    """
    # Use secrets.compare_digest for timing-safe comparison
    return secrets.compare_digest(provided_otp, expected_otp)


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length
        
    Returns:
        Secure random token
    """
    return secrets.token_urlsafe(length)


# API Key Management
def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key pair.
    
    Returns:
        Tuple of (api_key, hashed_api_key)
    """
    api_key = f"pk_{secrets.token_urlsafe(32)}"
    hashed_key = get_password_hash(api_key)
    return api_key, hashed_key


def verify_api_key(provided_key: str, hashed_key: str) -> bool:
    """
    Verify an API key.
    
    Args:
        provided_key: API key provided in request
        hashed_key: Stored hashed API key
        
    Returns:
        True if API key is valid
    """
    return verify_password(provided_key, hashed_key)


# Security Utilities
def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def sanitize_input(input_str: str) -> str:
    """
    Basic input sanitization to prevent XSS.
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        Sanitized string
    """
    import html
    return html.escape(input_str.strip())


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Args:
        email: Email address
        
    Returns:
        Masked email (e.g., j***@example.com)
    """
    if "@" not in email:
        return "***"
    
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" * (len(local) - 1)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_ip_address(ip: str) -> str:
    """
    Mask IP address for privacy.
    
    Args:
        ip: IP address
        
    Returns:
        Masked IP (e.g., 192.168.x.x)
    """
    if "." in ip:  # IPv4
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.x.x"
    elif ":" in ip:  # IPv6
        parts = ip.split(":")
        return f"{parts[0]}:{parts[1]}:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx"
    return "xxx.xxx.xxx.xxx"


# MFA/TOTP Functions
def generate_totp_secret() -> str:
    """
    Generate a new TOTP secret for MFA.
    
    Returns:
        Base32 encoded TOTP secret
    """
    return pyotp.random_base32()


def generate_totp_uri(secret: str, email: str, issuer: str = "PhishCatcher") -> str:
    """
    Generate TOTP URI for QR code generation.
    
    Args:
        secret: TOTP secret
        email: User email
        issuer: Application name
        
    Returns:
        TOTP URI for QR code
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer
    )


def generate_qr_code(uri: str) -> str:
    """
    Generate QR code for TOTP setup.
    
    Args:
        uri: TOTP URI
        
    Returns:
        Base64 encoded QR code image
    """
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def verify_totp_token(secret: str, token: str, valid_window: int = 1) -> bool:
    """
    Verify TOTP token.
    
    Args:
        secret: TOTP secret
        token: User-provided token
        valid_window: Time window for valid tokens (default 1 = 30 seconds before/after)
        
    Returns:
        True if token is valid
    """
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=valid_window)
    except Exception:
        return False


def encrypt_mfa_secret(secret: str) -> str:
    """
    Encrypt MFA secret for storage.
    
    Args:
        secret: TOTP secret to encrypt
        
    Returns:
        Encrypted secret
    """
    fernet = get_fernet()
    return fernet.encrypt(secret.encode()).decode()


def decrypt_mfa_secret(encrypted_secret: str) -> str:
    """
    Decrypt MFA secret from storage.
    
    Args:
        encrypted_secret: Encrypted TOTP secret
        
    Returns:
        Decrypted secret
    """
    fernet = get_fernet()
    return fernet.decrypt(encrypted_secret.encode()).decode()


# Rate Limiting for MFA Operations
_mfa_rate_limits = {}

def check_mfa_rate_limit(user_id: str, operation: str, max_attempts: int = 5, window_minutes: int = 15) -> tuple[bool, str]:
    """
    Check rate limit for MFA operations.
    
    Args:
        user_id: User identifier
        operation: Operation type ('setup', 'verify', 'backup_code')
        max_attempts: Maximum attempts allowed
        window_minutes: Time window in minutes
        
    Returns:
        Tuple of (allowed: bool, message: str)
    """
    now = datetime.utcnow()
    key = f"{user_id}:{operation}"
    
    if key not in _mfa_rate_limits:
        _mfa_rate_limits[key] = []
    
    # Clean old attempts outside the window
    _mfa_rate_limits[key] = [
        attempt_time for attempt_time in _mfa_rate_limits[key]
        if (now - attempt_time).total_seconds() < window_minutes * 60
    ]
    
    # Check if rate limit exceeded
    if len(_mfa_rate_limits[key]) >= max_attempts:
        return False, f"Too many {operation} attempts. Please wait {window_minutes} minutes before trying again."
    
    # Record this attempt
    _mfa_rate_limits[key].append(now)
    return True, ""

def clear_mfa_rate_limit(user_id: str, operation: str):
    """
    Clear rate limit for a specific user and operation.
    
    Args:
        user_id: User identifier
        operation: Operation type
    """
    key = f"{user_id}:{operation}"
    if key in _mfa_rate_limits:
        del _mfa_rate_limits[key]


def encrypt_backup_codes(backup_codes: list[str]) -> str:
    """
    Encrypt backup codes for secure storage.
    
    Args:
        backup_codes: List of backup code strings
        
    Returns:
        Encrypted JSON string of backup codes
    """
    import json
    fernet = get_fernet()
    backup_codes_json = json.dumps(backup_codes)
    return fernet.encrypt(backup_codes_json.encode()).decode()


def decrypt_backup_codes(encrypted_codes: str) -> list[str]:
    """
    Decrypt backup codes from storage.
    
    Args:
        encrypted_codes: Encrypted backup codes JSON string
        
    Returns:
        List of backup code strings
    """
    import json
    fernet = get_fernet()
    decrypted_json = fernet.decrypt(encrypted_codes.encode()).decode()
    return json.loads(decrypted_json)


# Account Lockout Functions
def should_lock_account(failed_attempts: int) -> bool:
    """
    Check if account should be locked based on failed attempts.
    
    Args:
        failed_attempts: Number of failed attempts
        
    Returns:
        True if account should be locked
    """
    return failed_attempts >= 5  # Lock after 5 failed login attempts


def should_lock_otp_account(failed_otp_attempts: int) -> bool:
    """
    Check if account should be locked based on failed OTP attempts.
    
    Args:
        failed_otp_attempts: Number of failed OTP attempts
        
    Returns:
        True if account should be locked
    """
    return failed_otp_attempts >= 3  # Lock after 3 failed OTP attempts


def calculate_lock_time(lock_minutes: int = 5) -> datetime:
    """
    Calculate lock expiration time.
    
    Args:
        lock_minutes: Number of minutes to lock account
        
    Returns:
        Lock expiration datetime
    """
    from datetime import timedelta
    return datetime.utcnow() + timedelta(minutes=lock_minutes)


def is_account_locked(locked_until: Optional[datetime]) -> bool:
    """
    Check if account is currently locked.
    
    Args:
        locked_until: Lock expiration time
        
    Returns:
        True if account is locked
    """
    if locked_until is None:
        return False
    return datetime.utcnow() < locked_until
