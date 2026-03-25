"""
Server-Side OAuth Flow

Fixed:
  - 'async with get_db() as db' replaced with 'async with get_db_session() as db'
    get_db() is an async generator (uses yield), not an asynccontextmanager.
    get_db_session() IS decorated with @asynccontextmanager and works correctly.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from datetime import datetime, timedelta
import secrets
import json

from app.models.user import User
from app.database import get_db_session   # FIX: was importing get_db
from app.services.google_oauth import google_oauth_service
from app.services.security import create_access_token, create_refresh_token, create_mfa_session_token
from app.routers.auth import normalize_email, get_password_hash
from app.services.activation_service import activation_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["server-oauth"])

# In production, use Redis for oauth_states
oauth_states = {}


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


@router.get("/server/google/login")
async def server_google_login():
    try:
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=5)
        }

        from app.config import get_settings
        settings = get_settings()
        auth_url_data = google_oauth_service.get_auth_url(redirect_uri=settings.GOOGLE_REDIRECT_URI)
        auth_url = auth_url_data["auth_url"]
        auth_url = auth_url.replace(f"state={auth_url_data['state']}", f"state={state}")

        return RedirectResponse(url=auth_url, status_code=302)

    except Exception as e:
        logger.error(f"Server OAuth login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate OAuth flow")


@router.get("/server/google/callback")
async def server_google_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None
):
    try:
        if error:
            return RedirectResponse(url=f"http://localhost:5173/login?error={error}", status_code=302)

        if not code or not state:
            return RedirectResponse(url="http://localhost:5173/login?error=missing_parameters", status_code=302)

        if state not in oauth_states:
            return RedirectResponse(url="http://localhost:5173/login?error=invalid_state", status_code=302)

        state_data = oauth_states[state]
        if datetime.utcnow() > state_data["expires_at"]:
            del oauth_states[state]
            return RedirectResponse(url="http://localhost:5173/login?error=expired_state", status_code=302)

        del oauth_states[state]

        token_data = await google_oauth_service.handle_oauth_callback(code, state)
        if not token_data.get("success"):
            return RedirectResponse(url="http://localhost:5173/login?error=token_exchange_failed", status_code=302)

        # FIX: use get_db_session() — get_db() is an async generator, not a context manager
        async with get_db_session() as db:
            result = await db.execute(select(User).where(User.email == token_data['email']))
            user = result.scalar_one_or_none()

            if not user:
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

                activation_token = activation_service.generate_activation_token(str(user.id))
                activation_code = activation_service.generate_activation_code(str(user.id))
                email_sent = await activation_service.send_activation_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    user_id=str(user.id),
                    activation_token=activation_token,
                    activation_code=activation_code
                )

                if not email_sent:
                    return RedirectResponse(url="http://localhost:5173/login?error=email_failed", status_code=302)

                return RedirectResponse(
                    url=f"http://localhost:5173/activation-pending?email={user.email}&full_name={user.full_name or ''}",
                    status_code=302
                )

            if user.account_status == "pending":
                activation_token = activation_service.generate_activation_token(str(user.id))
                activation_code = activation_service.generate_activation_code(str(user.id))
                await activation_service.send_activation_email(
                    user_email=user.email,
                    user_name=user.full_name or user.email.split('@')[0],
                    user_id=str(user.id),
                    activation_token=activation_token,
                    activation_code=activation_code
                )
                return RedirectResponse(
                    url=f"http://localhost:5173/activation-pending?email={user.email}&full_name={user.full_name or ''}",
                    status_code=302
                )

            if user.mfa_enabled:
                mfa_session_token = create_mfa_session_token(
                    data={"sub": str(user.id), "type": "mfa_session"},
                    expires_delta=timedelta(minutes=10)
                )
                return RedirectResponse(
                    url=f"http://localhost:5173/mfa-verification?mfa_session_token={mfa_session_token}",
                    status_code=302
                )

            access_token = create_access_token(data={"sub": str(user.id)})
            refresh_token = create_refresh_token(data={"sub": str(user.id)})

            tokens = json.dumps({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                }
            })
            encoded_tokens = secrets.token_urlsafe(32)
            oauth_states[encoded_tokens] = {
                "tokens": tokens,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(minutes=1)
            }

            return RedirectResponse(
                url=f"http://localhost:5173/oauth-success?token_id={encoded_tokens}",
                status_code=302
            )

    except Exception as e:
        logger.error(f"Server OAuth callback error: {e}")
        return RedirectResponse(url="http://localhost:5173/login?error=server_error", status_code=302)


@router.post("/server/oauth/tokens/{token_id}")
async def get_oauth_tokens(token_id: str):
    try:
        if token_id not in oauth_states:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found or expired")

        token_data = oauth_states[token_id]
        if datetime.utcnow() > token_data["expires_at"]:
            del oauth_states[token_id]
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token expired")

        tokens = json.loads(token_data["tokens"])
        del oauth_states[token_id]
        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving OAuth tokens: {e}")