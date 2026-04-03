"""
Dispute API routes.

Complete dispute workflow for transaction issues.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_admin_user
from app.db.session import get_db
from app.models.dispute import Dispute, DisputeEvidence, DisputeComment, DisputeStatus, DisputePriority
from app.models.transaction import Transaction as Payment
from app.models.user import User
from app.services.email import email_service
from app.services.webhooks import webhook_service
from app.schemas.dispute import (
    DisputeCreateRequest,
    DisputeResponse,
    DisputeUpdateRequest,
    DisputeEvidenceResponse,
    DisputeCommentCreate,
    DisputeCommentResponse,
    DisputeDetailResponse,
    DisputeListResponse,
)


router = APIRouter(prefix="/disputes", tags=["disputes"])

# Upload directory
EVIDENCE_DIR = Path("uploads/disputes")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/plain",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def generate_case_number() -> str:
    """Generate a unique case number."""
    return f"DSP-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"


# ============================================================================
# User Endpoints
# ============================================================================

@router.post("", response_model=DisputeResponse, summary="Create a dispute")
async def create_dispute(
    request: DisputeCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisputeResponse:
    """
    Create a new dispute for a transaction.
    
    The dispute will be reviewed by our support team.
    """
    # Get payment
    payment = db.scalar(select(Payment).where(Payment.id == request.payment_id))
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    
    # Check ownership
    if payment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only dispute your own payments.",
        )
    
    # Check for existing open dispute
    existing = db.scalar(
        select(Dispute).where(
            Dispute.payment_id == payment.id,
            Dispute.status.in_([
                DisputeStatus.OPENED.value,
                DisputeStatus.UNDER_REVIEW.value,
                DisputeStatus.AWAITING_INFO.value,
            ])
        )
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An open dispute already exists for this payment (Case: {existing.case_number}).",
        )
    
    # Determine amount
    dispute_amount = request.amount if request.amount else payment.amount
    
    if dispute_amount > payment.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dispute amount cannot exceed payment amount.",
        )
    
    # Create dispute
    dispute = Dispute(
        payment_id=payment.id,
        user_id=user.id,
        merchant_id=payment.merchant_id,
        amount=dispute_amount,
        currency="USD",
        reason=request.reason,
        description=request.description,
        status=DisputeStatus.OPENED.value,
        priority=DisputePriority.MEDIUM.value,
        case_number=generate_case_number(),
        response_due_by=datetime.utcnow() + timedelta(days=7),
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    
    # Add system comment
    comment = DisputeComment(
        dispute_id=dispute.id,
        author_id=user.id,
        author_type="system",
        message=f"Dispute opened by user. Reason: {request.reason}",
    )
    db.add(comment)
    db.commit()
    
    # Send webhook to merchant
    if payment.merchant_id:
        await webhook_service.dispatch_event(
            db=db,
            merchant_id=payment.merchant_id,
            event_type="dispute.opened",
            data={
                "dispute_id": dispute.id,
                "case_number": dispute.case_number,
                "payment_id": payment.id,
                "amount": str(dispute.amount),
                "reason": dispute.reason,
            },
        )
    
    # Send email confirmation
    email_service.send_dispute_update(
        to=user.email,
        name=user.full_name,
        case_number=dispute.case_number,
        status="opened",
        message="Your dispute has been received and is under review.",
    )
    
    return DisputeResponse(
        id=dispute.id,
        case_number=dispute.case_number,
        payment_id=dispute.payment_id,
        user_id=dispute.user_id,
        merchant_id=dispute.merchant_id,
        amount=dispute.amount,
        currency=dispute.currency,
        reason=dispute.reason,
        description=dispute.description,
        status=dispute.status,
        priority=dispute.priority,
        response_due_by=dispute.response_due_by,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
    )


@router.get("", response_model=DisputeListResponse, summary="List my disputes")
def list_my_disputes(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisputeListResponse:
    """List all disputes for the current user."""
    query = select(Dispute).where(Dispute.user_id == user.id)
    count_query = select(func.count(Dispute.id)).where(Dispute.user_id == user.id)
    
    if status_filter:
        query = query.where(Dispute.status == status_filter)
        count_query = count_query.where(Dispute.status == status_filter)
    
    total = db.scalar(count_query)
    
    disputes = db.execute(
        query.order_by(Dispute.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    
    return DisputeListResponse(
        items=[
            DisputeResponse(
                id=d.id,
                case_number=d.case_number,
                payment_id=d.payment_id,
                user_id=d.user_id,
                merchant_id=d.merchant_id,
                amount=d.amount,
                currency=d.currency,
                reason=d.reason,
                description=d.description,
                status=d.status,
                priority=d.priority,
                assigned_to=d.assigned_to,
                response_due_by=d.response_due_by,
                resolved_at=d.resolved_at,
                resolution_type=d.resolution_type,
                resolution_amount=d.resolution_amount,
                resolution_notes=d.resolution_notes,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in disputes
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{dispute_id}", response_model=DisputeDetailResponse, summary="Get dispute details")
def get_dispute(
    dispute_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisputeDetailResponse:
    """Get full details of a dispute including evidence and comments."""
    dispute = db.scalar(
        select(Dispute).where(
            Dispute.id == dispute_id,
            Dispute.user_id == user.id,
        )
    )
    
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found.",
        )
    
    # Get evidence
    evidence = db.execute(
        select(DisputeEvidence).where(DisputeEvidence.dispute_id == dispute.id)
    ).scalars().all()
    
    # Get comments (exclude internal notes for non-admins)
    comments = db.execute(
        select(DisputeComment).where(
            DisputeComment.dispute_id == dispute.id,
            DisputeComment.is_internal == False,
        ).order_by(DisputeComment.created_at.asc())
    ).scalars().all()
    
    return DisputeDetailResponse(
        dispute=DisputeResponse(
            id=dispute.id,
            case_number=dispute.case_number,
            payment_id=dispute.payment_id,
            user_id=dispute.user_id,
            merchant_id=dispute.merchant_id,
            amount=dispute.amount,
            currency=dispute.currency,
            reason=dispute.reason,
            description=dispute.description,
            status=dispute.status,
            priority=dispute.priority,
            assigned_to=dispute.assigned_to,
            response_due_by=dispute.response_due_by,
            resolved_at=dispute.resolved_at,
            resolution_type=dispute.resolution_type,
            resolution_amount=dispute.resolution_amount,
            resolution_notes=dispute.resolution_notes,
            created_at=dispute.created_at,
            updated_at=dispute.updated_at,
        ),
        evidence=[
            DisputeEvidenceResponse(
                id=e.id,
                dispute_id=e.dispute_id,
                uploaded_by=e.uploaded_by,
                uploader_type=e.uploader_type,
                file_name=e.file_name,
                file_size=e.file_size,
                mime_type=e.mime_type,
                description=e.description,
                evidence_type=e.evidence_type,
                uploaded_at=e.uploaded_at,
            )
            for e in evidence
        ],
        comments=[
            DisputeCommentResponse(
                id=c.id,
                dispute_id=c.dispute_id,
                author_id=c.author_id,
                author_type=c.author_type,
                message=c.message,
                is_internal=c.is_internal,
                created_at=c.created_at,
            )
            for c in comments
        ],
    )


@router.post("/{dispute_id}/evidence", response_model=DisputeEvidenceResponse, summary="Upload evidence")
async def upload_evidence(
    dispute_id: int,
    evidence_type: str = Query(..., description="Type: receipt, screenshot, communication, other"),
    description: Optional[str] = Query(None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisputeEvidenceResponse:
    """Upload supporting evidence for a dispute."""
    dispute = db.scalar(
        select(Dispute).where(
            Dispute.id == dispute_id,
            Dispute.user_id == user.id,
        )
    )
    
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found.",
        )
    
    if dispute.status in [DisputeStatus.CLOSED.value, DisputeStatus.WITHDRAWN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add evidence to a closed dispute.",
        )
    
    # Validate file
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )
    
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB",
        )
    
    # Save file
    ext = Path(file.filename).suffix if file.filename else ".bin"
    unique_name = f"{dispute.case_number}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = EVIDENCE_DIR / unique_name
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    evidence = DisputeEvidence(
        dispute_id=dispute.id,
        uploaded_by=user.id,
        uploader_type="user",
        file_name=file.filename or unique_name,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type,
        description=description,
        evidence_type=evidence_type,
    )
    db.add(evidence)
    
    # Add system comment
    comment = DisputeComment(
        dispute_id=dispute.id,
        author_id=user.id,
        author_type="system",
        message=f"Evidence uploaded: {file.filename} ({evidence_type})",
    )
    db.add(comment)
    
    db.commit()
    db.refresh(evidence)
    
    return DisputeEvidenceResponse(
        id=evidence.id,
        dispute_id=evidence.dispute_id,
        uploaded_by=evidence.uploaded_by,
        uploader_type=evidence.uploader_type,
        file_name=evidence.file_name,
        file_size=evidence.file_size,
        mime_type=evidence.mime_type,
        description=evidence.description,
        evidence_type=evidence.evidence_type,
        uploaded_at=evidence.uploaded_at,
    )


@router.post("/{dispute_id}/comments", response_model=DisputeCommentResponse, summary="Add comment")
def add_comment(
    dispute_id: int,
    request: DisputeCommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisputeCommentResponse:
    """Add a comment to a dispute."""
    dispute = db.scalar(
        select(Dispute).where(
            Dispute.id == dispute_id,
            Dispute.user_id == user.id,
        )
    )
    
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found.",
        )
    
    if dispute.status in [DisputeStatus.CLOSED.value, DisputeStatus.WITHDRAWN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot comment on a closed dispute.",
        )
    
    comment = DisputeComment(
        dispute_id=dispute.id,
        author_id=user.id,
        author_type="user",
        message=request.message,
        is_internal=False,  # Users cannot create internal notes
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return DisputeCommentResponse(
        id=comment.id,
        dispute_id=comment.dispute_id,
        author_id=comment.author_id,
        author_type=comment.author_type,
        message=comment.message,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )


@router.post("/{dispute_id}/withdraw", response_model=DisputeResponse, summary="Withdraw dispute")
def withdraw_dispute(
    dispute_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisputeResponse:
    """Withdraw a dispute."""
    dispute = db.scalar(
        select(Dispute).where(
            Dispute.id == dispute_id,
            Dispute.user_id == user.id,
        )
    )
    
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found.",
        )
    
    if dispute.status in [DisputeStatus.CLOSED.value, DisputeStatus.WITHDRAWN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dispute is already closed.",
        )
    
    dispute.status = DisputeStatus.WITHDRAWN.value
    dispute.resolved_at = datetime.utcnow()
    
    comment = DisputeComment(
        dispute_id=dispute.id,
        author_id=user.id,
        author_type="system",
        message="Dispute withdrawn by user.",
    )
    db.add(comment)
    
    db.commit()
    db.refresh(dispute)
    
    return DisputeResponse(
        id=dispute.id,
        case_number=dispute.case_number,
        payment_id=dispute.payment_id,
        user_id=dispute.user_id,
        merchant_id=dispute.merchant_id,
        amount=dispute.amount,
        currency=dispute.currency,
        reason=dispute.reason,
        description=dispute.description,
        status=dispute.status,
        priority=dispute.priority,
        resolved_at=dispute.resolved_at,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
    )


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/admin/all", response_model=DisputeListResponse, summary="List all disputes (admin)")
def list_all_disputes(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> DisputeListResponse:
    """List all disputes for admin review."""
    query = select(Dispute)
    count_query = select(func.count(Dispute.id))
    
    if status_filter:
        query = query.where(Dispute.status == status_filter)
        count_query = count_query.where(Dispute.status == status_filter)
    
    if priority_filter:
        query = query.where(Dispute.priority == priority_filter)
        count_query = count_query.where(Dispute.priority == priority_filter)
    
    total = db.scalar(count_query)
    
    disputes = db.execute(
        query.order_by(Dispute.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    
    return DisputeListResponse(
        items=[
            DisputeResponse(
                id=d.id,
                case_number=d.case_number,
                payment_id=d.payment_id,
                user_id=d.user_id,
                merchant_id=d.merchant_id,
                amount=d.amount,
                currency=d.currency,
                reason=d.reason,
                description=d.description,
                status=d.status,
                priority=d.priority,
                assigned_to=d.assigned_to,
                response_due_by=d.response_due_by,
                resolved_at=d.resolved_at,
                resolution_type=d.resolution_type,
                resolution_amount=d.resolution_amount,
                resolution_notes=d.resolution_notes,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in disputes
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.patch("/admin/{dispute_id}", response_model=DisputeResponse, summary="Update dispute (admin)")
async def update_dispute(
    dispute_id: int,
    request: DisputeUpdateRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> DisputeResponse:
    """Update dispute status, priority, or resolution."""
    dispute = db.scalar(select(Dispute).where(Dispute.id == dispute_id))
    
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispute not found.",
        )
    
    if request.status:
        old_status = dispute.status
        dispute.status = request.status
        
        # Check if resolved
        if request.status in [
            DisputeStatus.RESOLVED_FOR_USER.value,
            DisputeStatus.RESOLVED_FOR_MERCHANT.value,
            DisputeStatus.CLOSED.value,
        ]:
            dispute.resolved_at = datetime.utcnow()
            dispute.resolved_by = admin.id
        
        # Add status change comment
        comment = DisputeComment(
            dispute_id=dispute.id,
            author_id=admin.id,
            author_type="admin",
            message=f"Status changed from {old_status} to {request.status}",
            is_internal=True,
        )
        db.add(comment)
    
    if request.priority:
        dispute.priority = request.priority
    
    if request.assigned_to is not None:
        dispute.assigned_to = request.assigned_to
    
    if request.resolution_type:
        dispute.resolution_type = request.resolution_type
    
    if request.resolution_amount is not None:
        dispute.resolution_amount = request.resolution_amount
    
    if request.resolution_notes:
        dispute.resolution_notes = request.resolution_notes
    
    db.commit()
    db.refresh(dispute)
    
    # Notify user of status change
    if request.status:
        user = db.scalar(select(User).where(User.id == dispute.user_id))
        if user:
            email_service.send_dispute_update(
                to=user.email,
                name=user.full_name,
                case_number=dispute.case_number,
                status=dispute.status,
                message=request.resolution_notes or f"Your dispute status has been updated to: {dispute.status}",
            )
        
        # Send webhook
        if dispute.merchant_id:
            event_type = "dispute.resolved" if dispute.resolved_at else "dispute.updated"
            await webhook_service.dispatch_event(
                db=db,
                merchant_id=dispute.merchant_id,
                event_type=event_type,
                data={
                    "dispute_id": dispute.id,
                    "case_number": dispute.case_number,
                    "status": dispute.status,
                    "resolution_type": dispute.resolution_type,
                },
            )
    
    return DisputeResponse(
        id=dispute.id,
        case_number=dispute.case_number,
        payment_id=dispute.payment_id,
        user_id=dispute.user_id,
        merchant_id=dispute.merchant_id,
        amount=dispute.amount,
        currency=dispute.currency,
        reason=dispute.reason,
        description=dispute.description,
        status=dispute.status,
        priority=dispute.priority,
        assigned_to=dispute.assigned_to,
        response_due_by=dispute.response_due_by,
        resolved_at=dispute.resolved_at,
        resolution_type=dispute.resolution_type,
        resolution_amount=dispute.resolution_amount,
        resolution_notes=dispute.resolution_notes,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
    )
