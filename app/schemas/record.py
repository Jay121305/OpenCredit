"""
Financial Record schemas for CRUD operations, filtering, and pagination.
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.record import RecordCategory, RecordStatus, RecordType


class RecordCreate(BaseModel):
    """Schema for creating a new financial record."""
    
    amount: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("999999999.99"),
        description="Transaction amount (positive value)",
        json_schema_extra={"example": 150.00}
    )
    type: RecordType = Field(
        ...,
        description="Record type: income, expense, or transfer",
        json_schema_extra={"example": "expense"}
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Category of the record",
        json_schema_extra={"example": "food"}
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description or notes",
        json_schema_extra={"example": "Lunch at restaurant"}
    )
    record_date: date = Field(
        ...,
        description="Date when the transaction occurred",
        json_schema_extra={"example": "2026-04-03"}
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Normalize category to lowercase."""
        return v.lower().strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize description."""
        if v:
            return v.strip()
        return v


class RecordUpdate(BaseModel):
    """Schema for updating a financial record. All fields optional."""
    
    amount: Optional[Decimal] = Field(
        None,
        gt=0,
        le=Decimal("999999999.99"),
        description="Transaction amount"
    )
    type: Optional[RecordType] = Field(
        None,
        description="Record type"
    )
    category: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Category"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description or notes"
    )
    record_date: Optional[date] = Field(
        None,
        description="Transaction date"
    )
    status: Optional[RecordStatus] = Field(
        None,
        description="Record status"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lower().strip()
        return v


class RecordResponse(BaseModel):
    """Schema for record response (single record)."""
    
    id: int
    user_id: int
    amount: Decimal
    type: str
    category: str
    description: Optional[str]
    record_date: date
    status: str
    is_deleted: bool
    created_at: str
    updated_at: Optional[str]

    model_config = {"from_attributes": True}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def serialize_datetime(cls, v):
        if v is None:
            return None
        return v.isoformat() if hasattr(v, "isoformat") else str(v)


class RecordFilter(BaseModel):
    """Schema for filtering records in list queries."""
    
    type: Optional[RecordType] = Field(
        None,
        description="Filter by record type"
    )
    category: Optional[str] = Field(
        None,
        description="Filter by category"
    )
    status: Optional[RecordStatus] = Field(
        None,
        description="Filter by status"
    )
    date_from: Optional[date] = Field(
        None,
        description="Start date (inclusive)"
    )
    date_to: Optional[date] = Field(
        None,
        description="End date (inclusive)"
    )
    min_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Minimum amount"
    )
    max_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Maximum amount"
    )
    search: Optional[str] = Field(
        None,
        max_length=100,
        description="Search in description"
    )
    include_deleted: bool = Field(
        False,
        description="Include soft-deleted records"
    )


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    
    page: int = Field(
        1,
        ge=1,
        description="Page number (1-indexed)"
    )
    per_page: int = Field(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100)"
    )
    sort_by: str = Field(
        "record_date",
        description="Field to sort by"
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order: asc or desc"
    )


class PaginationMeta(BaseModel):
    """Pagination metadata in list responses."""
    
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class RecordListResponse(BaseModel):
    """Schema for paginated record list response."""
    
    items: list[RecordResponse]
    pagination: PaginationMeta
