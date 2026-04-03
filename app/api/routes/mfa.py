"""
MFA (Multi-Factor Authentication) API routes.

Endpoints for:
- TOTP setup and verification
- SMS 2FA setup and verification
- Backup codes management
- MFA challenge/verify during login
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.models.mfa import UserMFA
from app.models.user import User
from app.services.mfa import mfa_service
from app.services.sms import sms_service
from app.services.email import email_service
from app.schemas.mfa import (
    MFAStatusResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPVerifyResponse,
    SMSSetupRequest,
    SMSSetupResponse,
    SMSVerifyRequest,
    BackupCodesResponse,
    DisableMFARequest,
)


router = APIRouter(prefix="/mfa", tags=["mfa"])


def get_or_create_mfa(db: Session, user_id: int) -> UserMFA:
    """Get or create MFA record for user."""
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user_id))
    if not mfa:
        mfa = UserMFA(user_id=user_id)
        db.add(mfa)
        db.commit()
        db.refresh(mfa)
    return mfa


def hash_backup_code(code: str) -> str:
    """Hash a backup code."""
    return hashlib.sha256(code.encode()).hexdigest()


def mask_phone(phone: str) -> str:
    """Mask phone number for display."""
    if len(phone) <= 4:
        return "****"
    return f"****{phone[-4:]}"


@router.get("/status", response_model=MFAStatusResponse, summary="Get MFA status")
def get_mfa_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFAStatusResponse:
    """Get current MFA configuration status."""
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user.id))
    
    if not mfa:
        return MFAStatusResponse(
            mfa_enabled=False,
            totp_enabled=False,
            sms_enabled=False,
            phone_number=None,
            backup_codes_remaining=0,
        )
    
    # Count remaining backup codes
    backup_count = 0
    if mfa.backup_codes:
        backup_count = len([c for c in mfa.backup_codes.split(",") if c])
    
    return MFAStatusResponse(
        mfa_enabled=mfa.is_enabled,
        totp_enabled=mfa.totp_enabled,
        sms_enabled=mfa.sms_enabled,
        phone_number=mask_phone(mfa.phone_number) if mfa.phone_number else None,
        backup_codes_remaining=backup_count,
    )


@router.post("/totp/setup", response_model=TOTPSetupResponse, summary="Set up TOTP")
def setup_totp(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TOTPSetupResponse:
    """
    Set up TOTP (authenticator app) for the user.
    
    Returns a QR code to scan with Google Authenticator, Authy, etc.
    The secret is also provided for manual entry.
    
    After scanning, verify with POST /mfa/totp/verify to enable.
    """
    mfa = get_or_create_mfa(db, user.id)
    
    if mfa.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled. Disable it first to reconfigure.",
        )
    
    # Generate new TOTP setup
    setup = mfa_service.setup_totp(user.email)
    
    # Store secret (not yet confirmed)
    mfa.totp_secret = setup["secret"]
    db.commit()
    
    return TOTPSetupResponse(
        secret=setup["secret"],
        qr_code=setup["qr_code"],
        provisioning_uri=setup["provisioning_uri"],
    )


@router.post("/totp/verify", response_model=TOTPVerifyResponse, summary="Verify and enable TOTP")
def verify_totp(
    request: TOTPVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TOTPVerifyResponse:
    """
    Verify TOTP code and enable TOTP for the user.
    
    This completes the TOTP setup process. Backup codes are generated
    and returned - save them securely as they won't be shown again!
    """
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user.id))
    
    if not mfa or not mfa.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not set up. Call POST /mfa/totp/setup first.",
        )
    
    if mfa.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled.",
        )
    
    # Verify the code
    if not mfa_service.verify_totp(mfa.totp_secret, request.code):
        return TOTPVerifyResponse(verified=False, backup_codes=None)
    
    # Enable TOTP and generate backup codes
    mfa.totp_enabled = True
    mfa.totp_confirmed_at = datetime.utcnow()
    
    backup_codes = mfa_service.generate_backup_codes()
    mfa.backup_codes = ",".join([hash_backup_code(c) for c in backup_codes])
    mfa.backup_codes_generated_at = datetime.utcnow()
    
    db.commit()
    
    # Send notification
    email_service.send(
        to=user.email,
        subject="2FA Enabled on Your OpenCredit Account",
        html=f"""
        <h2>Two-Factor Authentication Enabled</h2>
        <p>Hi {user.full_name},</p>
        <p>TOTP (authenticator app) has been enabled on your account.</p>
        <p>If you didn't do this, please contact support immediately.</p>
        """,
    )
    
    return TOTPVerifyResponse(verified=True, backup_codes=backup_codes)


@router.post("/sms/setup", response_model=SMSSetupResponse, summary="Set up SMS 2FA")
def setup_sms(
    request: SMSSetupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SMSSetupResponse:
    """
    Set up SMS 2FA for the user.
    
    Sends a verification code to the provided phone number.
    Verify with POST /mfa/sms/verify to enable.
    """
    mfa = get_or_create_mfa(db, user.id)
    
    # Normalize phone number
    phone = request.phone_number.strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"
    
    # Generate and send OTP
    otp = mfa_service.generate_sms_otp(phone)
    sms_service.send_otp(phone, otp)
    
    # Store phone (not yet verified)
    mfa.phone_number = phone
    db.commit()
    
    return SMSSetupResponse(
        phone_number=mask_phone(phone),
        message=f"Verification code sent to {mask_phone(phone)}. It expires in {settings.otp_expiry_seconds // 60} minutes.",
    )


@router.post("/sms/verify", response_model=TOTPVerifyResponse, summary="Verify and enable SMS 2FA")
def verify_sms(
    request: SMSVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TOTPVerifyResponse:
    """
    Verify SMS code and enable SMS 2FA for the user.
    """
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user.id))
    
    if not mfa or not mfa.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMS not set up. Call POST /mfa/sms/setup first.",
        )
    
    # Verify the OTP
    if not mfa_service.verify_sms_otp(mfa.phone_number, request.code):
        return TOTPVerifyResponse(verified=False, backup_codes=None)
    
    # Enable SMS 2FA
    mfa.sms_enabled = True
    mfa.phone_verified_at = datetime.utcnow()
    
    # Generate backup codes if not already present
    backup_codes = None
    if not mfa.backup_codes:
        backup_codes = mfa_service.generate_backup_codes()
        mfa.backup_codes = ",".join([hash_backup_code(c) for c in backup_codes])
        mfa.backup_codes_generated_at = datetime.utcnow()
    
    db.commit()
    
    # Send notification
    email_service.send(
        to=user.email,
        subject="SMS 2FA Enabled on Your OpenCredit Account",
        html=f"""
        <h2>SMS Two-Factor Authentication Enabled</h2>
        <p>Hi {user.full_name},</p>
        <p>SMS 2FA has been enabled for phone number {mask_phone(mfa.phone_number)}.</p>
        <p>If you didn't do this, please contact support immediately.</p>
        """,
    )
    
    return TOTPVerifyResponse(verified=True, backup_codes=backup_codes)


@router.post("/backup-codes/regenerate", response_model=BackupCodesResponse, summary="Regenerate backup codes")
def regenerate_backup_codes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BackupCodesResponse:
    """
    Regenerate backup codes. This invalidates all existing backup codes.
    """
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user.id))
    
    if not mfa or not mfa.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled. Enable TOTP or SMS first.",
        )
    
    # Generate new backup codes
    backup_codes = mfa_service.generate_backup_codes()
    mfa.backup_codes = ",".join([hash_backup_code(c) for c in backup_codes])
    mfa.backup_codes_generated_at = datetime.utcnow()
    
    db.commit()
    
    return BackupCodesResponse(codes=backup_codes)


@router.post("/disable", summary="Disable MFA")
def disable_mfa(
    request: DisableMFARequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Disable MFA methods. Requires password confirmation.
    """
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user.id))
    
    if not mfa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not configured.",
        )
    
    if request.method == "totp":
        mfa.totp_enabled = False
        mfa.totp_secret = None
        mfa.totp_confirmed_at = None
        message = "TOTP disabled"
    elif request.method == "sms":
        mfa.sms_enabled = False
        mfa.phone_verified_at = None
        message = "SMS 2FA disabled"
    else:
        # Disable all
        mfa.totp_enabled = False
        mfa.totp_secret = None
        mfa.totp_confirmed_at = None
        mfa.sms_enabled = False
        mfa.phone_verified_at = None
        mfa.backup_codes = None
        message = "All MFA methods disabled"
    
    db.commit()
    
    # Send notification
    email_service.send(
        to=user.email,
        subject="2FA Disabled on Your OpenCredit Account",
        html=f"""
        <h2>⚠️ Two-Factor Authentication Disabled</h2>
        <p>Hi {user.full_name},</p>
        <p>{message} on your account.</p>
        <p>If you didn't do this, please secure your account immediately.</p>
        """,
    )
    
    return {"message": message}


@router.post("/challenge/send", summary="Send MFA challenge")
def send_mfa_challenge(
    method: str = "sms",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Send MFA challenge (SMS OTP or Email OTP).
    
    For TOTP, no challenge needs to be sent - user enters code from app.
    """
    mfa = db.scalar(select(UserMFA).where(UserMFA.user_id == user.id))
    
    if not mfa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not configured.",
        )
    
    if method == "sms":
        if not mfa.sms_enabled or not mfa.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMS 2FA is not enabled.",
            )
        otp = mfa_service.generate_sms_otp(mfa.phone_number)
        sms_service.send_otp(mfa.phone_number, otp)
        return {
            "method": "sms",
            "hint": mask_phone(mfa.phone_number),
            "expires_in": settings.otp_expiry_seconds,
        }
    
    elif method == "email":
        otp = mfa_service.generate_email_otp(user.email)
        email_service.send_otp(user.email, user.full_name, otp)
        return {
            "method": "email",
            "hint": f"{user.email[:3]}***",
            "expires_in": settings.otp_expiry_seconds,
        }
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid method. Use 'sms' or 'email'.",
    )
