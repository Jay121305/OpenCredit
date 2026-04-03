"""
Refund and Chargeback models.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RefundStatus(str, Enum):
    """Refund status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RefundType(str, Enum):
    """Type of refund."""
    FULL = "full"
    PARTIAL = "partial"


class RefundReason(str, Enum):
    """Common refund reasons."""
    DUPLICATE = "duplicate_charge"
    FRAUDULENT = "fraudulent"
    CUSTOMER_REQUEST = "customer_request"
    PRODUCT_NOT_RECEIVED = "product_not_received"
    PRODUCT_DEFECTIVE = "product_defective"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    OTHER = "other"


class ChargebackStatus(str, Enum):
    """Chargeback status."""
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    REPRESENTMENT = "representment"  # Fighting the chargeback
    WON = "won"
    LOST = "lost"
    ACCEPTED = "accepted"  # Merchant accepted the chargeback


class Refund(Base):
    """Refund record."""
    
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Related entities
    payment_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Refund details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    refund_type: Mapped[str] = mapped_column(String(20), default=RefundType.FULL.value, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default=RefundStatus.PENDING.value, nullable=False, index=True)
    
    # Processing
    processed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Reference
    reference_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)  # External reference
    
    # Metadata
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Chargeback(Base):
    """Chargeback record (customer-initiated dispute through bank)."""
    
    __tablename__ = "chargebacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Related entities
    payment_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Chargeback details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    reason_code: Mapped[str] = mapped_column(String(20), nullable=False)  # Bank reason code
    reason_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default=ChargebackStatus.RECEIVED.value, nullable=False, index=True)
    
    # Evidence
    evidence_due_by: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evidence_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    # Resolution
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Financial impact
    fee_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)  # Chargeback fee
    recovered_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # External references
    bank_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    network_case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Visa/MC case ID
    
    # Timestamps
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
