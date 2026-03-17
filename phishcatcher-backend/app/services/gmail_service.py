"""
Gmail Service Module

This module handles Gmail API integration for real-time email analysis.
Includes OAuth2 authentication, email fetching, and phishing detection.
"""

import os
import json
import base64
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings
from app.services.email_analyzer import analyze_email_content
from app.models.user import User
from app.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly'
]

class GmailService:
    """Service for Gmail API integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client_config = {
            "web": {
                "client_id": self.settings.GMAIL_CLIENT_ID,
                "client_secret": self.settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.GMAIL_REDIRECT_URI]
            }
        }
    
    def get_auth_url(self, user_id: str) -> str:
        """Get Gmail OAuth authorization URL."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=self.settings.GMAIL_REDIRECT_URI
        )
        flow.state = user_id  # Use user_id as state parameter
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and store credentials."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=self.settings.GMAIL_REDIRECT_URI,
            state=state
        )
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user info from Gmail
            service = build('gmail', 'v1', credentials=credentials)
            user_info = service.users().getProfile(userId='me').execute()
            
            # Store credentials for user
            await self._store_credentials(state, credentials, user_info)
            
            return {
                "success": True,
                "email": user_info.get('emailAddress'),
                "historyId": user_info.get('historyId')
            }
        except Exception as e:
            logger.error(f"Gmail OAuth callback error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _store_credentials(self, user_id: str, credentials, user_info: Dict):
        """Store Gmail credentials for user."""
        # In a real implementation, you'd store this in the database
        # For now, we'll store it in a file or encrypted field
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        # Store in user's Gmail settings (you'd need to add this to your User model)
        async with get_db_session() as db:
            # Find user by state (which contains user_id)
            result = await db.execute(select(User).where(User.email == user_id))
            user = result.scalar_one_or_none()
            if user:
                # You'd need to add gmail_credentials field to User model
                user.gmail_credentials = json.dumps(credentials_data)
                user.gmail_email = user_info.get('emailAddress')
                user.gmail_connected_at = datetime.utcnow()
                await db.commit()
    
    async def disconnect_gmail(self, user_id: str) -> bool:
        """Disconnect Gmail account for user."""
        try:
            async with get_db_session() as db:
                result = await db.execute(select(User).where(User.email == user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.gmail_credentials = None
                    user.gmail_email = None
                    user.gmail_connected_at = None
                    await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error disconnecting Gmail: {e}")
            return False
    
    async def get_gmail_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get stored Gmail credentials for user."""
        try:
            async with get_db() as db:
                user = await db.get(User, user_id)
                if not user or not user.gmail_credentials:
                    return None
                
                credentials_data = json.loads(user.gmail_credentials)
                
                credentials = Credentials(
                    token=credentials_data['token'],
                    refresh_token=credentials_data.get('refresh_token'),
                    token_uri=credentials_data['token_uri'],
                    client_id=credentials_data['client_id'],
                    client_secret=credentials_data['client_secret'],
                    scopes=credentials_data['scopes']
                )
                
                if credentials_data.get('expiry'):
                    credentials.expiry = datetime.fromisoformat(credentials_data['expiry'])
                
                return credentials
        except Exception as e:
            logger.error(f"Error getting Gmail credentials: {e}")
            return None
    
    async def fetch_recent_emails(self, user_id: str, max_results: int = 10) -> List[Dict]:
        """Fetch recent emails from Gmail."""
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return []
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get recent messages
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q='is:unread'  # Only fetch unread emails
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract email content
                email_data = self._parse_email(msg)
                email_data['analysis'] = await analyze_email_content(email_data)
                emails.append(email_data)
            
            return emails
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
    
    def _parse_email(self, message: Dict) -> Dict:
        """Parse Gmail message into structured format."""
        headers = message['payload']['headers']
        
        # Extract headers
        subject = ''
        from_email = ''
        date = ''
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                from_email = header['value']
            elif header['name'] == 'Date':
                date = header['value']
        
        # Extract body
        body = ''
        if 'parts' in message['payload']:
            # Multipart message
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        else:
            # Single part message
            data = message['payload']['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return {
            'id': message['id'],
            'subject': subject,
            'from': from_email,
            'date': date,
            'body': body,
            'snippet': message.get('snippet', ''),
            'labels': message.get('labelIds', [])
        }
    
    async def mark_as_safe(self, user_id: str, message_id: str) -> bool:
        """Mark email as safe (remove from spam/phishing)."""
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return False
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            # Remove spam label and add safe label
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'removeLabelIds': ['SPAM'],
                    'addLabelIds': ['SAFE']  # You'd need to create this label first
                }
            ).execute()
            
            return True
        except HttpError as e:
            logger.error(f"Error marking email as safe: {e}")
            return False
    
    async def report_phishing(self, user_id: str, message_id: str) -> bool:
        """Report email as phishing."""
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return False
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            # Add spam label and remove from inbox
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': ['SPAM'],
                    'removeLabelIds': ['INBOX']
                }
            ).execute()
            
            return True
        except HttpError as e:
            logger.error(f"Error reporting phishing: {e}")
            return False

# Global Gmail service instance
gmail_service = GmailService()
