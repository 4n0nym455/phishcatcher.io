"""
Email Template Service for PhishCatcher

This service handles rendering HTML email templates with the orb_glow_sphere effect
for various email types sent to users.
"""

from typing import Dict, Any, Optional
from jinja2 import Template, Environment, FileSystemLoader
import os
from pathlib import Path

class EmailTemplateService:
    """Service for rendering email templates with orb_glow_sphere effect."""
    
    def __init__(self):
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
    def render_email(self, 
                   template_name: str = "email_template.html",
                   subject: str = "",
                   title: str = "",
                   message: str = "",
                   action_url: Optional[str] = None,
                   action_text: str = "Click Here",
                   security_info: Optional[str] = None,
                   status: str = "default",
                   **kwargs) -> str:
        """
        Render email template with given parameters.
        
        Args:
            template_name: Name of the template file
            subject: Email subject
            title: Email title
            message: Main email message
            action_url: URL for action button
            action_text: Text for action button
            security_info: Security information to display
            status: Email status (default, success, warning, error)
            **kwargs: Additional template variables
            
        Returns:
            Rendered HTML email content
        """
        try:
            # Load template
            template = self.env.get_template(template_name)
            
            # Prepare template context
            context = {
                'subject': subject,
                'title': title,
                'message': message,
                'action_url': action_url,
                'action_text': action_text,
                'security_info': security_info,
                'status': status,
                **kwargs
            }
            
            # Render template
            return template.render(**context)
            
        except Exception as e:
            print(f"Error rendering email template: {e}")
            # Fallback to simple HTML
            return self._fallback_email(subject, title, message, action_url, action_text)
    
    def _fallback_email(self, subject: str, title: str, message: str, 
                      action_url: Optional[str], action_text: str) -> str:
        """Fallback email if template rendering fails."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px;">
                <h1 style="color: #333; margin-bottom: 20px;">{title}</h1>
                <p style="color: #666; line-height: 1.6; margin-bottom: 20px;">{message}</p>
                {f'<a href="{action_url}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">{action_text}</a>' if action_url else ''}
            </div>
        </body>
        </html>
        """

# Email template types
class EmailTypes:
    """Predefined email types with their configurations."""
    
    PASSWORD_RESET = {
        'subject': 'Password Reset Request',
        'title': 'Reset Your Password',
        'status': 'warning',
        'security_info': 'This link will expire in 1 hour for security reasons. If you didn\'t request this reset, please ignore this email.'
    }
    
    PASSWORD_CHANGED = {
        'subject': 'Password Successfully Changed',
        'title': 'Your Password Has Been Changed',
        'status': 'success',
        'security_info': 'If you didn\'t change your password, please contact support immediately.'
    }
    
    EMAIL_VERIFICATION = {
        'subject': 'Verify Your Email Address',
        'title': 'Complete Your Registration',
        'status': 'default',
        'security_info': 'Please verify your email to activate your account. This link expires in 24 hours.'
    }
    
    PHISHING_ALERT = {
        'subject': 'Phishing Alert - Suspicious Email Detected',
        'title': '⚠️ Potential Phishing Email Detected',
        'status': 'error',
        'security_info': 'We detected characteristics commonly found in phishing emails. Please review carefully and do not click suspicious links.'
    }
    
    WELCOME = {
        'subject': 'Welcome to PhishCatcher',
        'title': '🎉 Welcome to PhishCatcher',
        'status': 'success',
        'security_info': 'Your account has been created successfully. You can now start analyzing emails for phishing threats.'
    }
    
    ANALYSIS_COMPLETE = {
        'subject': 'Email Analysis Complete',
        'title': '📊 Analysis Results Ready',
        'status': 'success',
        'security_info': 'Your email has been analyzed. No threats were detected in this message.'
    }

# Global instance
email_template_service = EmailTemplateService()
