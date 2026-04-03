"""
SMS notification service using Twilio.

Handles SMS notifications:
- OTP codes for 2FA
- Transaction alerts
- Security notifications
"""

import logging
from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.core.config import settings


logger = logging.getLogger(__name__)


class SMSService:
    """SMS service using Twilio API."""
    
    def __init__(self) -> None:
        self.enabled = bool(
            settings.twilio_account_sid and 
            settings.twilio_auth_token and 
            settings.twilio_phone_number
        )
        self.client: Optional[Client] = None
        
        if self.enabled:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        else:
            logger.warning("SMS service disabled: Twilio credentials not configured")
    
    def send(self, to: str, message: str) -> Optional[str]:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number (E.164 format, e.g., +1234567890)
            message: Message content
            
        Returns:
            Message SID if successful, None otherwise
        """
        if not self.enabled or not self.client:
            logger.info(f"SMS (disabled): to={to}, message={message[:50]}...")
            return None
        
        # Ensure phone number is in E.164 format
        if not to.startswith("+"):
            to = f"+{to}"
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=to,
            )
            logger.info(f"SMS sent: to={to}, sid={msg.sid}")
            return msg.sid
        except TwilioRestException as e:
            logger.error(f"SMS failed: to={to}, error={str(e)}")
            return None
        except Exception as e:
            logger.error(f"SMS unexpected error: to={to}, error={str(e)}")
            return None
    
    def send_otp(self, to: str, otp_code: str) -> Optional[str]:
        """Send OTP code via SMS."""
        message = f"Your OpenCredit verification code is: {otp_code}\n\nThis code expires in {settings.otp_expiry_seconds // 60} minutes. Never share this code."
        return self.send(to, message)
    
    def send_payment_alert(
        self,
        to: str,
        amount: float,
        currency: str,
        status: str,
        merchant_name: str,
    ) -> Optional[str]:
        """Send payment alert via SMS."""
        status_emoji = {
            "approved": "✅",
            "flagged": "⚠️",
            "rejected": "❌",
        }.get(status, "📋")
        
        message = f"{status_emoji} OpenCredit Payment\n${amount:,.2f} {currency} - {status.upper()}\nMerchant: {merchant_name}\n\nNot you? Contact support immediately."
        return self.send(to, message)
    
    def send_security_alert(self, to: str, event: str) -> Optional[str]:
        """Send security alert via SMS."""
        message = f"🔐 OpenCredit Security Alert\n\n{event}\n\nIf this wasn't you, secure your account immediately."
        return self.send(to, message)
    
    def send_kyc_update(self, to: str, status: str) -> Optional[str]:
        """Send KYC status update via SMS."""
        status_messages = {
            "pending": "📄 Your KYC documents are being reviewed.",
            "approved": "✅ Your KYC verification is approved!",
            "rejected": "❌ Your KYC verification needs attention. Check email for details.",
        }
        message = f"OpenCredit: {status_messages.get(status, 'Your KYC status has been updated.')}"
        return self.send(to, message)
    
    def send_dispute_update(self, to: str, dispute_id: int, status: str) -> Optional[str]:
        """Send dispute status update via SMS."""
        message = f"OpenCredit: Dispute #{dispute_id} status updated to {status.replace('_', ' ').upper()}. Check email for details."
        return self.send(to, message)


# Singleton instance
sms_service = SMSService()
