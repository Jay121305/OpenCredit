"""
KYC (Know Your Customer) models.

Supports manual document verification workflow.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KYCStatus(str, Enum):
    """KYC verification status."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DocumentType(str, Enum):
    """Supported document types."""
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    SELFIE = "selfie"


class KYCVerification(Base):
    """User KYC verification record."""
    
    __tablename__ = "kyc_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default=KYCStatus.NOT_STARTED.value, nullable=False, index=True)
    
    # Personal Information
    legal_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    legal_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    nationality: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    
    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    
    # Tax Information
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # SSN, TIN, etc.
    tax_id_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Review
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Risk assessment
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low, medium, high
    risk_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Sanctions check
    sanctions_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sanctions_clear: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Timestamps
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class KYCDocument(Base):
    """KYC document uploads."""
    
    __tablename__ = "kyc_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kyc_id: Mapped[int] = mapped_column(Integer, ForeignKey("kyc_verifications.id", ondelete="CASCADE"), index=True)
    
    # Document info
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Relative path or URL
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Bytes
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Verification
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Metadata
    extracted_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
