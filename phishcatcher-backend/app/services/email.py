"""
Email Service

This module handles email sending functionality for the PhishCatcher application.
Uses HTML templates with orb_glow_sphere effect for professional email design.
"""

import logging
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from app.config import get_settings
from app.services.email_template_service import email_template_service, EmailTypes

logger = logging.getLogger(__name__)


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """
    Send password reset email to user using HTML template with orb_glow_sphere.
    
    Args:
        email: User's email address
        reset_token: Password reset token
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        settings = get_settings()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Render HTML email with orb_glow_sphere
        html_content = email_template_service.render_email(
            subject=EmailTypes.PASSWORD_RESET['subject'],
            title=EmailTypes.PASSWORD_RESET['title'],
            message=f"Hello,<br><br>We received a request to reset your password for your PhishCatcher account. Click the button below to reset your password.",
            action_url=reset_url,
            action_text="Reset Password",
            security_info=EmailTypes.PASSWORD_RESET['security_info'],
            status=EmailTypes.PASSWORD_RESET['status']
        )
        
        # Send email
        return await _send_email(
            to_email=email,
            subject=EmailTypes.PASSWORD_RESET['subject'],
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


async def send_otp_email(email: str, otp: str) -> bool:
    """
    Send OTP email to user using HTML template with orb_glow_sphere.
    
    Args:
        email: User's email address
        otp: One-time password
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Render HTML email with orb_glow_sphere
        html_content = email_template_service.render_email(
            subject="Email Verification Code",
            title="Verify Your Email Address",
            message=f"Your verification code is: <strong style='font-size: 24px; color: #8b5cf6;'>{otp}</strong><br><br>This code will expire in 10 minutes.",
            security_info="Never share this code with anyone. If you didn't request this, please ignore this email.",
            status="default"
        )
        
        # Send email
        return await _send_email(
            to_email=email,
            subject="Email Verification Code",
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False


async def send_password_change_notification(email: str, ip_address: Optional[str] = None) -> bool:
    """
    Send password change notification email to user using HTML template with orb_glow_sphere.
    
    Args:
        email: User's email address
        ip_address: IP address from which password was changed
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        location_info = f" from IP {ip_address}" if ip_address else ""
        
        # Render HTML email with orb_glow_sphere
        html_content = email_template_service.render_email(
            subject=EmailTypes.PASSWORD_CHANGED['subject'],
            title=EmailTypes.PASSWORD_CHANGED['title'],
            message=f"Your PhishCatcher account password has been successfully changed{location_info}.",
            security_info=EmailTypes.PASSWORD_CHANGED['security_info'],
            status=EmailTypes.PASSWORD_CHANGED['status']
        )
        
        # Send email
        return await _send_email(
            to_email=email,
            subject=EmailTypes.PASSWORD_CHANGED['subject'],
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Failed to send password change notification email to {email}: {e}")
        return False


async def send_welcome_email(email: str, user_name: Optional[str] = None) -> bool:
    """
    Send welcome email to new user using HTML template with orb_glow_sphere.
    
    Args:
        email: User's email address
        user_name: User's name (optional)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        settings = get_settings()
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
        
        # Render HTML email with orb_glow_sphere
        html_content = email_template_service.render_email(
            subject=EmailTypes.WELCOME['subject'],
            title=EmailTypes.WELCOME['title'],
            message=f"Welcome to PhishCatcher{f', {user_name}!' if user_name else '!'} Your account has been created successfully and you can now start analyzing emails for phishing threats.",
            action_url=dashboard_url,
            action_text="Go to Dashboard",
            security_info=EmailTypes.WELCOME['security_info'],
            status=EmailTypes.WELCOME['status']
        )
        
        # Send email
        return await _send_email(
            to_email=email,
            subject=EmailTypes.WELCOME['subject'],
            html_content=html_content
        )
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        return False


async def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Send email using SMTP configuration.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        settings = get_settings()
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.FROM_EMAIL
        msg['To'] = to_email
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email using SendGrid SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
