"""
Transaction Dispute models.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DisputeStatus(str, Enum):
    """Dispute status."""
    OPENED = "opened"
    UNDER_REVIEW = "under_review"
    AWAITING_INFO = "awaiting_info"
    ESCALATED = "escalated"
    RESOLVED_FOR_USER = "resolved_for_user"
    RESOLVED_FOR_MERCHANT = "resolved_for_merchant"
    CLOSED = "closed"
    WITHDRAWN = "withdrawn"


class DisputeReason(str, Enum):
    """Dispute reason categories."""
    UNAUTHORIZED = "unauthorized"
    NOT_RECEIVED = "not_received"
    NOT_AS_DESCRIBED = "not_as_described"
    DUPLICATE = "duplicate"
    WRONG_AMOUNT = "wrong_amount"
    CREDIT_NOT_PROCESSED = "credit_not_processed"
    OTHER = "other"


class DisputePriority(str, Enum):
    """Dispute priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Dispute(Base):
    """Transaction dispute record."""
    
    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Related entities
    payment_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Dispute details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status and priority
    status: Mapped[str] = mapped_column(String(30), default=DisputeStatus.OPENED.value, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=DisputePriority.MEDIUM.value, nullable=False)
    
    # Assignment
    assigned_to: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timeline
    response_due_by: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Resolution
    resolution_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # refund, credit, no_action
    resolution_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Reference number
    case_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DisputeEvidence(Base):
    """Evidence uploaded for a dispute."""
    
    __tablename__ = "dispute_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dispute_id: Mapped[int] = mapped_column(Integer, ForeignKey("disputes.id", ondelete="CASCADE"), index=True)
    
    # Uploader
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploader_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, merchant, admin
    
    # File info
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)  # receipt, screenshot, communication, etc.
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DisputeComment(Base):
    """Comments/messages on a dispute."""
    
    __tablename__ = "dispute_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dispute_id: Mapped[int] = mapped_column(Integer, ForeignKey("disputes.id", ondelete="CASCADE"), index=True)
    
    # Author
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, merchant, admin, system
    
    # Content
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Internal admin notes
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
