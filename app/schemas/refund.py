"""
Refund schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class RefundCreateRequest(BaseModel):
    """Request to create a refund."""
    
    payment_id: int = Field(..., description="ID of the payment to refund")
    amount: Optional[Decimal] = Field(None, description="Amount to refund (full refund if not specified)")
    reason: str = Field(..., description="Reason for refund")
    description: Optional[str] = Field(None, description="Additional details")


class RefundResponse(BaseModel):
    """Refund details."""
    
    id: int
    payment_id: int
    merchant_id: Optional[int] = None
    user_id: Optional[int] = None
    amount: Decimal
    currency: str
    refund_type: str
    reason: str
    description: Optional[str] = None
    status: str
    processed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime


class RefundProcessRequest(BaseModel):
    """Admin request to process a refund."""
    
    action: str = Field(..., description="'approve' or 'reject'")
    rejection_reason: Optional[str] = Field(None, description="Required if rejecting")


class RefundListResponse(BaseModel):
    """List of refunds."""
    
    items: List[RefundResponse]
    total: int
    page: int
    page_size: int


class ChargebackCreateRequest(BaseModel):
    """Request to record a chargeback."""
    
    payment_id: int = Field(..., description="ID of the disputed payment")
    amount: Decimal = Field(..., description="Chargeback amount")
    reason_code: str = Field(..., description="Bank reason code")
    reason_description: Optional[str] = Field(None, description="Description of the reason")
    bank_reference: Optional[str] = Field(None, description="Bank reference number")
    evidence_due_by: Optional[datetime] = Field(None, description="Deadline to submit evidence")


class ChargebackResponse(BaseModel):
    """Chargeback details."""
    
    id: int
    payment_id: int
    merchant_id: Optional[int] = None
    user_id: Optional[int] = None
    amount: Decimal
    currency: str
    reason_code: str
    reason_description: Optional[str] = None
    status: str
    evidence_due_by: Optional[datetime] = None
    evidence_submitted: bool
    resolved_at: Optional[datetime] = None
    fee_amount: Optional[Decimal] = None
    recovered_amount: Optional[Decimal] = None
    bank_reference: Optional[str] = None
    received_at: datetime
    created_at: datetime


class ChargebackUpdateRequest(BaseModel):
    """Request to update a chargeback."""
    
    status: Optional[str] = Field(None, description="New status")
    evidence_details: Optional[str] = Field(None, description="Evidence JSON")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class ChargebackListResponse(BaseModel):
    """List of chargebacks."""
    
    items: List[ChargebackResponse]
    total: int
    page: int
    page_size: int
