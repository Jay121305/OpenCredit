"""
Financial Record model for dashboard transactions.

Supports income, expense, and transfer record types with categories,
soft-delete, and full audit trail.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RecordType(str, Enum):
    """Type of financial record."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class RecordStatus(str, Enum):
    """Status of financial record."""
    ACTIVE = "active"
    PENDING = "pending"
    CANCELLED = "cancelled"


class RecordCategory(str, Enum):
    """Predefined categories for financial records."""
    # Income categories
    SALARY = "salary"
    FREELANCE = "freelance"
    INVESTMENT = "investment"
    GIFT = "gift"
    REFUND = "refund"
    OTHER_INCOME = "other_income"
    
    # Expense categories
    FOOD = "food"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    RENT = "rent"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    TRAVEL = "travel"
    INSURANCE = "insurance"
    SUBSCRIPTIONS = "subscriptions"
    OTHER_EXPENSE = "other_expense"
    
    # Transfer categories
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class FinancialRecord(Base):
    """Financial record for dashboard tracking."""
    
    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Ownership
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Core fields
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), 
        nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False,
        index=True
    )
    category: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # When the transaction occurred (user-specified)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Status and soft-delete
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default=RecordStatus.ACTIVE.value
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True, 
        onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="financial_records")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_records_user_date", "user_id", "record_date"),
        Index("ix_records_user_type", "user_id", "type"),
        Index("ix_records_user_category", "user_id", "category"),
        Index("ix_records_user_active", "user_id", "is_deleted", "status"),
    )

    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.status = RecordStatus.CANCELLED.value

    @property
    def is_income(self) -> bool:
        """Check if this is an income record."""
        return self.type == RecordType.INCOME.value

    @property
    def is_expense(self) -> bool:
        """Check if this is an expense record."""
        return self.type == RecordType.EXPENSE.value

    @property
    def signed_amount(self) -> Decimal:
        """Get amount with sign based on type (negative for expenses)."""
        if self.type == RecordType.EXPENSE.value:
            return -abs(self.amount)
        return abs(self.amount)
