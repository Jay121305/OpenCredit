"""
MFA (Multi-Factor Authentication) schemas.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class MFAStatusResponse(BaseModel):
    """MFA status for a user."""
    
    mfa_enabled: bool = Field(..., description="Whether any MFA method is enabled")
    totp_enabled: bool = Field(..., description="Whether TOTP (authenticator app) is enabled")
    sms_enabled: bool = Field(..., description="Whether SMS 2FA is enabled")
    phone_number: Optional[str] = Field(None, description="Masked phone number if SMS enabled")
    backup_codes_remaining: int = Field(0, description="Number of unused backup codes")


class TOTPSetupResponse(BaseModel):
    """TOTP setup response with QR code."""
    
    secret: str = Field(..., description="TOTP secret (save this for manual entry)")
    qr_code: str = Field(..., description="QR code as base64 data URL")
    provisioning_uri: str = Field(..., description="otpauth:// URI for manual setup")


class TOTPVerifyRequest(BaseModel):
    """Request to verify TOTP code and enable TOTP."""
    
    code: str = Field(..., min_length=6, max_length=6, description="6-digit code from authenticator app")


class TOTPVerifyResponse(BaseModel):
    """Response after TOTP verification."""
    
    verified: bool = Field(..., description="Whether the code was valid")
    backup_codes: Optional[List[str]] = Field(None, description="Backup codes (only shown once!)")


class SMSSetupRequest(BaseModel):
    """Request to set up SMS 2FA."""
    
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number in E.164 format")


class SMSSetupResponse(BaseModel):
    """Response after SMS setup initiation."""
    
    phone_number: str = Field(..., description="Masked phone number")
    message: str = Field(..., description="Status message")


class SMSVerifyRequest(BaseModel):
    """Request to verify SMS OTP."""
    
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class MFAChallengeRequest(BaseModel):
    """Request to initiate MFA challenge during login."""
    
    method: str = Field("totp", description="MFA method to use: totp, sms")


class MFAChallengeResponse(BaseModel):
    """Response with MFA challenge details."""
    
    challenge_id: str = Field(..., description="Challenge ID for verification")
    method: str = Field(..., description="MFA method being used")
    expires_in: int = Field(..., description="Seconds until challenge expires")
    hint: Optional[str] = Field(None, description="Hint (e.g., masked phone number)")


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA during login."""
    
    challenge_id: str = Field(..., description="Challenge ID from MFA initiation")
    code: str = Field(..., min_length=6, max_length=8, description="MFA code")


class MFAVerifyResponse(BaseModel):
    """Response after MFA verification."""
    
    verified: bool = Field(..., description="Whether verification succeeded")
    access_token: Optional[str] = Field(None, description="JWT token if verified")
    token_type: Optional[str] = Field(None, description="Token type")


class BackupCodesResponse(BaseModel):
    """Response with new backup codes."""
    
    codes: List[str] = Field(..., description="New backup codes (save these securely!)")
    message: str = Field(default="Save these codes securely. They can only be used once each.")


class DisableMFARequest(BaseModel):
    """Request to disable MFA."""
    
    password: str = Field(..., description="Current password for confirmation")
    method: Optional[str] = Field(None, description="Specific method to disable, or all if not specified")
