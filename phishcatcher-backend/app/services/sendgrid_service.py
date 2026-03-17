"""
SendGrid Email Service for Security Verification

This service handles sending emails through SendGrid API for:
- Email verification codes
- Security notifications
- Password change notifications
- Account deletion confirmations
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import httpx
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from jinja2 import Template
from app.config import get_settings

logger = logging.getLogger(__name__)

class SendGridService:
    """Enterprise-grade email service using SendGrid."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Use SendGrid API key if available, otherwise fall back to SMTP
        api_key = getattr(self.settings, 'SENDGRID_API_KEY', None) or getattr(self.settings, 'SMTP_PASSWORD', None)
        if api_key and api_key.startswith('SG.'):
            self.client = SendGridAPIClient(api_key=api_key)
        else:
            self.client = None
            logger.warning("SendGrid API key not configured or invalid format")
        
        # Use SendGrid from email if available, otherwise fall back to FROM_EMAIL
        self.from_email = getattr(self.settings, 'SENDGRID_FROM_EMAIL', None) or getattr(self.settings, 'FROM_EMAIL', 'noreply@phishcatcher.io')
        self.from_name = getattr(self.settings, 'SENDGRID_FROM_NAME', 'PhishCatcher')
        
        # Email templates
        self.templates = {
            'email_verification': {
                'subject': 'PhishCatcher - Verification Code',
                'template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhishCatcher - Email Verification</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #7c3aed 0%, #6a11cb 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
        .content { padding: 30px; }
        .code-box { background-color: #f3f4f6; border: 2px dashed #d1d5db; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }
        .code { font-size: 32px; font-weight: bold; color: #1a73e8; letter-spacing: 4px; font-family: 'Courier New', monospace; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6b7280; font-size: 14px; }
        .security-info { background-color: #e3f2fd; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .button { display: inline-block; background-color: #7c3aed; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .button:hover { background-color: #6a11cb; }
        .expiry { color: #dc3545; font-size: 14px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔒 PhishCatcher</div>
            <h1>Email Verification</h1>
        </div>
        
        <div class="content">
            <p>Hello,</p>
            
            <p>You requested to perform a sensitive action on your PhishCatcher account. To proceed, please use the verification code below:</p>
            
            <div class="security-info">
                <strong>🔐 Security Information:</strong>
                <ul>
                    <li>This code expires in <strong>10 minutes</strong></li>
                    <li>Never share this code with anyone</li>
                    <li>PhishCatcher will never ask for your password via email</li>
                </ul>
            </div>
            
            <div class="code-box">
                <div class="code">{{ code }}</div>
                <div class="expiry">⏰ Expires: {{ expiry_time }}</div>
            </div>
            
            <p>If you didn't request this verification, please secure your account immediately and contact support.</p>
        </div>
        
        <div class="footer">
            <p>This is an automated message from PhishCatcher Security Team.</p>
            <p>© 2024 PhishCatcher. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                '''
            },
            'security_alert': {
                'subject': 'PhishCatcher - Security Alert',
                'template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhishCatcher - Security Alert</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
        .alert { font-size: 48px; margin-bottom: 10px; }
        .content { padding: 30px; }
        .details { background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 20px; margin: 20px 0; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6b7280; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="alert">🚨</div>
            <h1>Security Alert</h1>
        </div>
        
        <div class="content">
            <p>A sensitive action was performed on your PhishCatcher account:</p>
            
            <div class="details">
                <h3>📋 Action Details:</h3>
                <ul>
                    <li><strong>Action:</strong> {{ action }}</li>
                    <li><strong>Time:</strong> {{ timestamp }}</li>
                    <li><strong>IP Address:</strong> {{ ip_address }}</li>
                    <li><strong>Device:</strong> {{ user_agent }}</li>
                </ul>
            </div>
            
            <p><strong>If this was you:</strong></p>
            <ul>
                <li>No action is needed - your account is secure</li>
                <li>Review your account settings if concerned</li>
                <li>Contact support immediately if you suspect unauthorized access</li>
            </ul>
            
            <p><strong>If this was NOT you:</strong></p>
            <ul>
                <li>Change your password immediately</li>
                <li>Enable two-factor authentication</li>
                <li>Review your account activity</li>
                <li>Contact support at support@phishcatcher.com</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>This is an automated security message from PhishCatcher Security Team.</p>
            <p>© 2024 PhishCatcher. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                '''
            }
        }
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        template_data = self.templates.get(template_name, {})
        template_str = template_data.get('template', '')
        
        # Simple string replacement for now to avoid Jinja2 complexity
        for key, value in context.items():
            template_str = template_str.replace(f'{{ {key} }}', str(value))
        
        return template_str
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SendGrid."""
        if not self.client:
            logger.error("SendGrid client not initialized")
            return False
            
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            
            if response.status_code == 202:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}: {response.status_code} {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def send_verification_code(self, to_email: str, code: str, action: str = "security_action") -> bool:
        """Send email verification code."""
        expiry_time = (datetime.utcnow() + timedelta(minutes=10)).strftime('%I:%M %p, %B %Y')
        
        context = {
            'code': code,
            'expiry_time': expiry_time,
            'action': action.replace('_', ' ').title()
        }
        
        html_content = self._render_template('email_verification', context)
        subject = f"PhishCatcher - Verification Code for {action.replace('_', ' ').title()}"
        
        return self.send_email(to_email, subject, html_content)
    
    def send_security_alert(self, to_email: str, action: str, ip_address: str = None, user_agent: str = None) -> bool:
        """Send security alert email."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        context = {
            'action': action.replace('_', ' ').title(),
            'timestamp': timestamp,
            'ip_address': ip_address or 'Unknown',
            'user_agent': user_agent or 'Unknown'
        }
        
        html_content = self._render_template('security_alert', context)
        subject = f"PhishCatcher - Security Alert: {action.replace('_', ' ').title()}"
        
        return self.send_email(to_email, subject, html_content)
    
    def send_password_change_notification(self, to_email: str) -> bool:
        """Send password change notification."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        context = {
            'action': 'Password Changed',
            'timestamp': timestamp,
            'ip_address': 'Current Session',
            'user_agent': 'Web Application'
        }
        
        html_content = self._render_template('security_alert', context)
        subject = "PhishCatcher - Password Changed"
        
        return self.send_email(to_email, subject, html_content)
    
    def send_account_deletion_notification(self, to_email: str) -> bool:
        """Send account deletion notification."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        context = {
            'action': 'Account Deleted',
            'timestamp': timestamp,
            'ip_address': 'Final Action',
            'user_agent': 'Web Application'
        }
        
        html_content = self._render_template('security_alert', context)
        subject = "PhishCatcher - Account Deletion Confirmation"
        
        return self.send_email(to_email, subject, html_content)

# Global instance
sendgrid_service = SendGridService()
