"""
Payment schemas with strong input validation.

Includes:
- Amount limits
- Currency validation (ISO 4217)
- Idempotency key format validation (UUID v4)
- Category and geo sanitization
"""

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


# Valid ISO 4217 currency codes (subset)
VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CNY", "INR", "CAD", "AUD", "CHF", "HKD",
    "SGD", "SEK", "KRW", "NOK", "NZD", "MXN", "TWD", "ZAR", "BRL", "DKK",
}

# Valid payment categories
VALID_CATEGORIES = {
    "food", "groceries", "transport", "entertainment", "shopping", "utilities",
    "healthcare", "education", "travel", "services", "other", "uncategorized",
}

# ISO 3166-1 alpha-2 country codes (subset)
VALID_GEO_CODES = {
    "US", "GB", "DE", "FR", "JP", "CN", "IN", "CA", "AU", "BR",
    "KR", "IT", "ES", "MX", "NL", "SE", "CH", "SG", "HK", "UNKNOWN",
}


class PaymentRequest(BaseModel):
    """Payment request with comprehensive validation."""
    
    amount: float = Field(
        ...,
        gt=0,
        description="Payment amount (must be positive)",
        json_schema_extra={"example": 150.50}
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code",
        json_schema_extra={"example": "USD"}
    )
    category: str = Field(
        default="uncategorized",
        min_length=2,
        max_length=64,
        description="Payment category",
        json_schema_extra={"example": "shopping"}
    )
    geo: str = Field(
        default="UNKNOWN",
        min_length=2,
        max_length=64,
        description="ISO 3166-1 alpha-2 country code",
        json_schema_extra={"example": "US"}
    )
    idempotency_key: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Unique idempotency key (UUID v4 recommended)",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_limit(cls, v: float) -> float:
        """Validate amount doesn't exceed maximum transaction limit."""
        max_amount = settings.max_transaction_amount
        if v > max_amount:
            raise ValueError(f"Amount exceeds maximum transaction limit of {max_amount}")
        # Round to 2 decimal places
        return round(v, 2)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency is a known ISO 4217 code."""
        v = v.upper()
        if v not in VALID_CURRENCIES:
            raise ValueError(f"Invalid currency code. Allowed: {', '.join(sorted(VALID_CURRENCIES))}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate and normalize category."""
        v = v.lower().strip()
        # Allow any category but sanitize
        v = re.sub(r"[^a-z0-9_\-]", "", v)
        if not v:
            return "uncategorized"
        return v

    @field_validator("geo")
    @classmethod
    def validate_geo(cls, v: str) -> str:
        """Validate geo code."""
        v = v.upper().strip()
        if v not in VALID_GEO_CODES:
            # Don't reject, but flag as unknown
            return "UNKNOWN"
        return v

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        """
        Validate idempotency key format.
        
        Accepts UUID v4 format or alphanumeric strings.
        """
        v = v.strip()
        
        # Try to parse as UUID
        try:
            uuid.UUID(v, version=4)
            return v.lower()
        except ValueError:
            pass
        
        # Allow alphanumeric with hyphens/underscores
        if not re.match(r"^[a-zA-Z0-9\-_]+$", v):
            raise ValueError("Idempotency key must be alphanumeric (hyphens and underscores allowed)")
        
        return v


class PaymentResponse(BaseModel):
    """Payment response with transaction details."""
    
    transaction_id: int = Field(
        ...,
        description="Unique transaction ID",
        json_schema_extra={"example": 12345}
    )
    status: str = Field(
        ...,
        description="Transaction status (approved, rejected, flagged)",
        json_schema_extra={"example": "approved"}
    )
    fraud_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Fraud detection score (0.0 - 1.0)",
        json_schema_extra={"example": 0.15}
    )
    available_credit: float = Field(
        ...,
        description="Remaining available credit after transaction",
        json_schema_extra={"example": 4850.50}
    )
    created_at: datetime = Field(
        ...,
        description="Transaction timestamp",
        json_schema_extra={"example": "2026-03-23T07:00:00Z"}
    )
