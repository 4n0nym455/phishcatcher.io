"""
Account Activation Service

Handles activation flow for new OAuth users:
- Generate activation tokens
- Send activation emails with OTP
- Verify activation codes
- Handle terms acceptance
- Activate user accounts
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

from app.services.email_service import email_service
from app.services.security_service import security_service

logger = logging.getLogger(__name__)

class ActivationService:
    """Service for handling account activation flow."""
    
    def __init__(self):
        self.activation_tokens = {}  # In production, use Redis
        self.activation_codes = {}   # In production, use Redis
    
    def generate_activation_token(self, user_id: str) -> str:
        """Generate secure activation token."""
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
        
        self.activation_tokens[user_id] = {
            "token": token,
            "expiry": expiry,
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"Generated activation token for user {user_id}")
        return token
    
    def generate_activation_code(self, user_id: str) -> str:
        """Generate 6-digit activation code."""
        code = f"{secrets.randbelow(1000000):06d}"
        expiry = datetime.utcnow() + timedelta(minutes=10)  # 10 minute expiry
        
        self.activation_codes[user_id] = {
            "code": code,
            "expiry": expiry,
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"Generated activation code for user {user_id}")
        return code
    
    async def send_activation_email(self, user_email: str, user_name: str, user_id: str, activation_token: str, activation_code: str) -> bool:
        """Send activation email with OTP and activation link."""
        try:
            # Create activation URL
            activation_url = f"http://localhost:5173/activate?token={activation_token}&email={user_email}"
            
            # Send activation email
            success = await email_service.send_custom_email(
                to_email=user_email,
                subject="Activate Your PhishCatcher Account",
                html_content=self._get_activation_email_html(user_name, activation_code, activation_url)
            )
            
            if success:
                logger.info(f"Activation email sent to {user_email}")
                return True
            else:
                logger.error(f"Failed to send activation email to {user_email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending activation email: {e}")
            return False
    
    def _get_activation_email_html(self, user_name: str, activation_code: str, activation_url: str) -> str:
        """Generate activation email HTML."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Activate Your PhishCatcher Account</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 28px;
            font-weight: bold;
            color: #7b61ff;
            margin-bottom: 10px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 20px;
        }}
        .code {{
            background: #f3f4f6;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .code-number {{
            font-size: 32px;
            font-weight: bold;
            color: #7b61ff;
            letter-spacing: 4px;
            font-family: monospace;
        }}
        .button {{
            display: inline-block;
            background: #7b61ff;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            margin: 20px 0;
            text-align: center;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
            text-align: center;
        }}
        .security {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🎯 PhishCatcher</div>
            <h1 class="title">Activate Your Account</h1>
        </div>
        
        <p>Hi {user_name},</p>
        
        <p>Welcome to PhishCatcher! We're excited to have you on board. To complete your registration and activate your account, please follow the steps below:</p>
        
        <div class="security">
            <strong>🔒 Security Notice:</strong> This activation code will expire in <strong>10 minutes</strong> for your security.
        </div>
        
        <h3>Step 1: Copy Your Activation Code</h3>
        <div class="code">
            <div class="code-number">{activation_code}</div>
        </div>
        
        <h3>Step 2: Click the Activation Link</h3>
        <p>Click the button below to go to the activation page:</p>
        
        <div style="text-align: center;">
            <a href="{activation_url}" class="button">Activate Account</a>
        </div>
        
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; background: #f3f4f6; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px;">
            {activation_url}
        </p>
        
        <h3>Step 3: Enter Code & Accept Terms</h3>
        <p>On the activation page:</p>
        <ul>
            <li>Enter the 6-digit code shown above</li>
            <li>Read and accept our Terms & Conditions</li>
            <li>Read and accept our Privacy Policy</li>
            <li>Click "Activate Account"</li>
        </ul>
        
        <div class="footer">
            <p><strong>Need Help?</strong></p>
            <p>If you didn't request this activation, please ignore this email. If you have any questions, contact our support team.</p>
            <p>© 2026 PhishCatcher. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """
    
    def verify_activation_code(self, user_id: str, code: str) -> bool:
        """Verify activation code."""
        if user_id not in self.activation_codes:
            logger.warning(f"No activation code found for user {user_id}")
            return False
        
        stored_code_data = self.activation_codes[user_id]
        
        # Check expiry
        if datetime.utcnow() > stored_code_data["expiry"]:
            logger.warning(f"Activation code expired for user {user_id}")
            del self.activation_codes[user_id]
            return False
        
        # Check code match
        if stored_code_data["code"] != code:
            logger.warning(f"Invalid activation code for user {user_id}")
            return False
        
        logger.info(f"Activation code verified for user {user_id}")
        return True
    
    def verify_activation_token(self, user_id: str, token: str) -> bool:
        """Verify activation token."""
        if user_id not in self.activation_tokens:
            logger.warning(f"No activation token found for user {user_id}")
            return False
        
        stored_token_data = self.activation_tokens[user_id]
        
        # Check expiry
        if datetime.utcnow() > stored_token_data["expiry"]:
            logger.warning(f"Activation token expired for user {user_id}")
            del self.activation_tokens[user_id]
            return False
        
        # Check token match
        if stored_token_data["token"] != token:
            logger.warning(f"Invalid activation token for user {user_id}")
            return False
        
        logger.info(f"Activation token verified for user {user_id}")
        return True
    
    def cleanup_expired_codes(self):
        """Clean up expired activation codes and tokens."""
        current_time = datetime.utcnow()
        expired_users = []
        
        # Clean up expired codes
        for user_id, code_data in self.activation_codes.items():
            if current_time > code_data["expiry"]:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.activation_codes[user_id]
        
        # Clean up expired tokens
        expired_users = []
        for user_id, token_data in self.activation_tokens.items():
            if current_time > token_data["expiry"]:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.activation_tokens[user_id]
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired activation records")

# Global instance
activation_service = ActivationService()
