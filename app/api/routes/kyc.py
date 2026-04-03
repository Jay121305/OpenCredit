"""
KYC API routes.

Endpoints for:
- Submitting KYC information
- Uploading documents
- Checking KYC status
- Admin review workflow
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_admin_user
from app.db.session import get_db
from app.models.kyc import KYCVerification, KYCDocument, KYCStatus, DocumentType
from app.models.user import User
from app.services.email import email_service
from app.services.sms import sms_service
from app.schemas.kyc import (
    KYCSubmitRequest,
    KYCStatusResponse,
    KYCVerificationResponse,
    KYCDocumentUploadResponse,
    KYCReviewRequest,
    KYCListResponse,
)


router = APIRouter(prefix="/kyc", tags=["kyc"])

# Upload directory
UPLOAD_DIR = Path("uploads/kyc")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_or_create_kyc(db: Session, user_id: int) -> KYCVerification:
    """Get or create KYC verification for user."""
    kyc = db.scalar(select(KYCVerification).where(KYCVerification.user_id == user_id))
    if not kyc:
        kyc = KYCVerification(user_id=user_id, status=KYCStatus.NOT_STARTED.value)
        db.add(kyc)
        db.commit()
        db.refresh(kyc)
    return kyc


@router.get("/status", response_model=KYCStatusResponse, summary="Get KYC status")
def get_kyc_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KYCStatusResponse:
    """Get current KYC verification status."""
    kyc = db.scalar(select(KYCVerification).where(KYCVerification.user_id == user.id))
    
    if not kyc:
        return KYCStatusResponse(
            status=KYCStatus.NOT_STARTED.value,
            documents_uploaded=0,
        )
    
    # Count documents
    doc_count = db.scalar(
        select(func.count(KYCDocument.id)).where(KYCDocument.kyc_id == kyc.id)
    )
    
    return KYCStatusResponse(
        status=kyc.status,
        submitted_at=kyc.submitted_at,
        reviewed_at=kyc.reviewed_at,
        rejection_reason=kyc.rejection_reason,
        documents_uploaded=doc_count or 0,
        expires_at=kyc.expires_at,
        risk_level=kyc.risk_level,
        sanctions_clear=kyc.sanctions_clear,
    )


@router.post("/submit", response_model=KYCVerificationResponse, summary="Submit KYC information")
def submit_kyc(
    request: KYCSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KYCVerificationResponse:
    """
    Submit personal information for KYC verification.
    
    After submitting, upload required documents using POST /kyc/documents.
    """
    kyc = get_or_create_kyc(db, user.id)
    
    if kyc.status == KYCStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC is already approved.",
        )
    
    # Update personal info
    kyc.legal_first_name = request.personal_info.legal_first_name
    kyc.legal_last_name = request.personal_info.legal_last_name
    kyc.date_of_birth = request.personal_info.date_of_birth
    kyc.nationality = request.personal_info.nationality
    
    # Update address
    kyc.address_line1 = request.address.address_line1
    kyc.address_line2 = request.address.address_line2
    kyc.city = request.address.city
    kyc.state = request.address.state
    kyc.postal_code = request.address.postal_code
    kyc.country = request.address.country
    
    # Update tax info if provided
    if request.tax_info:
        kyc.tax_id = request.tax_info.tax_id
        kyc.tax_id_type = request.tax_info.tax_id_type
    
    kyc.status = KYCStatus.PENDING.value
    kyc.submitted_at = datetime.utcnow()
    kyc.rejection_reason = None  # Clear any previous rejection
    
    db.commit()
    db.refresh(kyc)
    
    # Get documents
    docs = db.execute(
        select(KYCDocument).where(KYCDocument.kyc_id == kyc.id)
    ).scalars().all()
    
    return KYCVerificationResponse(
        id=kyc.id,
        user_id=kyc.user_id,
        status=kyc.status,
        legal_first_name=kyc.legal_first_name,
        legal_last_name=kyc.legal_last_name,
        date_of_birth=kyc.date_of_birth,
        nationality=kyc.nationality,
        city=kyc.city,
        country=kyc.country,
        documents=[
            KYCDocumentUploadResponse(
                document_id=d.id,
                document_type=d.document_type,
                file_name=d.file_name,
                uploaded_at=d.uploaded_at,
            )
            for d in docs
        ],
        submitted_at=kyc.submitted_at,
        reviewed_at=kyc.reviewed_at,
        created_at=kyc.created_at,
        risk_level=kyc.risk_level,
        sanctions_clear=kyc.sanctions_clear,
    )


@router.post("/documents", response_model=KYCDocumentUploadResponse, summary="Upload KYC document")
async def upload_document(
    document_type: str = Query(..., description="Document type: passport, drivers_license, national_id, utility_bill, bank_statement, selfie"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KYCDocumentUploadResponse:
    """
    Upload a document for KYC verification.
    
    Supported types: passport, drivers_license, national_id, utility_bill, bank_statement, selfie
    """
    # Validate document type
    valid_types = [t.value for t in DocumentType]
    if document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}",
        )
    
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )
    
    kyc = get_or_create_kyc(db, user.id)
    
    if kyc.status == KYCStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC is already approved.",
        )
    
    # Generate unique filename
    ext = Path(file.filename).suffix if file.filename else ".bin"
    unique_name = f"{kyc.user_id}_{document_type}_{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Check if document of this type already exists and replace it
    existing = db.scalar(
        select(KYCDocument).where(
            KYCDocument.kyc_id == kyc.id,
            KYCDocument.document_type == document_type,
        )
    )
    
    if existing:
        # Delete old file
        old_path = Path(existing.file_path)
        if old_path.exists():
            old_path.unlink()
        # Update existing record
        existing.file_name = file.filename or unique_name
        existing.file_path = str(file_path)
        existing.file_size = len(content)
        existing.mime_type = file.content_type
        existing.verified = False
        existing.uploaded_at = datetime.utcnow()
        doc = existing
    else:
        # Create new document record
        doc = KYCDocument(
            kyc_id=kyc.id,
            document_type=document_type,
            file_name=file.filename or unique_name,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=file.content_type,
        )
        db.add(doc)
    
    db.commit()
    db.refresh(doc)
    
    return KYCDocumentUploadResponse(
        document_id=doc.id,
        document_type=doc.document_type,
        file_name=doc.file_name,
        uploaded_at=doc.uploaded_at,
    )


@router.get("/documents", summary="List uploaded documents")
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[KYCDocumentUploadResponse]:
    """List all uploaded KYC documents."""
    kyc = db.scalar(select(KYCVerification).where(KYCVerification.user_id == user.id))
    
    if not kyc:
        return []
    
    docs = db.execute(
        select(KYCDocument).where(KYCDocument.kyc_id == kyc.id)
    ).scalars().all()
    
    return [
        KYCDocumentUploadResponse(
            document_id=d.id,
            document_type=d.document_type,
            file_name=d.file_name,
            uploaded_at=d.uploaded_at,
        )
        for d in docs
    ]


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/pending", response_model=KYCListResponse, summary="List pending KYC verifications")
def list_pending_kyc(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> KYCListResponse:
    """List all pending KYC verifications for admin review."""
    offset = (page - 1) * page_size
    
    # Count total
    total = db.scalar(
        select(func.count(KYCVerification.id)).where(
            KYCVerification.status.in_([KYCStatus.PENDING.value, KYCStatus.UNDER_REVIEW.value])
        )
    )
    
    # Get items
    kycs = db.execute(
        select(KYCVerification)
        .where(KYCVerification.status.in_([KYCStatus.PENDING.value, KYCStatus.UNDER_REVIEW.value]))
        .order_by(KYCVerification.submitted_at.asc())
        .offset(offset)
        .limit(page_size)
    ).scalars().all()
    
    items = []
    for kyc in kycs:
        docs = db.execute(
            select(KYCDocument).where(KYCDocument.kyc_id == kyc.id)
        ).scalars().all()
        
        items.append(KYCVerificationResponse(
            id=kyc.id,
            user_id=kyc.user_id,
            status=kyc.status,
            legal_first_name=kyc.legal_first_name,
            legal_last_name=kyc.legal_last_name,
            date_of_birth=kyc.date_of_birth,
            nationality=kyc.nationality,
            city=kyc.city,
            country=kyc.country,
            documents=[
                KYCDocumentUploadResponse(
                    document_id=d.id,
                    document_type=d.document_type,
                    file_name=d.file_name,
                    uploaded_at=d.uploaded_at,
                )
                for d in docs
            ],
            submitted_at=kyc.submitted_at,
            reviewed_at=kyc.reviewed_at,
            created_at=kyc.created_at,
            risk_level=kyc.risk_level,
            sanctions_clear=kyc.sanctions_clear,
        ))
    
    return KYCListResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/{kyc_id}/review", response_model=KYCVerificationResponse, summary="Review KYC")
def review_kyc(
    kyc_id: int,
    request: KYCReviewRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> KYCVerificationResponse:
    """
    Review and approve/reject a KYC verification.
    
    Only admins can review KYC submissions.
    """
    kyc = db.scalar(select(KYCVerification).where(KYCVerification.id == kyc_id))
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC verification not found.",
        )
    
    if kyc.status not in [KYCStatus.PENDING.value, KYCStatus.UNDER_REVIEW.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review KYC with status: {kyc.status}",
        )
    
    if request.status == "rejected" and not request.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required when rejecting.",
        )
    
    # Update status
    kyc.status = KYCStatus.APPROVED.value if request.status == "approved" else KYCStatus.REJECTED.value
    kyc.reviewed_by = admin.id
    kyc.reviewed_at = datetime.utcnow()
    kyc.rejection_reason = request.rejection_reason
    kyc.notes = request.notes
    kyc.risk_level = request.risk_level
    
    db.commit()
    db.refresh(kyc)
    
    # Get user for notifications
    user = db.scalar(select(User).where(User.id == kyc.user_id))
    
    if user:
        # Send email notification
        email_service.send_kyc_status(
            to=user.email,
            name=user.full_name,
            status=kyc.status,
            reason=request.rejection_reason,
        )
    
    # Get documents
    docs = db.execute(
        select(KYCDocument).where(KYCDocument.kyc_id == kyc.id)
    ).scalars().all()
    
    return KYCVerificationResponse(
        id=kyc.id,
        user_id=kyc.user_id,
        status=kyc.status,
        legal_first_name=kyc.legal_first_name,
        legal_last_name=kyc.legal_last_name,
        date_of_birth=kyc.date_of_birth,
        nationality=kyc.nationality,
        city=kyc.city,
        country=kyc.country,
        documents=[
            KYCDocumentUploadResponse(
                document_id=d.id,
                document_type=d.document_type,
                file_name=d.file_name,
                uploaded_at=d.uploaded_at,
            )
            for d in docs
        ],
        submitted_at=kyc.submitted_at,
        reviewed_at=kyc.reviewed_at,
        created_at=kyc.created_at,
        risk_level=kyc.risk_level,
        sanctions_clear=kyc.sanctions_clear,
    )
