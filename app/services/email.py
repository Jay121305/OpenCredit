"""
Email notification service using Resend.

Handles all transactional emails:
- Welcome emails
- Payment receipts
- OTP codes
- KYC status updates
- Dispute notifications
"""

import logging
from typing import Optional

import resend

from app.core.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    """Email service using Resend API."""
    
    def __init__(self) -> None:
        self.enabled = bool(settings.resend_api_key)
        if self.enabled:
            resend.api_key = settings.resend_api_key
        else:
            logger.warning("Email service disabled: RESEND_API_KEY not configured")
    
    def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML body content
            text: Plain text body (optional)
            
        Returns:
            Email ID if successful, None otherwise
        """
        if not self.enabled:
            logger.info(f"Email (disabled): to={to}, subject={subject}")
            return None
        
        try:
            params = {
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            if text:
                params["text"] = text
            
            response = resend.Emails.send(params)
            logger.info(f"Email sent: to={to}, subject={subject}, id={response.get('id')}")
            return response.get("id")
        except Exception as e:
            logger.error(f"Email failed: to={to}, error={str(e)}")
            return None
    
    def send_welcome(self, to: str, name: str) -> Optional[str]:
        """Send welcome email after registration."""
        subject = "Welcome to OpenCredit! 🎉"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4f7cff, #00d4ff); padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
                .button {{ display: inline-block; background: #4f7cff; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to OpenCredit!</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p>Thank you for joining OpenCredit! Your account has been created successfully.</p>
                    <p>Here's what you can do:</p>
                    <ul>
                        <li>💳 Make secure payments with your credit line</li>
                        <li>📊 Track your spending with real-time analytics</li>
                        <li>🔒 Enable two-factor authentication for extra security</li>
                        <li>📄 Complete KYC verification to unlock higher limits</li>
                    </ul>
                    <p>Your starting credit limit is <strong>${settings.default_credit_limit:,.2f}</strong>.</p>
                    <a href="#" class="button">Get Started</a>
                </div>
                <div class="footer">
                    <p>OpenCredit - Digital Credit Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(to, subject, html)
    
    def send_payment_receipt(
        self,
        to: str,
        name: str,
        amount: float,
        currency: str,
        transaction_id: int,
        status: str,
        merchant_name: str,
        available_credit: float,
    ) -> Optional[str]:
        """Send payment receipt email."""
        status_color = {
            "approved": "#00e68a",
            "flagged": "#ffb444",
            "rejected": "#ff4d6a",
        }.get(status, "#666")
        
        subject = f"Payment {status.title()}: ${amount:,.2f} {currency}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4f7cff, #00d4ff); padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
                .amount {{ font-size: 32px; font-weight: bold; color: #333; }}
                .status {{ display: inline-block; padding: 6px 16px; border-radius: 20px; color: white; font-weight: 600; background: {status_color}; }}
                .details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Receipt</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p class="amount">${amount:,.2f} {currency}</p>
                    <p><span class="status">{status.upper()}</span></p>
                    
                    <div class="details">
                        <div class="detail-row">
                            <span>Transaction ID</span>
                            <strong>#{transaction_id}</strong>
                        </div>
                        <div class="detail-row">
                            <span>Merchant</span>
                            <strong>{merchant_name}</strong>
                        </div>
                        <div class="detail-row">
                            <span>Status</span>
                            <strong>{status.title()}</strong>
                        </div>
                        <div class="detail-row">
                            <span>Available Credit</span>
                            <strong>${available_credit:,.2f}</strong>
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        If you didn't make this transaction, please contact support immediately.
                    </p>
                </div>
                <div class="footer">
                    <p>OpenCredit - Digital Credit Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(to, subject, html)
    
    def send_otp(self, to: str, name: str, otp_code: str) -> Optional[str]:
        """Send OTP code via email."""
        subject = f"Your OpenCredit verification code: {otp_code}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4f7cff, #00d4ff); padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; text-align: center; }}
                .otp-code {{ font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #4f7cff; background: white; padding: 20px 40px; border-radius: 12px; display: inline-block; margin: 20px 0; }}
                .warning {{ color: #ff4d6a; font-size: 14px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Verification Code</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p>Your verification code is:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code expires in {settings.otp_expiry_seconds // 60} minutes.</p>
                    <p class="warning">⚠️ Never share this code with anyone. OpenCredit will never ask for your code.</p>
                </div>
                <div class="footer">
                    <p>OpenCredit - Digital Credit Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(to, subject, html)
    
    def send_kyc_status(self, to: str, name: str, status: str, reason: Optional[str] = None) -> Optional[str]:
        """Send KYC status update email."""
        status_messages = {
            "pending": ("KYC Verification Submitted", "Your documents are being reviewed. This usually takes 1-2 business days."),
            "approved": ("KYC Verification Approved! ✅", "Your identity has been verified. You now have access to higher transaction limits."),
            "rejected": ("KYC Verification Needs Attention", f"We couldn't verify your documents. Reason: {reason or 'Please resubmit clearer documents.'}"),
        }
        
        title, message = status_messages.get(status, ("KYC Update", "Your KYC status has been updated."))
        subject = f"OpenCredit: {title}"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4f7cff, #00d4ff); padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{title}</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p>{message}</p>
                </div>
                <div class="footer">
                    <p>OpenCredit - Digital Credit Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(to, subject, html)
    
    def send_dispute_update(
        self,
        to: str,
        name: str,
        dispute_id: int,
        status: str,
        resolution: Optional[str] = None,
    ) -> Optional[str]:
        """Send dispute status update email."""
        subject = f"Dispute #{dispute_id} Update: {status.replace('_', ' ').title()}"
        
        resolution_text = f"<p><strong>Resolution:</strong> {resolution}</p>" if resolution else ""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4f7cff, #00d4ff); padding: 30px; border-radius: 12px 12px 0 0; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 12px 12px; }}
                .status {{ font-size: 20px; font-weight: bold; color: #4f7cff; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Dispute Update</h1>
                </div>
                <div class="content">
                    <p>Hi {name},</p>
                    <p>Your dispute <strong>#{dispute_id}</strong> has been updated.</p>
                    <p class="status">Status: {status.replace('_', ' ').title()}</p>
                    {resolution_text}
                    <p>We'll notify you of any further updates.</p>
                </div>
                <div class="footer">
                    <p>OpenCredit - Digital Credit Platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send(to, subject, html)


# Singleton instance
email_service = EmailService()
