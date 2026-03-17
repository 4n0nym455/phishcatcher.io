"""
Comprehensive Email Service for PhishCatcher

This service handles all email communications including:
- OTP/Verification codes
- User onboarding
- Password reset
- Account notifications
- Security alerts
- Marketing communications
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.services.sendgrid_service import sendgrid_service

logger = logging.getLogger(__name__)

class EmailService:
    """Comprehensive email service for all user communications."""
    
    def __init__(self):
        self.sendgrid = sendgrid_service
        
        # Email templates for different purposes
        self.templates = {
            'otp_verification': {
                'subject': 'PhishCatcher - Your Verification Code',
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
        .expiry { color: #dc3545; font-size: 14px; margin-top: 10px; }
        .security-info { background-color: #e3f2fd; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6b7280; font-size: 14px; }
        .button { display: inline-block; background-color: #7c3aed; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .button:hover { background-color: #6a11cb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔒 PhishCatcher</div>
            <h1>Email Verification</h1>
        </div>
        
        <div class="content">
            <p>Hello {{ user_name }},</p>
            
            <p>You requested to {{ action }}. To proceed, please use the verification code below:</p>
            
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
            'welcome_onboarding': {
                'subject': 'Welcome to PhishCatcher! 🎉',
                'template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to PhishCatcher</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
        .content { padding: 30px; }
        .welcome-box { background-color: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .feature-list { background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .feature-item { margin-bottom: 15px; display: flex; align-items: center; }
        .feature-icon { font-size: 24px; margin-right: 15px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6b7280; font-size: 14px; }
        .button { display: inline-block; background-color: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; margin: 10px 5px; }
        .button:hover { background-color: #059669; }
        .button-secondary { background-color: #6b7280; }
        .button-secondary:hover { background-color: #4b5563; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🎉 PhishCatcher</div>
            <h1>Welcome to PhishCatcher!</h1>
        </div>
        
        <div class="content">
            <p>Hi {{ user_name }},</p>
            
            <div class="welcome-box">
                <h2>🚀 Your account is ready!</h2>
                <p>Welcome to PhishCatcher - your intelligent email phishing detection and protection system. We're excited to have you on board!</p>
            </div>
            
            <div class="feature-list">
                <h3>🛡️ What you can do with PhishCatcher:</h3>
                
                <div class="feature-item">
                    <div class="feature-icon">🔍</div>
                    <div>
                        <strong>Scan Emails</strong>
                        <p>Analyze emails for phishing attempts with our advanced ML algorithms</p>
                    </div>
                </div>
                
                <div class="feature-item">
                    <div class="feature-icon">📊</div>
                    <div>
                        <strong>View Analytics</strong>
                        <p>Track your email security metrics and phishing detection history</p>
                    </div>
                </div>
                
                <div class="feature-item">
                    <div class="feature-icon">🔐</div>
                    <div>
                        <strong>Multi-Factor Security</strong>
                        <p>Protect your account with MFA and OAuth integration</p>
                    </div>
                </div>
                
                <div class="feature-item">
                    <div class="feature-icon">🌐</div>
                    <div>
                        <strong>Gmail Integration</strong>
                        <p>Connect your Gmail account for seamless email scanning</p>
                    </div>
                </div>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ dashboard_url }}" class="button">Go to Dashboard</a>
                <a href="{{ help_url }}" class="button button-secondary">Get Help</a>
            </div>
            
            <p><strong>Next Steps:</strong></p>
            <ol>
                <li>Complete your profile setup</li>
                <li>Connect your email accounts</li>
                <li>Configure security settings</li>
                <li>Start scanning for phishing attempts</li>
            </ol>
        </div>
        
        <div class="footer">
            <p>Need help? Contact us at support@phishcatcher.io</p>
            <p>© 2024 PhishCatcher. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                '''
            },
            'password_reset': {
                'subject': 'PhishCatcher - Reset Your Password',
                'template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhishCatcher - Password Reset</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
        .content { padding: 30px; }
        .reset-box { background-color: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .reset-link { background-color: #ef4444; color: white; padding: 15px 25px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; margin: 20px 0; }
        .reset-link:hover { background-color: #dc2626; }
        .security-info { background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6b7280; font-size: 14px; }
        .code { font-family: 'Courier New', monospace; background-color: #f3f4f6; padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🔑 PhishCatcher</div>
            <h1>Password Reset Request</h1>
        </div>
        
        <div class="content">
            <p>Hi {{ user_name }},</p>
            
            <p>We received a request to reset your PhishCatcher password. If you made this request, you can reset your password using the link below:</p>
            
            <div class="reset-box">
                <h3>🔐 Password Reset Information</h3>
                <p><strong>Reset Code:</strong> <span class="code">{{ reset_code }}</span></p>
                <p><strong>Expires in:</strong> {{ expiry_time }}</p>
                <p><strong>Requested from:</strong> {{ ip_address }}</p>
            </div>
            
            <div style="text-align: center;">
                <a href="{{ reset_url }}" class="reset-link">Reset Your Password</a>
            </div>
            
            <div class="security-info">
                <strong>🔒 Security Notice:</strong>
                <ul>
                    <li>This reset link expires in <strong>1 hour</strong></li>
                    <li>Never share this link with anyone</li>
                    <li>If you didn't request this reset, please contact support immediately</li>
                    <li>Make sure to create a strong, unique password</li>
                </ul>
            </div>
            
            <p><strong>Alternative Method:</strong></p>
            <p>If the button above doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background-color: #f3f4f6; padding: 10px; border-radius: 4px; font-family: monospace;">{{ reset_url }}</p>
        </div>
        
        <div class="footer">
            <p>Need help? Contact us at support@phishcatcher.io</p>
            <p>© 2024 PhishCatcher. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                '''
            },
            'account_suspended': {
                'subject': 'PhishCatcher - Account Action Required',
                'template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhishCatcher - Account Suspended</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }
        .logo { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
        .content { padding: 30px; }
        .alert-box { background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .action-box { background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; color: #6b7280; font-size: 14px; }
        .button { display: inline-block; background-color: #f59e0b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .button:hover { background-color: #d97706; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">⚠️ PhishCatcher</div>
            <h1>Account Action Required</h1>
        </div>
        
        <div class="content">
            <p>Hi {{ user_name }},</p>
            
            <div class="alert-box">
                <h3>🚨 Account Status: {{ status }}</h3>
                <p>{{ reason }}</p>
                <p><strong>Date:</strong> {{ date }}</p>
            </div>
            
            <div class="action-box">
                <h3>📋 Required Actions:</h3>
                <ul>
                    {{ actions_list }}
                </ul>
            </div>
            
            <div style="text-align: center;">
                <a href="{{ action_url }}" class="button">Review Account</a>
            </div>
            
            <p><strong>Need Help?</strong></p>
            <p>If you believe this is an error or need assistance, please contact our support team:</p>
            <ul>
                <li>Email: support@phishcatcher.io</li>
                <li>Help Center: {{ help_url }}</li>
                <li>Response Time: Within 24 hours</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>This is an automated security message from PhishCatcher.</p>
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
        
        # Simple string replacement for template variables
        for key, value in context.items():
            template_str = template_str.replace(f'{{ {key} }}', str(value))
        
        return template_str
    
    async def send_otp_verification(self, to_email: str, user_name: str, code: str, action: str = "verify your account") -> bool:
        """Send OTP verification email."""
        expiry_time = (datetime.utcnow() + timedelta(minutes=10)).strftime('%I:%M %p, %B %d, %Y')
        
        context = {
            'user_name': user_name,
            'code': code,
            'action': action,
            'expiry_time': expiry_time
        }
        
        subject = f"PhishCatcher - Your Verification Code"
        html_content = self._render_template('otp_verification', context)
        
        return self.sendgrid.send_email(to_email, subject, html_content)
    
    async def send_welcome_email(self, to_email: str, user_name: str, dashboard_url: str = None) -> bool:
        """Send welcome/onboarding email."""
        context = {
            'user_name': user_name,
            'dashboard_url': dashboard_url or 'http://localhost:5173/dashboard',
            'help_url': 'http://localhost:5173/help'
        }
        
        subject = "Welcome to PhishCatcher! 🎉"
        html_content = self._render_template('welcome_onboarding', context)
        
        return self.sendgrid.send_email(to_email, subject, html_content)
    
    async def send_password_reset(self, to_email: str, user_name: str, reset_code: str, reset_url: str, ip_address: str = None) -> bool:
        """Send password reset email."""
        expiry_time = (datetime.utcnow() + timedelta(hours=1)).strftime('%I:%M %p, %B %d, %Y')
        
        context = {
            'user_name': user_name,
            'reset_code': reset_code,
            'reset_url': reset_url,
            'ip_address': ip_address or 'Unknown',
            'expiry_time': expiry_time
        }
        
        subject = "PhishCatcher - Reset Your Password"
        html_content = self._render_template('password_reset', context)
        
        return self.sendgrid.send_email(to_email, subject, html_content)
    
    async def send_account_suspended(self, to_email: str, user_name: str, status: str, reason: str, actions: list, action_url: str = None) -> bool:
        """Send account suspension/notification email."""
        actions_list = '\n'.join([f'<li>{action}</li>' for action in actions])
        
        context = {
            'user_name': user_name,
            'status': status,
            'reason': reason,
            'date': datetime.utcnow().strftime('%B %d, %Y'),
            'actions_list': actions_list,
            'action_url': action_url or 'http://localhost:5173/account',
            'help_url': 'http://localhost:5173/help'
        }
        
        subject = "PhishCatcher - Account Action Required"
        html_content = self._render_template('account_suspended', context)
        
        return self.sendgrid.send_email(to_email, subject, html_content)
    
    async def send_security_alert(self, to_email: str, user_name: str, action: str, ip_address: str = None, user_agent: str = None) -> bool:
        """Send security alert email."""
        return self.sendgrid.send_security_alert(to_email, action, ip_address, user_agent)
    
    async def send_custom_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send custom email content."""
        return self.sendgrid.send_email(to_email, subject, html_content)

# Global instance
email_service = EmailService()
