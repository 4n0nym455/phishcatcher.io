"""
Google OAuth Service for Authentication

This module handles Google OAuth for user authentication (not Gmail integration).
Includes OAuth2 flow for sign-in/sign-up.
"""

import logging
from typing import Dict, Any, Optional
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import secrets
import time

from app.config import get_settings

logger = logging.getLogger(__name__)

# Google OAuth scopes for authentication
AUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

class GoogleOAuthService:
    """Service for Google OAuth authentication."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client_config = {
            "web": {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.GOOGLE_REDIRECT_URI]
            }
        }
    
    def get_auth_url(self, redirect_uri: str = None) -> Dict[str, str]:
        """Get Google OAuth authorization URL for authentication."""
        try:
            if not self.settings.GOOGLE_CLIENT_ID or not self.settings.GOOGLE_CLIENT_SECRET:
                raise ValueError("Google OAuth credentials not configured")
            
            # Use provided redirect URI or default to popup callback
            if not redirect_uri:
                if not self.settings.GOOGLE_REDIRECT_URI:
                    raise ValueError("Google OAuth redirect URI not configured")
                redirect_uri = self.settings.GOOGLE_REDIRECT_URI
            else:
                redirect_uri = redirect_uri
            
            state = secrets.token_urlsafe(32)
            
            # Create a minimal client config with only authentication scopes
            minimal_client_config = {
                "web": {
                    "client_id": self.settings.GOOGLE_CLIENT_ID,
                    "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            }
            
            flow = Flow.from_client_config(
                minimal_client_config,
                scopes=AUTH_SCOPES,  # Only authentication scopes
                redirect_uri=redirect_uri
            )
            flow.state = state
            
            # Generate auth URL with strict scope control
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='false',  # Don't include any previously granted scopes
                prompt='consent',  # Force consent dialog
                # Don't pass scope here - it's already set in the Flow constructor
            )
            
            return {
                "auth_url": auth_url,
                "state": state
            }
            
        except Exception as e:
            logger.error(f"Failed to generate OAuth URL: {e}")
            raise
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle Google OAuth callback and get user info."""
        try:
            # Validate inputs
            if not code or not state:
                raise ValueError("Missing required OAuth parameters")
            
            if not self.settings.GOOGLE_CLIENT_ID or not self.settings.GOOGLE_CLIENT_SECRET:
                raise ValueError("Google OAuth credentials not configured")
            
            # Create the same minimal client config for consistency
            minimal_client_config = {
                "web": {
                    "client_id": self.settings.GOOGLE_CLIENT_ID,
                    "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.settings.GOOGLE_REDIRECT_URI]
                }
            }
            
            flow = Flow.from_client_config(
                minimal_client_config,
                scopes=AUTH_SCOPES,  # Only authentication scopes
                redirect_uri=self.settings.GOOGLE_REDIRECT_URI
            )
            
            # Set the state to match what was used in the authorization request
            flow.state = state
            
            # Exchange authorization code for tokens
            try:
                flow.fetch_token(code=code)
                credentials = flow.credentials
                
                # Validate and filter scopes to only allow authentication scopes
                if hasattr(credentials, 'scopes') and credentials.scopes:
                    received_scopes = set(credentials.scopes)
                    expected_scopes = set(AUTH_SCOPES)
                    
                    # Filter out any Gmail scopes and only keep authentication scopes
                    filtered_scopes = received_scopes.intersection(expected_scopes)
                    gmail_scopes = received_scopes - expected_scopes
                    
                    if gmail_scopes:
                        logger.warning(f"Filtering out Gmail scopes: {gmail_scopes}")
                        # Update credentials with filtered scopes
                        credentials.scopes = list(filtered_scopes)
                    
                    # Ensure we have all required authentication scopes
                    missing_scopes = expected_scopes - filtered_scopes
                    if missing_scopes:
                        logger.error(f"Missing required authentication scopes: {missing_scopes}")
                        raise ValueError(f"Missing required OAuth scopes: {missing_scopes}")
                
            except Exception as e:
                logger.error(f"Failed to exchange authorization code: {e}")
                if "invalid_grant" in str(e):
                    raise ValueError("Authorization code is invalid or has expired")
                elif "redirect_uri_mismatch" in str(e):
                    raise ValueError("Redirect URI mismatch. Check your OAuth configuration.")
                elif "Scope has changed" in str(e):
                    raise ValueError("OAuth scope mismatch. Please ensure consistent scopes are used.")
                else:
                    raise ValueError(f"Token exchange failed: {str(e)}")
            
            # Get user info from Google
            try:
                service = build('oauth2', 'v2', credentials=credentials)
                user_info = service.userinfo().get().execute()
                
                if not user_info or not user_info.get('email'):
                    raise ValueError("Failed to retrieve user information from Google")
                
                logger.info(f"Successfully retrieved user info for: {user_info.get('email')}")
                
                return {
                    "success": True,
                    "email": user_info.get('email'),
                    "name": user_info.get('name'),
                    "picture": user_info.get('picture'),
                    "verified_email": user_info.get('verified_email', False)
                }
                
            except Exception as e:
                logger.error(f"Failed to retrieve user info: {e}")
                raise ValueError(f"Failed to retrieve user information: {str(e)}")
                
        except ValueError as e:
            logger.error(f"OAuth validation error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Google OAuth callback error: {e}")
            return {"success": False, "error": f"OAuth authentication failed: {str(e)}"}

# Global Google OAuth service instance
google_oauth_service = GoogleOAuthService()
