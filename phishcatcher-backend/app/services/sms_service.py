"""
Brevo SMS Service for PhishCatcher

Sends transactional SMS messages via Brevo's Transactional SMS API.
Used for OTP delivery, security alerts, and phone verification.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class SmsService:
    """Transactional SMS service using Brevo."""

    API_URL = "https://api.brevo.com/v3/transactionalSMS/send"

    def __init__(self):
        self.settings = get_settings()

        api_key = (
            getattr(self.settings, 'BREVO_SMS_API_KEY', None)
            or getattr(self.settings, 'BREVO_API_KEY', None)
        )
        if api_key and (api_key.startswith('xkeysib-') or api_key.startswith('xsmtpsib-')):
            self.api_key = api_key
        else:
            self.api_key = None
            logger.warning("Brevo SMS API key not configured")

        sender = getattr(self.settings, 'BREVO_SMS_SENDER', 'PhishCatcher')
        self.sender = sender[:11]  # Brevo limits to 11 chars

    async def send_sms(self, to_phone: str, content: str, sender: str = None, tag: str = None) -> bool:
        """Send raw SMS message."""
        if not self.api_key:
            logger.error("SMS API key not initialized")
            return False

        try:
            payload = {
                "sender": sender or self.sender,
                "recipient": to_phone,
                "content": content,
                "type": "transactional",
            }
            if tag:
                payload["tag"] = tag

            async with httpx.AsyncClient(timeout=15.0) as client:
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
                logger.info(f"SMS sent successfully to {to_phone}")
                return True
            else:
                logger.error(f"Failed to send SMS to {to_phone}: HTTP {response.status_code} {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending SMS to {to_phone}: {e}")
            return False

    async def send_otp(self, to_phone: str, code: str) -> bool:
        """Send OTP verification code via SMS."""
        content = f"Your PhishCatcher verification code is: {code}"
        return await self.send_sms(to_phone, content, tag="otp_verification")

    async def send_password_reset_sms(self, to_phone: str, code: str) -> bool:
        """Send password reset code via SMS."""
        content = f"Your PhishCatcher password reset code is: {code}"
        return await self.send_sms(to_phone, content, tag="password_reset")

    async def send_security_alert_sms(self, to_phone: str, action: str, details: str = None) -> bool:
        """Send security alert via SMS."""
        content = f"ALERT: {action} on your PhishCatcher account."
        if details:
            content += f" {details}"
        content += " If this wasn't you, contact support immediately."
        return await self.send_sms(to_phone, content, tag="security_alert")


sms_service = SmsService()
