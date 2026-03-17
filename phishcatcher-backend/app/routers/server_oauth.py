"""
Server-Side OAuth Flow

This implements a server-side OAuth flow that redirects the user
directly instead of using popups, eliminating timing issues.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import secrets
import json

from app.models.user import User
from app.database import get_db
from app.services.google_oauth import google_oauth_service
from app.services.security import create_access_token, create_refresh_token, create_mfa_session_token
from app.routers.auth import normalize_email, get_password_hash
from app.services.activation_service import activation_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["server-oauth"])

# Store OAuth states temporarily (in production, use Redis)
oauth_states = {}

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str

@router.get("/server/google/login")
async def server_google_login():
    """Initiate server-side Google OAuth flow."""
    try:
        # Generate state and store it
        state = secrets.token_urlsafe(32)
        
        # Store state with timestamp (5 minute expiry)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=5)
        }
        
        # Get Google OAuth URL (not async)
        # Use the existing popup redirect URI that's already registered in Google Cloud
        existing_callback_uri = "http://localhost:5173/auth/google/callback"
        auth_url_data = google_oauth_service.get_auth_url(redirect_uri=existing_callback_uri)
        
        # Add our state to the URL
        auth_url = auth_url_data["auth_url"]
        auth_url = auth_url.replace(f"state={auth_url_data['state']}", f"state={state}")
        
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Server OAuth login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow"
        )

@router.get("/server/google/callback")
async def server_google_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None
):
    """Handle server-side Google OAuth callback."""
    try:
        if error:
            logger.error(f"OAuth error: {error}")
            # Redirect to frontend with error
            return RedirectResponse(
                url=f"http://localhost:5173/login?error={error}",
                status_code=302
            )
        
        if not code or not state:
            logger.error("Missing code or state in OAuth callback")
            return RedirectResponse(
                url="http://localhost:5173/login?error=missing_parameters",
                status_code=302
            )
        
        # Verify state
        logger.info(f"Looking for OAuth state: {state}")
        logger.info(f"Available states: {list(oauth_states.keys())}")
        
        if state not in oauth_states:
            logger.error(f"Invalid OAuth state: {state}")
            logger.error(f"Available states: {list(oauth_states.keys())}")
            return RedirectResponse(
                url="http://localhost:5173/login?error=invalid_state",
                status_code=302
            )
        
        # Check state expiry
        state_data = oauth_states[state]
        if datetime.utcnow() > state_data["expires_at"]:
            logger.error(f"Expired OAuth state: {state}")
            del oauth_states[state]
            return RedirectResponse(
                url="http://localhost:5173/login?error=expired_state",
                status_code=302
            )
        
        # Clean up state
        del oauth_states[state]
        
        # Process OAuth callback immediately
        token_data = await google_oauth_service.handle_oauth_callback(code, state)
        
        if not token_data.get("success"):
            logger.error(f"OAuth token exchange failed: {token_data}")
            return RedirectResponse(
                url=f"http://localhost:5173/login?error=token_exchange_failed",
                status_code=302
            )
        
        # Check if user exists
        async with get_db() as db:
            result = await db.execute(select(User).where(User.email == token_data['email']))
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user with pending status
                user = User(
                    email=token_data['email'],
                    normalized_email=normalize_email(token_data['email']),
                    password_hash=get_password_hash(secrets.token_urlsafe(32)),
                    full_name=token_data.get('name'),
                    email_verified=True,
                    account_status="pending"
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                
                # Generate activation token and code
                activation_token = activation_service.generate_activation_token(str(user.id))
                activation_code = activation_service.generate_activation_code(str(user.id))
                
                # Send activation email
                email_sent = await activation_service.send_activation_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    user_id=str(user.id),
                    activation_token=activation_token,
                    activation_code=activation_code
                )
                
                if not email_sent:
                    logger.error("Failed to send activation email")
                    return RedirectResponse(
                        url="http://localhost:5173/login?error=email_failed",
                        status_code=302
                    )
                
                # Redirect to activation pending page
                return RedirectResponse(
                    url=f"http://localhost:5173/activation-pending?email={user.email}&full_name={user.full_name or ''}&message=Please check your email for activation instructions",
                    status_code=302
                )
            
            # Handle existing users
            if user.account_status == "pending":
                # User exists but not activated - resend activation
                activation_token = activation_service.generate_activation_token(str(user.id))
                activation_code = activation_service.generate_activation_code(str(user.id))
                
                email_sent = await activation_service.send_activation_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    user_id=str(user.id),
                    activation_token=activation_token,
                    activation_code=activation_code
                )
                
                return RedirectResponse(
                    url=f"http://localhost:5173/activation-pending?email={user.email}&full_name={user.full_name or ''}&message=Your account is still pending activation. Please check your email.",
                    status_code=302
                )
            
            # Check if user has MFA enabled
            if user.mfa_enabled:
                # Generate MFA session token
                mfa_session_token = create_mfa_session_token(
                    data={"sub": str(user.id), "type": "mfa_session"}, 
                    expires_delta=timedelta(minutes=10)
                )
                
                # Store MFA session and redirect to MFA verification
                redirect_url = f"http://localhost:5173/mfa-verification?mfa_session_token={mfa_session_token}"
                return RedirectResponse(url=redirect_url, status_code=302)
            
            # Create access tokens for active users
            access_token = create_access_token(data={"sub": str(user.id)})
            refresh_token = create_refresh_token(data={"sub": str(user.id)})
            
            # Create redirect URL with tokens
            tokens = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                }
            }
            
            # Encode tokens for URL
            token_data = json.dumps(tokens)
            encoded_tokens = secrets.token_urlsafe(32)  # Simple encoding for demo
            
            # Store tokens temporarily (in production, use Redis with proper expiry)
            oauth_states[encoded_tokens] = {
                "tokens": token_data,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=1)
            }
            
            # Redirect to frontend with token identifier
            return RedirectResponse(
                url=f"http://localhost:5173/oauth-success?token_id={encoded_tokens}",
                status_code=302
            )
            
    except Exception as e:
        logger.error(f"Server OAuth callback error: {e}")
        return RedirectResponse(
            url=f"http://localhost:5173/login?error=server_error",
            status_code=302
        )

@router.post("/server/oauth/tokens/{token_id}")
async def get_oauth_tokens(token_id: str):
    """Retrieve OAuth tokens by token ID."""
    try:
        if token_id not in oauth_states:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found or expired"
            )
        
        token_data = oauth_states[token_id]
        
        # Check expiry
        if datetime.utcnow() > token_data["expires_at"]:
            del oauth_states[token_id]
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token expired"
            )
        
        # Return tokens and clean up
        tokens = json.loads(token_data["tokens"])
        del oauth_states[token_id]
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OAuth tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tokens"
        )
