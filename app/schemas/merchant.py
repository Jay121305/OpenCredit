"""
Merchant schemas for API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MerchantCreateRequest(BaseModel):
    """Request to create a new merchant."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Merchant business name",
        json_schema_extra={"example": "Acme Electronics"}
    )


class MerchantCreateResponse(BaseModel):
    """Response after creating a merchant."""
    
    merchant_id: int = Field(..., description="Unique merchant ID")
    name: str = Field(..., description="Merchant name")
    api_key: str = Field(
        ...,
        description="API key (shown only once - store securely!)",
        json_schema_extra={"example": "oc_live_abc123..."}
    )


class MerchantKeyRotateResponse(BaseModel):
    """Response after rotating a merchant's API key."""
    
    merchant_id: int = Field(..., description="Merchant ID")
    new_api_key: str = Field(
        ...,
        description="New API key (store securely!)",
        json_schema_extra={"example": "oc_live_xyz789..."}
    )
    old_key_valid_until: Optional[datetime] = Field(
        None,
        description="Old key remains valid until this time (grace period)"
    )
    message: str = Field(
        default="API key rotated successfully",
        description="Status message"
    )


class MerchantResponse(BaseModel):
    """Merchant details response (without sensitive data)."""
    
    id: int
    name: str
    is_active: bool
    created_at: datetime
    key_rotated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MerchantKeyRevokeResponse(BaseModel):
    """Response after revoking a merchant's secondary key."""
    
    merchant_id: int
    message: str = "Secondary API key revoked"
