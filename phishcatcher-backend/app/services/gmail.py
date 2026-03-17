"""
Gmail Integration Service

This module provides OAuth authentication and email fetching functionality
for Gmail using the Google Gmail API.
"""

import base64
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from app.config import get_settings
from app.services.security import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class GmailService:
    """
    Gmail API service for OAuth and email operations.
    
    This class handles:
    - OAuth authentication flow
    - Token refresh
    - Email fetching
    - Push notification setup
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    def __init__(self, access_token: Optional[str] = None, 
                 refresh_token: Optional[str] = None,
                 token_expires_at: Optional[datetime] = None):
        """
        Initialize Gmail service.
        
        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            token_expires_at: Token expiration datetime
        """
        self.settings = get_settings()
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self._credentials: Optional[Credentials] = None
        self._service: Optional[build] = None
        
        if access_token and refresh_token:
            self._init_credentials()
    
    def _init_credentials(self):
        """Initialize Google credentials."""
        self._credentials = Credentials(
            token=self.access_token,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.settings.GOOGLE_CLIENT_ID,
            client_secret=self.settings.GOOGLE_CLIENT_SECRET,
            scopes=self.SCOPES
        )
    
    def _get_service(self) -> build:
        """Get or create Gmail API service."""
        if self._service is None:
            if self._credentials is None:
                raise ValueError("Credentials not initialized")
            
            # Refresh token if expired
            if self._credentials.expired and self._credentials.refresh_token:
                try:
                    self._credentials.refresh(Request())
                    self.access_token = self._credentials.token
                except RefreshError as e:
                    logger.error(f"Token refresh failed: {e}")
                    raise
            
            self._service = build('gmail', 'v1', credentials=self._credentials, cache_discovery=False)
        
        return self._service
    
    @staticmethod
    def get_authorization_url(state: str) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        from google_auth_oauthlib.flow import Flow
        
        settings = get_settings()
        
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=GmailService.SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        
        return authorization_url
    
    @staticmethod
    def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dictionary with tokens and user info
        """
        from google_auth_oauthlib.flow import Flow
        
        settings = get_settings()
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=GmailService.SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'expires_at': datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp() - datetime.utcnow().timestamp()) if credentials.expiry else None,
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture')
        }
    
    async def fetch_emails(self, max_results: int = 100, 
                          query: str = 'in:inbox',
                          page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query
            page_token: Page token for pagination
            
        Returns:
            Dictionary with emails and next page token
        """
        try:
            service = self._get_service()
            
            # List messages
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query,
                pageToken=page_token
            ).execute()
            
            messages = results.get('messages', [])
            next_page_token = results.get('nextPageToken')
            
            # Fetch full message details
            emails = []
            for msg_meta in messages:
                try:
                    email_data = await self._fetch_email_detail(service, msg_meta['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error fetching email {msg_meta['id']}: {e}")
                    continue
            
            return {
                'emails': emails,
                'next_page_token': next_page_token,
                'total_fetched': len(emails)
            }
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
    
    async def _fetch_email_detail(self, service, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full email details by message ID."""
        try:
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = self._extract_headers(message.get('payload', {}).get('headers', []))
            
            # Extract body
            body_text, body_html = self._extract_body(message.get('payload', {}))
            
            # Extract attachments info
            attachments = self._extract_attachments(message.get('payload', {}))
            
            # Get raw message for analysis
            raw_message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='raw'
            ).execute()
            
            raw_bytes = base64.urlsafe_b64decode(raw_message['raw'].encode('ASCII'))
            
            return {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'history_id': message.get('historyId'),
                'label_ids': message.get('labelIds', []),
                'snippet': message.get('snippet'),
                'headers': headers,
                'body_text': body_text,
                'body_html': body_html,
                'attachments': attachments,
                'size_estimate': message.get('sizeEstimate'),
                'raw': raw_bytes,
                'internal_date': message.get('internalDate')
            }
            
        except Exception as e:
            logger.error(f"Error fetching email detail {message_id}: {e}")
            return None
    
    def _extract_headers(self, headers: List[Dict[str, str]]) -> Dict[str, str]:
        """Extract relevant headers from message."""
        header_dict = {}
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name in ['from', 'to', 'cc', 'bcc', 'subject', 'date', 
                       'message-id', 'reply-to', 'return-path']:
                header_dict[name] = value
            elif name == 'authentication-results':
                header_dict['authentication_results'] = value
            elif name == 'dkim-signature':
                header_dict['dkim_signature'] = value
        
        return header_dict
    
    def _extract_body(self, payload: Dict[str, Any]) -> tuple[str, str]:
        """Extract text and HTML body from message payload."""
        text = ''
        html = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                    text = base64.urlsafe_b64decode(
                        part['body']['data'].encode('ASCII')
                    ).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html' and 'data' in part.get('body', {}):
                    html = base64.urlsafe_b64decode(
                        part['body']['data'].encode('ASCII')
                    ).decode('utf-8', errors='ignore')
                elif mime_type.startswith('multipart/'):
                    # Recursively extract from multipart
                    sub_text, sub_html = self._extract_body(part)
                    if sub_text and not text:
                        text = sub_text
                    if sub_html and not html:
                        html = sub_html
        else:
            # Single part message
            mime_type = payload.get('mimeType', '')
            body_data = payload.get('body', {}).get('data', '')
            
            if body_data:
                decoded = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8', errors='ignore')
                if mime_type == 'text/plain':
                    text = decoded
                elif mime_type == 'text/html':
                    html = decoded
        
        return text, html
    
    def _extract_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from payload."""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                disposition = part.get('headers', [])
                has_attachment = any(
                    h.get('name') == 'Content-Disposition' and 'attachment' in h.get('value', '')
                    for h in disposition
                )
                
                if has_attachment or part.get('filename'):
                    attachment = {
                        'filename': part.get('filename', 'unnamed'),
                        'mime_type': part.get('mimeType', 'application/octet-stream'),
                        'size': part.get('body', {}).get('size', 0),
                        'attachment_id': part.get('body', {}).get('attachmentId')
                    }
                    attachments.append(attachment)
                
                # Recursively check nested parts
                if 'parts' in part:
                    attachments.extend(self._extract_attachments(part))
        
        return attachments
    
    async def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """
        Download attachment content.
        
        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID
            
        Returns:
            Attachment bytes
        """
        service = self._get_service()
        
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        data = attachment.get('data', '')
        return base64.urlsafe_b64decode(data.encode('ASCII'))
    
    async def setup_push_notifications(self, topic_name: str) -> Dict[str, Any]:
        """
        Setup Gmail push notifications via Pub/Sub.
        
        Args:
            topic_name: Google Cloud Pub/Sub topic name
            
        Returns:
            Watch response with expiration and resource ID
        """
        service = self._get_service()
        
        request = {
            'labelIds': ['INBOX'],
            'topicName': topic_name
        }
        
        response = service.users().watch(userId='me', body=request).execute()
        
        return {
            'history_id': response.get('historyId'),
            'expiration': response.get('expiration'),
            'resource_id': response.get('resourceId')
        }
    
    async def stop_push_notifications(self, resource_id: str) -> bool:
        """
        Stop Gmail push notifications.
        
        Args:
            resource_id: Resource ID from watch response
            
        Returns:
            True if successful
        """
        try:
            service = self._get_service()
            service.users().stop(userId='me').execute()
            return True
        except Exception as e:
            logger.error(f"Error stopping push notifications: {e}")
            return False
    
    async def get_history(self, history_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Get history changes since the given history ID.
        
        Args:
            history_id: Starting history ID
            max_results: Maximum results to return
            
        Returns:
            List of history changes
        """
        service = self._get_service()
        
        results = service.users().history().list(
            userId='me',
            startHistoryId=history_id,
            maxResults=max_results
        ).execute()
        
        return results.get('history', [])
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get Gmail user profile."""
        service = self._get_service()
        profile = service.users().getProfile(userId='me').execute()
        return {
            'email': profile.get('emailAddress'),
            'messages_total': profile.get('messagesTotal'),
            'threads_total': profile.get('threadsTotal'),
            'history_id': profile.get('historyId')
        }
    
    def is_token_valid(self) -> bool:
        """Check if current access token is valid."""
        if not self._credentials:
            return False
        return not self._credentials.expired


class GmailServiceFactory:
    """Factory for creating GmailService instances."""
    
    @staticmethod
    def from_provider(provider) -> GmailService:
        """
        Create GmailService from EmailProvider model.
        
        Args:
            provider: EmailProvider database model
            
        Returns:
            GmailService instance
        """
        settings = get_settings()
        
        # Decrypt tokens
        access_token = decrypt_data(provider.access_token) if provider.access_token else None
        refresh_token = decrypt_data(provider.refresh_token) if provider.refresh_token else None
        
        return GmailService(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=provider.token_expires_at
        )
