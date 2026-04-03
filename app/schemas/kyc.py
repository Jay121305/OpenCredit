"""
KYC schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


class KYCPersonalInfo(BaseModel):
    """Personal information for KYC."""
    
    legal_first_name: str = Field(..., min_length=1, max_length=100)
    legal_last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    nationality: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    
    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class KYCAddress(BaseModel):
    """Address information for KYC."""
    
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")


class KYCTaxInfo(BaseModel):
    """Tax information for KYC."""
    
    tax_id: str = Field(..., min_length=1, max_length=50, description="Tax ID (SSN, TIN, etc.)")
    tax_id_type: str = Field(..., description="Type of tax ID (ssn, tin, etc.)")


class KYCSubmitRequest(BaseModel):
    """Request to submit KYC information."""
    
    personal_info: KYCPersonalInfo
    address: KYCAddress
    tax_info: Optional[KYCTaxInfo] = None


class KYCDocumentUploadResponse(BaseModel):
    """Response after document upload."""
    
    document_id: int
    document_type: str
    file_name: str
    uploaded_at: datetime


class KYCStatusResponse(BaseModel):
    """KYC verification status."""
    
    status: str
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    documents_uploaded: int = 0
    required_documents: List[str] = Field(
        default=["passport", "selfie", "utility_bill"],
        description="List of required document types"
    )
    expires_at: Optional[datetime] = None
    risk_level: Optional[str] = None
    sanctions_clear: Optional[bool] = None


class KYCVerificationResponse(BaseModel):
    """Full KYC verification details."""
    
    id: int
    user_id: int
    status: str
    
    # Personal info (masked)
    legal_first_name: Optional[str] = None
    legal_last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    
    # Address
    city: Optional[str] = None
    country: Optional[str] = None
    
    # Documents
    documents: List[KYCDocumentUploadResponse] = []
    
    # Timestamps
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    
    # Risk
    risk_level: Optional[str] = None
    sanctions_clear: Optional[bool] = None


class KYCReviewRequest(BaseModel):
    """Admin request to review KYC."""
    
    status: str = Field(..., description="approved or rejected")
    rejection_reason: Optional[str] = Field(None, description="Required if rejected")
    risk_level: Optional[str] = Field(None, description="low, medium, high")
    notes: Optional[str] = Field(None, description="Internal notes")
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ["approved", "rejected"]:
            raise ValueError("Status must be 'approved' or 'rejected'")
        return v


class KYCListResponse(BaseModel):
    """List of KYC verifications for admin."""
    
    items: List[KYCVerificationResponse]
    total: int
    page: int
    page_size: int
