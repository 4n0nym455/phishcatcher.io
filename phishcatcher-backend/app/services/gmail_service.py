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
from app.services.security import encrypt_oauth_token, decrypt_oauth_token, is_encrypted_token
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

    def get_auth_url(self, user_id: str, email: str = None, force_new: bool = False) -> str:
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=self.settings.GMAIL_REDIRECT_URI
        )
        auth_params = {
            'access_type': 'offline', 
            'include_granted_scopes': 'true',
            'state': user_id,  # Pass user_id as state for CSRF
            'prompt': 'consent'  # Force consent to ensure refresh token is always provided
        }
        # Only use login_hint if we want to reconnect an EXISTING account
        if email and not force_new:
            auth_params['login_hint'] = email
        auth_url, _ = flow.authorization_url(**auth_params)
        return auth_url

    async def handle_oauth_callback(self, code: str, state: str, user_id: str = None, db = None) -> Dict[str, Any]:
        try:
            if user_id is None:
                import uuid
                user_id = uuid.UUID(state)
                user_id_str = str(user_id)
            else:
                user_id_str = user_id
            
            logger.info(f"Gmail OAuth callback - state: {state}, user_id: {user_id_str}")
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
            
            account_id, is_new = await self._store_credentials_to_provider(user_id_str, credentials, user_info, db)
            return {"success": True, "email": user_info.get('emailAddress'), "historyId": user_info.get('historyId'), "account_id": account_id, "is_new": is_new}
        except Exception as e:
            logger.error(f"Gmail OAuth callback error: {e}")
            return {"success": False, "error": str(e)}

    async def _store_credentials_to_provider(self, user_id: str, credentials, user_info: Dict, db=None):
        """Store Gmail credentials to EmailProvider table for multi-account support."""
        from app.models.email_provider import EmailProvider
        import uuid
        
        logger.info(f"_store_credentials_to_provider called - user_id: {user_id}, email: {user_info.get('emailAddress')}")
        logger.info(f"db is None: {db is None}")
        
        if not credentials.refresh_token:
            logger.error("Gmail credentials missing refresh_token - this is required for token refresh")
        
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else [],
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        # Check if account already exists
        existing = None
        if db:
            from sqlalchemy import select
            result = await db.execute(
                select(EmailProvider).where(
                    EmailProvider.user_id == uuid.UUID(user_id),
                    EmailProvider.email_address == user_info.get('emailAddress'),
                    EmailProvider.provider_type == "gmail",
                    EmailProvider.is_active == True
                )
            )
            existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing account (encrypt token before storing)
            credentials_json = json.dumps(credentials_data)
            existing.access_token = encrypt_oauth_token(credentials_json)
            existing.is_connected = True
            existing.last_sync_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Updated existing Gmail account {existing.id} for user {user_id}")
            return str(existing.id), False  # False = reconnected
        else:
            # Create new account (encrypt token before storing)
            email_address = user_info.get('emailAddress')
            # Generate a friendly name
            provider_name = email_address.split('@')[0].title() + "'s Gmail"
            
            credentials_json = json.dumps(credentials_data)
            new_account = EmailProvider(
                user_id=uuid.UUID(user_id),
                provider_type="gmail",
                provider_name=provider_name,
                email_address=email_address,
                access_token=encrypt_oauth_token(credentials_json),
                is_active=True,
                is_connected=True,
                sync_enabled=True,
            )
            db.add(new_account)
            await db.commit()
            await db.refresh(new_account)
            logger.info(f"Created new Gmail account {new_account.id} for user {user_id}")
            return str(new_account.id), True  # True = new account

    async def _update_stored_credentials(self, user_id: str, credentials):
        """Update stored credentials after refresh (legacy User table)."""
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
                logger.info(f"Updated Gmail credentials in User table for user {user_id}")

    async def _update_provider_credentials(self, user_id: str, credentials, provider_id):
        """Update stored credentials in EmailProvider table after refresh."""
        from app.models.email_provider import EmailProvider
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
            result = await db.execute(
                select(EmailProvider).where(EmailProvider.id == uuid.UUID(provider_id))
            )
            provider = result.scalar_one_or_none()
            if provider:
                provider.access_token = encrypt_oauth_token(json.dumps(credentials_data))
                provider.last_sync_at = datetime.utcnow()
                await db.commit()
                logger.info(f"Updated Gmail credentials in EmailProvider table for provider {provider_id}")

    async def _invalidate_credentials(self, user_id: str):
        """Invalidate Gmail credentials for a user (legacy User table)."""
        import uuid
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if user:
                user.gmail_credentials = None
                user.gmail_email = None
                user.gmail_connected_at = None
                await db.commit()
                logger.info(f"Invalidated Gmail credentials for user {user_id}")

    async def _invalidate_provider_credentials(self, provider_id: str):
        """Invalidate Gmail credentials in EmailProvider table."""
        from app.models.email_provider import EmailProvider
        import uuid
        async with get_db_session() as db:
            result = await db.execute(
                select(EmailProvider).where(EmailProvider.id == uuid.UUID(provider_id))
            )
            provider = result.scalar_one_or_none()
            if provider:
                provider.is_connected = False
                provider.access_token = None
                await db.commit()
                logger.info(f"Invalidated Gmail credentials for provider {provider_id}")

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

    async def get_gmail_credentials(self, user_id: str, provider_id: str = None) -> Optional[Credentials]:
        try:
            import uuid
            async with get_db_session() as db:
                # First check EmailProvider table (new multi-account system)
                from app.models.email_provider import EmailProvider
                base_query = select(EmailProvider).where(
                    EmailProvider.user_id == uuid.UUID(user_id),
                    EmailProvider.provider_type == "gmail",
                    EmailProvider.is_connected == True
                )
                if provider_id:
                    base_query = base_query.where(EmailProvider.id == uuid.UUID(provider_id))
                else:
                    base_query = base_query.order_by(EmailProvider.is_default.desc().nullslast(), EmailProvider.created_at.desc())
                provider_result = await db.execute(base_query.limit(1))
                email_provider = provider_result.scalar_one_or_none()
                
                if email_provider and email_provider.access_token:
                    try:
                        # Decrypt the token if it's encrypted
                        token_data = email_provider.access_token
                        if is_encrypted_token(token_data):
                            token_data = decrypt_oauth_token(token_data)
                        provider_creds = json.loads(token_data)
                        credentials = Credentials(
                            token=provider_creds.get('token'),
                            refresh_token=provider_creds.get('refresh_token'),
                            token_uri=provider_creds.get('token_uri'),
                            client_id=provider_creds.get('client_id'),
                            client_secret=provider_creds.get('client_secret'),
                            scopes=provider_creds.get('scopes', [])
                        )
                        if provider_creds.get('expiry'):
                            credentials.expiry = datetime.fromisoformat(provider_creds['expiry'])
                        
                        # Check if token is expired or will expire within 5 minutes
                        if credentials.expired or (credentials.expiry and credentials.expiry <= datetime.utcnow() + timedelta(minutes=5)):
                            if credentials.refresh_token:
                                try:
                                    logger.info(f"Refreshing expired Gmail credentials for user {user_id}")
                                    credentials.refresh(Request())
                                    await self._update_provider_credentials(user_id, credentials, str(email_provider.id))
                                except Exception as refresh_error:
                                    logger.error(f"Failed to refresh credentials: {refresh_error}")
                                    await self._invalidate_provider_credentials(str(email_provider.id))
                                    return None
                            else:
                                logger.warning(f"Credentials expired but no refresh token for user {user_id}")
                                await self._invalidate_provider_credentials(str(email_provider.id))
                                return None
                        
                        logger.info(f"Using Gmail credentials from EmailProvider table for user {user_id}")
                        return credentials
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Failed to parse EmailProvider credentials: {e}")
                
                # Fallback to legacy User.gmail_credentials field
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if not user or not user.gmail_credentials:
                    logger.warning(f"User {user_id} has no gmail_credentials stored")
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
                
                # Check if token is expired or will expire within 5 minutes
                if credentials.expired or (credentials.expiry and credentials.expiry <= datetime.utcnow() + timedelta(minutes=5)):
                    if credentials.refresh_token:
                        try:
                            logger.info(f"Refreshing expired Gmail credentials for user {user_id}")
                            credentials.refresh(Request())
                            await self._update_stored_credentials(user_id, credentials)
                        except Exception as refresh_error:
                            logger.error(f"Failed to refresh credentials: {refresh_error}")
                            await self._invalidate_credentials(user_id)
                            return None
                    else:
                        logger.warning(f"Credentials expired but no refresh token for user {user_id}")
                        return None
                
                logger.info(f"Using legacy Gmail credentials from User table for user {user_id}")
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
        query: str = None,
        provider_id: str = None
    ) -> Dict[str, Any]:
        credentials = await self.get_gmail_credentials(user_id, provider_id=provider_id)
        if not credentials:
            logger.warning(f"No Gmail credentials for user {user_id}")
            return {"emails": [], "next_page_token": None, "error": "Gmail authentication failed. Please reconnect Gmail in Settings."}
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
            
            logger.info(f"Gmail API list returned {len(messages)} messages for query: '{query}'")
            
            emails = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                email_data = self._parse_email(msg)
                emails.append(email_data)
            
            return {
                "emails": emails,
                "next_page_token": next_token,
                "count": len(emails),
                "query": query,
                "total_results": len(messages)
            }
        except HttpError as e:
            error_details = str(e)
            logger.error(f"Gmail API HttpError: {error_details}")
            
            # Provide more helpful error messages based on HTTP status
            if hasattr(e, 'resp') and e.resp.status:
                if e.resp.status == 401:
                    return {"emails": [], "next_page_token": None, "error": "Gmail authentication failed. Please reconnect Gmail in Settings."}
                elif e.resp.status == 403:
                    return {"emails": [], "next_page_token": None, "error": "Gmail permission denied. Check your OAuth scopes."}
                elif e.resp.status == 429:
                    return {"emails": [], "next_page_token": None, "error": "Gmail rate limit exceeded. Please try again later."}
            
            return {"emails": [], "next_page_token": None, "error": error_details}
        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            return {"emails": [], "next_page_token": None, "error": f"Failed to fetch emails: {str(e)}"}

    async def search_emails(
        self,
        user_id: str,
        query: str,
        max_results: int = 50,
        page_token: str = None,
        provider_id: str = None
    ) -> Dict[str, Any]:
        credentials = await self.get_gmail_credentials(user_id, provider_id=provider_id)
        if not credentials:
            return {"emails": [], "next_page_token": None, "error": "Gmail not connected"}
        
        if not query or not query.strip():
            return {"emails": [], "next_page_token": None, "error": "Query is required"}
        
        return await self.fetch_emails_paginated(
            user_id, 
            max_results=max_results, 
            page_token=page_token, 
            query=query.strip(),
            provider_id=provider_id
        )

    def build_filter_query(
        self,
        filter_type: str,
        date_from: str = None,
        date_to: str = None,
        from_address: str = None,
        subject_keyword: str = None,
        has_attachments: bool = None,
        email_contains: str = None
    ) -> str:
        parts = []
        
        filter_queries = {
            "unread": "is:unread",
            "read": "is:read",
            "starred": "is:starred",
            "important": "is:important",
            "attachments": "has:attachment",
            "no_attachments": "has:nattachment",
            "promotions": "category:promotions",
            "social": "category:social",
            "7days": f"newer_than:7d",
            "30days": f"newer_than:30d",
            "90days": f"newer_than:90d",
        }
        
        if filter_type in filter_queries:
            parts.append(filter_queries[filter_type])
        
        if date_from:
            # Convert YYYY-MM-DD to YYYY/MM/DD for Gmail
            from_date_formatted = date_from.replace('-', '/')
            parts.append(f"after:{from_date_formatted}")
        if date_to:
            # Convert YYYY-MM-DD to YYYY/MM/DD for Gmail
            to_date_formatted = date_to.replace('-', '/')
            parts.append(f"before:{to_date_formatted}")
        if from_address:
            parts.append(f"from:{from_address}")
        if subject_keyword:
            parts.append(f"subject:{subject_keyword}")
        if email_contains:
            parts.append(f"{email_contains}")
        if has_attachments is True:
            parts.append("has:attachment")
        elif has_attachments is False:
            parts.append("has:nattachment")
        
        return " ".join(parts)

    async def get_email_by_id(self, user_id: str, message_id: str, format: str = 'raw', provider_id: str = None) -> Optional[Dict]:
        credentials = await self.get_gmail_credentials(user_id, provider_id=provider_id)
        if not credentials:
            return None
        try:
            service = build('gmail', 'v1', credentials=credentials)
            msg = service.users().messages().get(userId='me', id=message_id, format=format).execute()
            return msg
        except HttpError as e:
            error_msg = str(e)
            if e.resp.status == 404:
                logger.warning(f"Gmail API 404 for message {message_id}: {error_msg}")
                raise Exception(f"HttpError 404: Requested entity was not found")
            logger.error(f"Gmail API error: {e}")
            raise Exception(f"Gmail API error: {error_msg}")
    
    async def get_email_headers(self, user_id: str, message_id: str, provider_id: str = None) -> Optional[Dict]:
        """Get email with full headers for subject/sender extraction."""
        return await self.get_email_by_id(user_id, message_id, format='full', provider_id=provider_id)

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

        body_text = ''
        body_html = ''
        links = []
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                mime_type = part.get('mimeType', '')
                body_data = part.get('body', {})
                
                if 'data' in body_data:
                    try:
                        part_body = base64.urlsafe_b64decode(body_data['data']).decode('utf-8')
                    except (base64.binascii.Error, UnicodeDecodeError) as e:
                        logger.warning(f"Failed to decode email body part: {e}")
                        part_body = ''
                elif 'attachmentId' in body_data:
                    part_body = ''
                else:
                    part_body = ''
                
                if mime_type == 'text/plain' and not body_text:
                    body_text = part_body
                elif mime_type == 'text/html' and not body_html:
                    body_html = part_body
                    # Extract links from HTML
                    import re
                    url_pattern = re.compile(
                        r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?',
                        re.IGNORECASE
                    )
                    # Also try to extract anchor text
                    anchor_pattern = re.compile(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', re.IGNORECASE)
                    for match in anchor_pattern.findall(body_html):
                        url, anchor_text = match
                        links.append({'url': url, 'display_text': anchor_text.strip()})
                    # Also add URLs found in the HTML that might not have anchors
                    all_urls = url_pattern.findall(body_html)
                    for url in all_urls:
                        if not any(l['url'] == url for l in links):
                            links.append({'url': url, 'display_text': None})
        
        elif 'data' in message['payload'].get('body', {}):
            try:
                body_text = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode email body: {e}")
                body_text = ''

        return {
            'id': message['id'],
            'subject': subject,
            'from': from_email,
            'date': date,
            'body': body_text,
            'body_html': body_html,
            'links': links,
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