"""
Transaction model with optimized indexes for query performance.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    approved = "approved"
    rejected = "rejected"
    flagged = "flagged"


class Transaction(Base):
    """
    Transaction record for payment processing.
    
    Indexes:
    - Primary key on id
    - user_id for user transaction lookups
    - merchant_id for merchant reporting
    - idempotency_key (unique) for deduplication
    - created_at for time-range queries
    - Composite (user_id, created_at) for analytics queries
    - Composite (user_id, category) for spending by category
    """
    
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="uncategorized")
    geo: Mapped[str] = mapped_column(String(64), nullable=False, default="UNKNOWN")
    status: Mapped[TransactionStatus] = mapped_column(SqlEnum(TransactionStatus), nullable=False)
    fraud_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Composite indexes for common query patterns
    __table_args__ = (
        # Analytics: user transactions over time
        Index("ix_transactions_user_created", "user_id", "created_at"),
        # Analytics: spending by category
        Index("ix_transactions_user_category", "user_id", "category"),
        # Fraud: recent transactions by user
        Index("ix_transactions_user_status", "user_id", "status"),
    )
