"""
Gmail Service Module - fixed version

Fixed:
  - Added 'from sqlalchemy import select' (was missing, caused NameError)
  - Replaced 'async with get_db() as db' with 'async with get_db_session() as db'
    get_db() is an async generator, not an asynccontextmanager
  - Replaced 'await db.get(User, user_id)' with proper select() query
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

from sqlalchemy import select   # FIX: was missing entirely

from app.config import get_settings
from app.services.email_analyzer import analyze_email_content
from app.models.user import User
from app.database import get_db_session  # FIX: was importing get_db
import logging

logger = logging.getLogger(__name__)

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly'
]


class GmailService:
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

    def get_auth_url(self, user_id: str, email: str = None) -> str:
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=self.settings.GMAIL_REDIRECT_URI
        )
        auth_params = {
            'access_type': 'offline', 
            'include_granted_scopes': 'true',
            'state': user_id  # Pass user_id as state for CSRF
        }
        if email:
            auth_params['login_hint'] = email
        auth_url, _ = flow.authorization_url(**auth_params)
        return auth_url

    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        try:
            import uuid
            user_id = uuid.UUID(state)
            user_id_str = str(user_id)
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid state parameter (not a valid UUID): {state}")
            return {"success": False, "error": f"Invalid state parameter: {str(e)}"}
        
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=self.settings.GMAIL_REDIRECT_URI,
            state=state
        )
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            service = build('gmail', 'v1', credentials=credentials)
            user_info = service.users().getProfile(userId='me').execute()
            await self._store_credentials(user_id_str, credentials, user_info)
            return {"success": True, "email": user_info.get('emailAddress'), "historyId": user_info.get('historyId')}
        except Exception as e:
            logger.error(f"Gmail OAuth callback error: {e}")
            return {"success": False, "error": str(e)}

    async def _store_credentials(self, user_id: str, credentials, user_info: Dict):
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else [],
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        import uuid
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if user:
                user.gmail_credentials = json.dumps(credentials_data)
                user.gmail_email = user_info.get('emailAddress')
                user.gmail_connected_at = datetime.utcnow()
                await db.commit()

    async def _update_stored_credentials(self, user_id: str, credentials):
        """Update stored credentials after refresh."""
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else [],
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        import uuid
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if user:
                user.gmail_credentials = json.dumps(credentials_data)
                await db.commit()
                logger.info(f"Updated Gmail credentials for user {user_id}")

    async def disconnect_gmail(self, user_id: str) -> bool:
        try:
            import uuid
            async with get_db_session() as db:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
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
        try:
            import uuid
            async with get_db_session() as db:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if not user or not user.gmail_credentials:
                    return None

                credentials_data = json.loads(user.gmail_credentials)
                
                required_fields = ['token', 'token_uri', 'client_id', 'client_secret']
                missing = [f for f in required_fields if not credentials_data.get(f)]
                if missing:
                    logger.error(f"Gmail credentials missing required fields: {missing}")
                    return None
                
                credentials = Credentials(
                    token=credentials_data['token'],
                    refresh_token=credentials_data.get('refresh_token'),
                    token_uri=credentials_data['token_uri'],
                    client_id=credentials_data['client_id'],
                    client_secret=credentials_data['client_secret'],
                    scopes=credentials_data.get('scopes', [])
                )
                if credentials_data.get('expiry'):
                    credentials.expiry = datetime.fromisoformat(credentials_data['expiry'])
                
                # Check if credentials are expired and refresh if needed
                if credentials.expired:
                    try:
                        credentials.refresh(Request())
                        # Update stored credentials with refreshed token
                        await self._update_stored_credentials(user_id, credentials)
                        logger.info(f"Refreshed Gmail credentials for user {user_id}")
                    except Exception as refresh_error:
                        logger.error(f"Failed to refresh Gmail credentials: {refresh_error}")
                        return None
                
                return credentials
        except Exception as e:
            logger.error(f"Error getting Gmail credentials: {e}")
            return None

    async def fetch_recent_emails(self, user_id: str, max_results: int = 10) -> List[Dict]:
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return []
        try:
            service = build('gmail', 'v1', credentials=credentials)
            results = service.users().messages().list(userId='me', maxResults=max_results, q='is:unread').execute()
            messages = results.get('messages', [])
            emails = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                email_data = self._parse_email(msg)
                email_data['analysis'] = await analyze_email_content(email_data)
                emails.append(email_data)
            return emails
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []

    async def fetch_emails_paginated(
        self,
        user_id: str,
        max_results: int = 20,
        page_token: str = None,
        query: str = None
    ) -> Dict[str, Any]:
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return {"emails": [], "next_page_token": None}
        try:
            service = build('gmail', 'v1', credentials=credentials)
            kwargs = {"userId": 'me', "maxResults": max_results}
            if page_token:
                kwargs["pageToken"] = page_token
            if query:
                kwargs["q"] = query
            results = service.users().messages().list(**kwargs).execute()
            messages = results.get('messages', [])
            next_token = results.get('nextPageToken')
            
            emails = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                email_data = self._parse_email(msg)
                emails.append(email_data)
            
            return {
                "emails": emails,
                "next_page_token": next_token,
                "count": len(emails),
                "query": query
            }
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {"emails": [], "next_page_token": None, "error": str(e)}

    async def search_emails(
        self,
        user_id: str,
        query: str,
        max_results: int = 50,
        page_token: str = None
    ) -> Dict[str, Any]:
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return {"emails": [], "next_page_token": None, "error": "Gmail not connected"}
        
        if not query or not query.strip():
            return {"emails": [], "next_page_token": None, "error": "Query is required"}
        
        return await self.fetch_emails_paginated(
            user_id, 
            max_results=max_results, 
            page_token=page_token, 
            query=query.strip()
        )

    def build_filter_query(
        self,
        filter_type: str,
        date_from: str = None,
        date_to: str = None,
        from_address: str = None,
        subject_keyword: str = None,
        has_attachments: bool = None
    ) -> str:
        parts = []
        
        filter_queries = {
            "unread": "is:unread",
            "read": "is:read",
            "starred": "is:starred",
            "important": "is:important",
            "attachments": "has:attachment",
            "no_attachments": "has:nattachment",
            "7days": f"newer_than:7d",
            "30days": f"newer_than:30d",
            "90days": f"newer_than:90d",
        }
        
        if filter_type in filter_queries:
            parts.append(filter_queries[filter_type])
        
        if date_from:
            parts.append(f"after:{date_from}")
        if date_to:
            parts.append(f"before:{date_to}")
        if from_address:
            parts.append(f"from:{from_address}")
        if subject_keyword:
            parts.append(f"subject:{subject_keyword}")
        if has_attachments is True:
            parts.append("has:attachment")
        elif has_attachments is False:
            parts.append("has:nattachment")
        
        return " ".join(parts)

    async def get_email_by_id(self, user_id: str, message_id: str, format: str = 'raw') -> Optional[Dict]:
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return None
        try:
            service = build('gmail', 'v1', credentials=credentials)
            msg = service.users().messages().get(userId='me', id=message_id, format=format).execute()
            return msg
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return None
    
    async def get_email_headers(self, user_id: str, message_id: str) -> Optional[Dict]:
        """Get email with full headers for subject/sender extraction."""
        return await self.get_email_by_id(user_id, message_id, format='full')

    def _parse_email(self, message: Dict) -> Dict:
        headers = message['payload']['headers']
        subject = from_email = date = ''
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                from_email = header['value']
            elif header['name'] == 'Date':
                date = header['value']

        body = ''
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'data' in message['payload'].get('body', {}):
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')

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
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return False
        try:
            service = build('gmail', 'v1', credentials=credentials)
            service.users().messages().modify(
                userId='me', id=message_id,
                body={'removeLabelIds': ['SPAM']}
            ).execute()
            return True
        except HttpError as e:
            logger.error(f"Error marking email as safe: {e}")
            return False

    async def report_phishing(self, user_id: str, message_id: str) -> bool:
        credentials = await self.get_gmail_credentials(user_id)
        if not credentials:
            return False
        try:
            service = build('gmail', 'v1', credentials=credentials)
            service.users().messages().modify(
                userId='me', id=message_id,
                body={'addLabelIds': ['SPAM'], 'removeLabelIds': ['INBOX']}
            ).execute()
            return True
        except HttpError as e:
            logger.error(f"Error reporting phishing: {e}")
            return False


gmail_service = GmailService()