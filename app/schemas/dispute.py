"""
Dispute schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class DisputeCreateRequest(BaseModel):
    """Request to create a dispute."""
    
    payment_id: int = Field(..., description="ID of the disputed payment")
    reason: str = Field(..., description="Reason category for the dispute")
    description: str = Field(..., min_length=10, description="Detailed description of the issue")
    amount: Optional[Decimal] = Field(None, description="Disputed amount (defaults to full payment)")


class DisputeResponse(BaseModel):
    """Dispute details."""
    
    id: int
    case_number: str
    payment_id: int
    user_id: Optional[int] = None
    merchant_id: Optional[int] = None
    amount: Decimal
    currency: str
    reason: str
    description: str
    status: str
    priority: str
    assigned_to: Optional[int] = None
    response_due_by: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None
    resolution_amount: Optional[Decimal] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DisputeUpdateRequest(BaseModel):
    """Request to update a dispute."""
    
    status: Optional[str] = Field(None, description="New status")
    priority: Optional[str] = Field(None, description="New priority")
    assigned_to: Optional[int] = Field(None, description="Assign to admin user ID")
    resolution_type: Optional[str] = Field(None, description="Resolution type")
    resolution_amount: Optional[Decimal] = Field(None, description="Resolution amount")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class DisputeEvidenceResponse(BaseModel):
    """Evidence file details."""
    
    id: int
    dispute_id: int
    uploaded_by: Optional[int] = None
    uploader_type: str
    file_name: str
    file_size: int
    mime_type: str
    description: Optional[str] = None
    evidence_type: str
    uploaded_at: datetime


class DisputeCommentCreate(BaseModel):
    """Request to add a comment."""
    
    message: str = Field(..., min_length=1, description="Comment message")
    is_internal: bool = Field(False, description="Mark as internal admin note")


class DisputeCommentResponse(BaseModel):
    """Comment details."""
    
    id: int
    dispute_id: int
    author_id: Optional[int] = None
    author_type: str
    message: str
    is_internal: bool
    created_at: datetime


class DisputeDetailResponse(BaseModel):
    """Full dispute details with evidence and comments."""
    
    dispute: DisputeResponse
    evidence: List[DisputeEvidenceResponse]
    comments: List[DisputeCommentResponse]


class DisputeListResponse(BaseModel):
    """List of disputes."""
    
    items: List[DisputeResponse]
    total: int
    page: int
    page_size: int
