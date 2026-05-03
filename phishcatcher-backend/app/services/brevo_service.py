"""
Brevo Email Service for PhishCatcher

Drop-in replacement for SendGridService. Uses Brevo's SMTP API (v3/smtp/email)
to send transactional emails with the same dark-theme HTML templates.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class BrevoService:
    """Enterprise-grade email service using Brevo with consistent dark theme."""

    API_URL = "https://api.brevo.com/v3/smtp/email"

    def __init__(self):
        self.settings = get_settings()

        api_key = getattr(self.settings, 'BREVO_API_KEY', None)
        if api_key and api_key.startswith('xkeysib-'):
            self.api_key = api_key
        else:
            self.api_key = None
            logger.warning("Brevo API key not configured or invalid format")

        self.from_email = getattr(self.settings, 'BREVO_FROM_EMAIL', None) or getattr(self.settings, 'FROM_EMAIL', 'noreply@phishcatcher.io')
        self.from_name = getattr(self.settings, 'BREVO_FROM_NAME', 'PhishCatcher')

    def _build_email(self, subject: str, title: str, message: str,
                     action_url: Optional[str] = None, action_text: Optional[str] = None,
                     security_info: Optional[str] = None, status: str = "default") -> str:
        """Build email HTML with consistent dark theme."""
        status_colors = {
            'default': ('rgba(139, 92, 246, 0.2)', 'rgba(139, 92, 246, 0.2)'),
            'success': ('rgba(34, 197, 94, 0.2)', 'rgba(34, 197, 94, 0.3)'),
            'warning': ('rgba(245, 158, 11, 0.2)', 'rgba(245, 158, 11, 0.3)'),
            'error': ('rgba(239, 68, 68, 0.2)', 'rgba(239, 68, 68, 0.3)'),
        }
        border_color, shadow_color = status_colors.get(status, status_colors['default'])

        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhishCatcher - {subject}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            line-height: 1.6;
            padding: 20px;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid {border_color};
            border-radius: 16px;
            overflow: hidden;
        }}
        .header {{
            padding: 40px 40px 20px 40px;
            text-align: center;
            border-bottom: 1px solid rgba(139, 92, 246, 0.1);
        }}
        .logo {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 20px;
        }}
        .logo-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: rgba(139, 92, 246, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }}
        .logo-text {{
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }}
        .content {{
            padding: 30px 40px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 16px;
            text-align: center;
        }}
        .message {{
            color: #cbd5e1;
            margin-bottom: 24px;
            line-height: 1.7;
        }}
        .code-box {{
            background: rgba(139, 92, 246, 0.1);
            border: 2px dashed rgba(139, 92, 246, 0.3);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            margin: 24px 0;
        }}
        .code {{
            font-size: 36px;
            font-weight: 700;
            color: #a78bfa;
            letter-spacing: 6px;
            font-family: 'Courier New', monospace;
        }}
        .expiry {{
            color: #94a3b8;
            font-size: 14px;
            margin-top: 12px;
        }}
        .button-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .action-button {{
            display: inline-block;
            padding: 14px 28px;
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: #ffffff;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            box-shadow: 0 4px 14px {shadow_color};
        }}
        .security-info {{
            background: rgba(139, 92, 246, 0.1);
            border: 1px solid rgba(139, 92, 246, 0.2);
            border-radius: 12px;
            padding: 20px;
            margin: 24px 0;
        }}
        .security-title {{
            font-weight: 600;
            color: #a78bfa;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .security-text {{
            color: #cbd5e1;
            font-size: 14px;
        }}
        .details-box {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 12px;
            padding: 20px;
            margin: 24px 0;
        }}
        .details-title {{
            font-weight: 600;
            color: #fca5a5;
            margin-bottom: 12px;
        }}
        .details-list {{
            list-style: none;
            color: #cbd5e1;
        }}
        .details-list li {{
            padding: 8px 0;
            border-bottom: 1px solid rgba(239, 68, 68, 0.1);
        }}
        .details-list li:last-child {{
            border-bottom: none;
        }}
        .footer {{
            padding: 20px 40px 40px 40px;
            text-align: center;
            border-top: 1px solid rgba(139, 92, 246, 0.1);
            background: rgba(15, 23, 42, 0.5);
        }}
        .footer-text {{
            color: #94a3b8;
            font-size: 12px;
        }}
        .footer-link {{
            color: #a78bfa;
            text-decoration: none;
        }}
        @media (max-width: 600px) {{
            .header, .content, .footer {{
                padding: 30px 25px;
            }}
            .title {{
                font-size: 20px;
            }}
            .code {{
                font-size: 28px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">&#128737;&#65039;</div>
                <span class="logo-text">PhishCatcher</span>
            </div>
        </div>

        <div class="content">
            <h1 class="title">{title}</h1>

            <div class="message">
                {message}
            </div>
''' + (f'''
            <div class="code-box">
                <div class="code">{action_text}</div>
            </div>
''' if action_text and not action_url else '') + f'''
''' + (f'''
            <div class="button-container">
                <a href="{action_url}" class="action-button">{action_text or 'Click Here'}</a>
            </div>
''' if action_url else '') + f'''
''' + (f'''
            <div class="security-info">
                <div class="security-title">&#128274; Security Information</div>
                <div class="security-text">{security_info}</div>
            </div>
''' if security_info else '') + '''
        </div>

        <div class="footer">
            <div class="footer-text">
                This email was sent by PhishCatcher. If you didn't request this, please
                contact support.
                <br><br>
                &copy; 2026 PhishCatcher. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>'''

    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using Brevo SMTP API."""
        if not self.api_key:
            logger.error("Brevo API key not initialized")
            return False

        try:
            payload = {
                "sender": {"name": self.from_name, "email": self.from_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.API_URL,
                    json=payload,
                    headers={
                        "api-key": self.api_key,
                        "content-type": "application/json",
                        "accept": "application/json",
                    },
                )

            if response.status_code == 201:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}: HTTP {response.status_code} {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    async def send_verification_code(self, to_email: str, code: str, action: str = "security_action") -> bool:
        """Send email verification code."""
        expiry_time = (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime('%I:%M %p UTC')

        html = self._build_email(
            subject=f"PhishCatcher - Verification Code",
            title="Verify Your Email",
            message=f"You requested to perform <strong>{action.replace('_', ' ').title()}</strong> on your PhishCatcher account. Use the code below to verify:",
            action_text=code,
            security_info=f"&#128274; This code expires in <strong>10 minutes</strong> ({expiry_time})<br>Never share this code with anyone. PhishCatcher will never ask for your password via email.",
            status="default"
        )

        return await self.send_email(to_email, f"PhishCatcher - Verification Code for {action.replace('_', ' ').title()}", html)

    async def send_password_reset(self, to_email: str, reset_url: str) -> bool:
        """Send password reset email."""
        html = self._build_email(
            subject="PhishCatcher - Password Reset Request",
            title="Reset Your Password",
            message="You requested a password reset for your PhishCatcher account. Click the button below to set a new password:",
            action_url=reset_url,
            action_text="Reset Password",
            security_info="This link will expire in <strong>1 hour</strong> for security reasons. If you didn't request this reset, please ignore this email.",
            status="warning"
        )

        return await self.send_email(to_email, "PhishCatcher - Password Reset Request", html)

    async def send_password_changed(self, to_email: str) -> bool:
        """Send password changed notification."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        html = self._build_email(
            subject="PhishCatcher - Password Changed",
            title="Password Successfully Changed",
            message="Your PhishCatcher account password has been changed successfully.",
            security_info=f"Changed at: <strong>{timestamp}</strong><br>If you didn't change your password, please contact support immediately.",
            status="success"
        )

        return await self.send_email(to_email, "PhishCatcher - Password Changed", html)

    async def send_security_alert(self, to_email: str, action: str, ip_address: str = None, user_agent: str = None) -> bool:
        """Send security alert email."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        html = self._build_email(
            subject=f"PhishCatcher - Security Alert",
            title="&#9888;&#65039; Security Alert",
            message=f"A sensitive action was performed on your PhishCatcher account.",
            security_info=f'''<strong>Action:</strong> {action.replace('_', ' ').title()}<br>
<strong>Time:</strong> {timestamp}<br>
<strong>IP Address:</strong> {ip_address or 'Unknown'}<br>
<strong>Device:</strong> {user_agent or 'Unknown'}''',
            status="error"
        )

        return await self.send_email(to_email, f"PhishCatcher - Security Alert: {action.replace('_', ' ').title()}", html)

    async def send_account_deletion(self, to_email: str) -> bool:
        """Send account deletion notification."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        html = self._build_email(
            subject="PhishCatcher - Account Deleted",
            title="Account Deleted",
            message="Your PhishCatcher account has been permanently deleted.",
            security_info=f"Deleted at: <strong>{timestamp}</strong><br>All your data has been removed from our systems.",
            status="error"
        )

        return await self.send_email(to_email, "PhishCatcher - Account Deleted", html)

    async def send_welcome(self, to_email: str, login_url: str) -> bool:
        """Send welcome email."""
        html = self._build_email(
            subject="Welcome to PhishCatcher",
            title="&#127881; Welcome to PhishCatcher",
            message="Your account has been created successfully. Start analyzing emails for phishing threats today!",
            action_url=login_url,
            action_text="Go to Dashboard",
            security_info="Your account is secured with multi-factor authentication support.",
            status="success"
        )

        return await self.send_email(to_email, "Welcome to PhishCatcher", html)


brevo_service = BrevoService()
