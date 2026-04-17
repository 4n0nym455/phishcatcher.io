"""
Token Service - Token Revocation and Management

This module provides token revocation functionality:
- Revoke individual tokens (logout)
- Check if token is revoked
- Revoke all tokens for a user (password change, etc.)
"""

from typing import Optional, Set
import time
import hmac
import hashlib

from app.config import get_settings


class TokenService:
    """
    Token service for managing token revocation and signing.
    """
    
    def __init__(self):
        self._revoked_tokens: Set[str] = set()
    
    async def revoke_token(self, jti: str, redis_client, ttl_seconds: int = 3600) -> None:
        """
        Revoke a token by adding its JTI to the revocation list.
        
        Args:
            jti: JWT Token ID (from token payload)
            redis_client: Async Redis client
            ttl_seconds: Time to live for the revoked token entry
        """
        if not jti:
            return
            
        key = f"revoked_token:{jti}"
        await redis_client.setex(key, ttl_seconds, "revoked")
        self._revoked_tokens.add(jti)
    
    async def is_token_revoked(self, jti: str, redis_client) -> bool:
        """
        Check if a token has been revoked.
        
        Args:
            jti: JWT Token ID
            redis_client: Async Redis client
            
        Returns:
            True if token is revoked, False otherwise
        """
        if not jti:
            return False
        
        if jti in self._revoked_tokens:
            return True
        
        key = f"revoked_token:{jti}"
        result = await redis_client.exists(key)
        return result > 0
    
    async def revoke_all_user_tokens(self, user_id: str, redis_client) -> None:
        """
        Revoke all tokens for a specific user.
        
        Args:
            user_id: User ID
            redis_client: Async Redis client
        """
        key = f"user_revoked_tokens:{user_id}"
        timestamp = int(time.time())
        await redis_client.setex(key, 86400, str(timestamp))
    
    async def check_user_tokens_revoked(self, user_id: str, redis_client, token_iat: int) -> bool:
        """
        Check if tokens issued before a certain time should be revoked.
        
        Args:
            user_id: User ID
            redis_client: Async Redis client
            token_iat: Token issued-at time (Unix timestamp)
            
        Returns:
            True if token should be considered revoked
        """
        key = f"user_revoked_tokens:{user_id}"
        revoked_at = await redis_client.get(key)
        
        if not revoked_at:
            return False
        
        revoked_timestamp = int(revoked_at.decode() if isinstance(revoked_at, bytes) else revoked_at)
        return token_iat < revoked_timestamp
    
    async def store_nonce(self, nonce: str, redis_client, ttl_seconds: int = 300) -> bool:
        """
        Store a nonce to prevent replay attacks.
        
        Args:
            nonce: Unique nonce value
            redis_client: Async Redis client
            ttl_seconds: Time to live (default 5 minutes)
            
        Returns:
            True if nonce was stored (new), False if already exists
        """
        key = f"nonce:{nonce}"
        result = await redis_client.set(key, "1", nx=True, ex=ttl_seconds)
        return result is not None
    
    async def is_nonce_used(self, nonce: str, redis_client) -> bool:
        """
        Check if a nonce has been used.
        
        Args:
            nonce: Nonce to check
            redis_client: Async Redis client
            
        Returns:
            True if nonce was already used
        """
        key = f"nonce:{nonce}"
        return await redis_client.exists(key) > 0
    
    def generate_signing_key(self) -> tuple[str, str]:
        """
        Generate a new HMAC signing key for a user.
        
        Returns:
            Tuple of (signing_key, signing_key_hash)
        """
        signing_key = secrets.token_hex(32)
        signing_key_hash = hashlib.sha256(signing_key.encode()).hexdigest()
        return signing_key, signing_key_hash
    
    def verify_signature(
        self,
        signing_key: str,
        method: str,
        path: str,
        timestamp: str,
        body: str,
        provided_signature: str
    ) -> bool:
        """
        Verify HMAC-SHA256 signature of a request.
        
        Args:
            signing_key: User's signing key
            method: HTTP method
            path: Request path
            timestamp: Unix timestamp string
            body: Request body (empty string if none)
            provided_signature: Signature provided in request header
            
        Returns:
            True if signature is valid
        """
        payload = f"{method.upper()}:{path}:{timestamp}:{body}"
        expected_signature = hmac.new(
            signing_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, provided_signature)
    
    def create_signature(
        self,
        signing_key: str,
        method: str,
        path: str,
        timestamp: int,
        body: str = ""
    ) -> str:
        """
        Create HMAC-SHA256 signature for a request.
        
        Args:
            signing_key: Signing key
            method: HTTP method
            path: Request path
            timestamp: Unix timestamp
            body: Request body
            
        Returns:
            HMAC signature
        """
        payload = f"{method.upper()}:{path}:{timestamp}:{body}"
        return hmac.new(
            signing_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()


import secrets
token_service = TokenService()
