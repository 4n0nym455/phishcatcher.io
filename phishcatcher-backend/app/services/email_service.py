"""
Comprehensive Email Service for PhishCatcher

Unified email service with consistent dark theme styling.
"""

import logging
from datetime import datetime, timezone
from app.services.brevo_service import brevo_service
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_frontend_url(path: str = '') -> str:
    """Get the frontend URL with optional path."""
    settings = get_settings()
    base_url = settings.FRONTEND_URL.rstrip('/')
    return f"{base_url}/{path.lstrip('/')}" if path else base_url


class EmailService:
    """Comprehensive email service with consistent dark theme."""

    def __init__(self):
        self.brevo = brevo_service

    async def send_otp_verification(self, to_email: str, user_name: str, code: str, action: str = "verify your account") -> bool:
        """Send OTP verification email."""
        expiry_time = (datetime.now(timezone.utc).strftime('%I:%M %p UTC'))

        html = self.brevo._build_email(
            subject="PhishCatcher - Verification Code",
            title="Verify Your Email",
            message=f"Hello <strong>{user_name}</strong>,<br><br>You requested to {action}. Use the code below to verify:",
            action_text=code,
            security_info=f"&#128274; This code expires in <strong>10 minutes</strong> ({expiry_time})<br>Never share this code with anyone.",
            status="default"
        )

        return await self.brevo.send_email(to_email, "PhishCatcher - Verification Code", html)

    async def send_welcome_email(self, to_email: str, user_name: str, dashboard_url: str = None) -> bool:
        """Send welcome/onboarding email."""
        dashboard_url = dashboard_url or get_frontend_url('dashboard')

        html = self.brevo._build_email(
            subject="Welcome to PhishCatcher",
            title="&#127881; Welcome to PhishCatcher",
            message=f"Hello <strong>{user_name}</strong>,<br><br>Your account is ready! Start analyzing emails for phishing threats today.",
            action_url=dashboard_url,
            action_text="Go to Dashboard",
            security_info="Your account is secured with multi-factor authentication support.",
            status="success"
        )

        return await self.brevo.send_email(to_email, "Welcome to PhishCatcher!", html)

    async def send_password_reset(self, to_email: str, user_name: str, reset_code: str, reset_url: str, ip_address: str = None) -> bool:
        """Send password reset email."""
        expiry_time = (datetime.now(timezone.utc).strftime('%I:%M %p UTC'))

        html = self.brevo._build_email(
            subject="PhishCatcher - Password Reset",
            title="Reset Your Password",
            message=f"Hello <strong>{user_name}</strong>,<br><br>You requested a password reset. Use the code below or click the button to set a new password:",
            action_url=reset_url,
            action_text="Reset Password",
            security_info=f"&#128274; This reset link expires in <strong>1 hour</strong><br>Requested from: {ip_address or 'Unknown'}",
            status="warning"
        )

        return await self.brevo.send_email(to_email, "PhishCatcher - Password Reset", html)

    async def send_account_suspended(self, to_email: str, user_name: str, status: str, reason: str, actions: list, action_url: str = None) -> bool:
        """Send account suspension notification email."""
        action_url = action_url or get_frontend_url('account')

        actions_html = "<br>".join([f"• {action}" for action in actions])

        html = self.brevo._build_email(
            subject="PhishCatcher - Account Action Required",
            title="&#9888;&#65039; Account Action Required",
            message=f"Hello <strong>{user_name}</strong>,<br><br><strong>Status:</strong> {status}<br><strong>Reason:</strong> {reason}<br><br><strong>Actions needed:</strong><br>{actions_html}",
            action_url=action_url,
            action_text="Review Account",
            security_info=f"Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}<br>Contact support if you believe this is an error.",
            status="warning"
        )

        return await self.brevo.send_email(to_email, "PhishCatcher - Account Action Required", html)

    async def send_security_alert(self, to_email: str, user_name: str, action: str, ip_address: str = None, user_agent: str = None) -> bool:
        """Send security alert email."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        html = self.brevo._build_email(
            subject="PhishCatcher - Security Alert",
            title="&#9888;&#65039; Security Alert",
            message=f"Hello <strong>{user_name}</strong>,<br><br>A sensitive action was performed on your account.",
            security_info=f"<strong>Action:</strong> {action.replace('_', ' ').title()}<br><strong>Time:</strong> {timestamp}<br><strong>IP:</strong> {ip_address or 'Unknown'}<br><strong>Device:</strong> {user_agent or 'Unknown'}",
            status="error"
        )

        return await self.brevo.send_email(to_email, f"PhishCatcher - Security Alert: {action.replace('_', ' ').title()}", html)

    async def send_account_approved(self, to_email: str, user_name: str, dashboard_url: str = None) -> bool:
        """Send account approval notification email."""
        dashboard_url = dashboard_url or get_frontend_url('dashboard')

        html = self.brevo._build_email(
            subject="PhishCatcher - Account Approved",
            title="&#9989; Account Approved",
            message=f"Hello <strong>{user_name}</strong>,<br><br>Your PhishCatcher account has been approved! You can now start protecting yourself from phishing attacks.",
            action_url=dashboard_url,
            action_text="Get Started",
            security_info=f"Approved on: {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            status="success"
        )

        return await self.brevo.send_email(to_email, "PhishCatcher - Your Account Has Been Approved", html)

    async def send_custom_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send custom email content."""
        return await self.brevo.send_email(to_email, subject, html_content)


email_service = EmailService()


async def send_password_reset_email(to_email: str, user_name: str, reset_code: str, reset_url: str, ip_address: str = None) -> bool:
    """Wrapper for backward compatibility."""
    return await email_service.send_password_reset(to_email, user_name, reset_code, reset_url, ip_address)


async def send_password_change_notification(to_email: str, user_name: str = None) -> bool:
    """Wrapper for backward compatibility."""
    return await email_service.send_custom_email(
        to_email,
        "PhishCatcher - Password Changed",
        f"<p>Hello{', ' + user_name if user_name else ''},</p><p>Your password has been changed successfully.</p><p>If you didn't make this change, please contact support immediately.</p>"
    )
