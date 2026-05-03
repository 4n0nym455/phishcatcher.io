"""
activation_service.py

Stateless activation flow backed by Redis.

Previous implementation stored tokens in plain Python dicts which meant:
- All pending activations were lost on every server restart / new worker
- In multi-process / multi-container deployments no two workers shared state

This version stores two Redis keys per user:
    activation:token:{user_id}  → opaque URL-safe token  (TTL 24 h)
    activation:code:{user_id}   → 6-digit numeric code   (TTL 10 min)

The email contains BOTH so the frontend can pre-fill the code while still
validating the token (binds the code to the intended recipient).
"""

from __future__ import annotations

import secrets
import logging
from datetime import datetime, timezone

from app.database import get_redis_client
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

# TTLs in seconds
TOKEN_TTL = 24 * 60 * 60   # 24 hours
CODE_TTL  = 10 * 60         # 10 minutes


def _token_key(user_id: str) -> str:
    return f"activation:token:{user_id}"


def _code_key(user_id: str) -> str:
    return f"activation:code:{user_id}"


class ActivationService:
    """Redis-backed activation token + code manager."""

    # ── Token ──────────────────────────────────────────────────────────────────

    async def generate_activation_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        redis = get_redis_client()
        await redis.setex(_token_key(user_id), TOKEN_TTL, token)
        logger.info("Activation token generated for user %s (TTL %ds)", user_id, TOKEN_TTL)
        return token

    async def verify_activation_token(self, user_id: str, token: str) -> bool:
        redis = get_redis_client()
        stored = await redis.get(_token_key(user_id))
        if not stored:
            logger.warning("No activation token found for user %s", user_id)
            return False
        return secrets.compare_digest(stored, token)

    # ── Code ───────────────────────────────────────────────────────────────────

    async def generate_activation_code(self, user_id: str) -> str:
        code  = f"{secrets.randbelow(1_000_000):06d}"
        redis = get_redis_client()
        await redis.setex(_code_key(user_id), CODE_TTL, code)
        logger.info("Activation code generated for user %s (TTL %ds)", user_id, CODE_TTL)
        return code

    async def verify_activation_code(self, user_id: str, code: str) -> bool:
        redis  = get_redis_client()
        stored = await redis.get(_code_key(user_id))
        if not stored:
            logger.warning("Activation code not found or expired for user %s", user_id)
            return False
        return secrets.compare_digest(stored, code)

    # ── Cleanup ─────────────────────────────────────────────────────────────────

    async def delete_activation_keys(self, user_id: str) -> None:
        """Call after successful activation to free Redis memory immediately."""
        redis = get_redis_client()
        await redis.delete(_token_key(user_id), _code_key(user_id))

    # ── Email ───────────────────────────────────────────────────────────────────

    async def send_activation_email(
        self,
        *,
        user_email:        str,
        user_name:         str,
        user_id:           str,
        activation_token:  str,
        activation_code:   str,
        frontend_url:      str = "http://localhost:5173",
    ) -> bool:
        """Render and send the activation email. Returns True on success."""
        activation_url = (
            f"{frontend_url}/activate"
            f"?token={activation_token}&email={user_email}"
        )
        html = _render_activation_email(user_name, activation_code, activation_url)
        try:
            ok = await email_service.send_custom_email(
                to_email=user_email,
                subject="Activate Your PhishCatcher Account",
                html_content=html,
            )
            if ok:
                logger.info("Activation email sent to %s", user_email)
            else:
                logger.error("Email service returned False for %s", user_email)
            return ok
        except Exception as exc:
            logger.exception("Failed to send activation email to %s: %s", user_email, exc)
            return False


# ── Template ───────────────────────────────────────────────────────────────────

def _render_activation_email(user_name: str, code: str, url: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Activate Your PhishCatcher Account</title>
  <style>
    body {{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#333;background:#f8f9fa;margin:0;padding:20px}}
    .container{{max-width:600px;margin:0 auto;background:#fff;border-radius:12px;padding:40px;box-shadow:0 4px 6px rgba(0,0,0,.1)}}
    .code-box{{background:#f3f4f6;border:2px dashed #e5e7eb;border-radius:8px;padding:20px;text-align:center;margin:20px 0}}
    .code{{font-size:32px;font-weight:bold;color:#7b61ff;letter-spacing:6px;font-family:monospace}}
    .btn{{display:inline-block;background:#7b61ff;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;margin:20px 0}}
    .warning{{background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:12px 16px;margin:16px 0;font-size:14px}}
  </style>
</head>
<body>
  <div class="container">
    <h1 style="color:#7b61ff">🎯 PhishCatcher</h1>
    <h2>Activate Your Account</h2>
    <p>Hi {user_name},</p>
    <p>Welcome to PhishCatcher! To activate your account, complete both steps below.</p>

    <div class="warning">
      ⏱ <strong>The activation code expires in 10 minutes.</strong>
      The activation link expires in 24 hours.
    </div>

    <h3>Step 1 – Your Activation Code</h3>
    <div class="code-box"><div class="code">{code}</div></div>

    <h3>Step 2 – Click the Activation Link</h3>
    <p>
      <a href="{url}" class="btn">Activate Account</a>
    </p>
    <p style="font-size:12px;word-break:break-all;color:#666">{url}</p>

    <h3>Step 3 – Enter Code &amp; Accept Terms</h3>
    <p>On the activation page enter the 6-digit code above, accept our Terms &amp;
    Conditions and Privacy Policy, then click <em>Activate Account</em>.</p>

    <hr style="border:none;border-top:1px solid #e5e7eb;margin:30px 0">
    <p style="font-size:12px;color:#999">
      If you did not create a PhishCatcher account, you can safely ignore this email.
      © {datetime.now(timezone.utc).year} PhishCatcher
    </p>
  </div>
</body>
</html>
""".strip()


# Singleton
activation_service = ActivationService()