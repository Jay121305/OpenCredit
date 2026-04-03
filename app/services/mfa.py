"""
Two-Factor Authentication (2FA) service.

Supports:
- TOTP (Time-based One-Time Password) - Google Authenticator compatible
- SMS OTP - One-time codes sent via Twilio
- Email OTP - One-time codes sent via Resend
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from io import BytesIO
import base64

import pyotp
import qrcode

from app.core.config import settings


logger = logging.getLogger(__name__)


class TOTPService:
    """
    TOTP (Time-based One-Time Password) service.
    
    Compatible with Google Authenticator, Authy, and other TOTP apps.
    """
    
    def __init__(self) -> None:
        self.issuer = settings.totp_issuer
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """
        Get the provisioning URI for QR code generation.
        
        Args:
            secret: TOTP secret
            email: User's email address
            
        Returns:
            otpauth:// URI for TOTP setup
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.issuer)
    
    def generate_qr_code(self, secret: str, email: str) -> str:
        """
        Generate QR code image as base64 data URL.
        
        Args:
            secret: TOTP secret
            email: User's email address
            
        Returns:
            Base64 encoded PNG image as data URL
        """
        uri = self.get_provisioning_uri(secret, email)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def verify(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: User's TOTP secret
            code: 6-digit code from authenticator app
            
        Returns:
            True if code is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            # Allow 1 period of clock drift (30 seconds before/after)
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False


class OTPService:
    """
    One-Time Password service for SMS and Email OTP.
    
    Generates numeric codes for verification via SMS or Email.
    """
    
    def __init__(self) -> None:
        self.expiry_seconds = settings.otp_expiry_seconds
        # In-memory store for OTPs (use Redis in production)
        self._otp_store: dict[str, Tuple[str, datetime]] = {}
    
    def generate(self, identifier: str, digits: int = 6) -> str:
        """
        Generate an OTP code for an identifier (email or phone).
        
        Args:
            identifier: Email or phone number
            digits: Number of digits (default 6)
            
        Returns:
            Generated OTP code
        """
        # Generate cryptographically secure random digits
        code = "".join([str(secrets.randbelow(10)) for _ in range(digits)])
        
        # Store with expiry
        expiry = datetime.utcnow() + timedelta(seconds=self.expiry_seconds)
        self._otp_store[identifier] = (code, expiry)
        
        logger.info(f"OTP generated for {identifier[:4]}***")
        return code
    
    def verify(self, identifier: str, code: str) -> bool:
        """
        Verify an OTP code.
        
        Args:
            identifier: Email or phone number
            code: OTP code to verify
            
        Returns:
            True if valid, False otherwise
        """
        stored = self._otp_store.get(identifier)
        if not stored:
            logger.warning(f"OTP not found for {identifier[:4]}***")
            return False
        
        stored_code, expiry = stored
        
        # Check expiry
        if datetime.utcnow() > expiry:
            logger.warning(f"OTP expired for {identifier[:4]}***")
            del self._otp_store[identifier]
            return False
        
        # Constant-time comparison to prevent timing attacks
        if secrets.compare_digest(stored_code, code):
            # Invalidate after successful use
            del self._otp_store[identifier]
            logger.info(f"OTP verified for {identifier[:4]}***")
            return True
        
        logger.warning(f"OTP mismatch for {identifier[:4]}***")
        return False
    
    def invalidate(self, identifier: str) -> None:
        """Invalidate any existing OTP for an identifier."""
        if identifier in self._otp_store:
            del self._otp_store[identifier]


class MFAService:
    """
    Multi-Factor Authentication service combining TOTP and OTP.
    """
    
    def __init__(self) -> None:
        self.totp = TOTPService()
        self.otp = OTPService()
    
    def setup_totp(self, email: str) -> dict:
        """
        Set up TOTP for a user.
        
        Returns:
            dict with secret, qr_code (base64), and provisioning_uri
        """
        secret = self.totp.generate_secret()
        qr_code = self.totp.generate_qr_code(secret, email)
        uri = self.totp.get_provisioning_uri(secret, email)
        
        return {
            "secret": secret,
            "qr_code": qr_code,
            "provisioning_uri": uri,
        }
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify a TOTP code."""
        return self.totp.verify(secret, code)
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        Generate backup codes for account recovery.
        
        Returns:
            List of backup codes (8 characters each)
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8 hex characters
            codes.append(code)
        return codes
    
    def generate_sms_otp(self, phone: str) -> str:
        """Generate OTP for SMS delivery."""
        return self.otp.generate(f"sms:{phone}")
    
    def verify_sms_otp(self, phone: str, code: str) -> bool:
        """Verify SMS OTP."""
        return self.otp.verify(f"sms:{phone}", code)
    
    def generate_email_otp(self, email: str) -> str:
        """Generate OTP for email delivery."""
        return self.otp.generate(f"email:{email}")
    
    def verify_email_otp(self, email: str, code: str) -> bool:
        """Verify email OTP."""
        return self.otp.verify(f"email:{email}", code)


# Singleton instances
totp_service = TOTPService()
otp_service = OTPService()
mfa_service = MFAService()
