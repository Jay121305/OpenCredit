"""
MFA (Multi-Factor Authentication) model.

Stores user MFA settings and backup codes.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MFAMethod(str, Enum):
    """MFA method types."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"


class UserMFA(Base):
    """User MFA configuration."""
    
    __tablename__ = "user_mfa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    
    # TOTP
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    totp_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # SMS
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Backup codes (comma-separated hashes)
    backup_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    backup_codes_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @property
    def is_enabled(self) -> bool:
        """Check if any MFA method is enabled."""
        return self.totp_enabled or self.sms_enabled
    
    @property
    def enabled_methods(self) -> list[str]:
        """Get list of enabled MFA methods."""
        methods = []
        if self.totp_enabled:
            methods.append(MFAMethod.TOTP.value)
        if self.sms_enabled:
            methods.append(MFAMethod.SMS.value)
        return methods
