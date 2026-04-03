"""
Refund and Chargeback API routes.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_admin_user
from app.db.session import get_db
from app.models.refund import Refund, Chargeback, RefundStatus, RefundType, ChargebackStatus
from app.models.transaction import Transaction as Payment
from app.models.user import User
from app.services.email import email_service
from app.services.webhooks import webhook_service
from app.schemas.refund import (
    RefundCreateRequest,
    RefundResponse,
    RefundProcessRequest,
    RefundListResponse,
    ChargebackCreateRequest,
    ChargebackResponse,
    ChargebackUpdateRequest,
    ChargebackListResponse,
)


router = APIRouter(prefix="/refunds", tags=["refunds"])


# ============================================================================
# Refund Endpoints
# ============================================================================

@router.post("", response_model=RefundResponse, summary="Request a refund")
async def create_refund(
    request: RefundCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RefundResponse:
    """
    Request a refund for a payment.
    
    - Full refund if amount not specified
    - Partial refund if amount is less than payment amount
    """
    # Get payment
    payment = db.scalar(select(Payment).where(Payment.id == request.payment_id))
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    
    # Check ownership (user can only refund their own payments)
    if payment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only request refunds for your own payments.",
        )
    
    # Check if already refunded
    existing_refund = db.scalar(
        select(Refund).where(
            Refund.payment_id == payment.id,
            Refund.status.in_([RefundStatus.PENDING.value, RefundStatus.APPROVED.value, RefundStatus.COMPLETED.value])
        )
    )
    
    if existing_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A refund already exists for this payment.",
        )
    
    # Determine refund amount
    refund_amount = request.amount if request.amount else payment.amount
    refund_type = RefundType.PARTIAL.value if request.amount and request.amount < payment.amount else RefundType.FULL.value
    
    if refund_amount > payment.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount cannot exceed payment amount.",
        )
    
    # Create refund
    refund = Refund(
        payment_id=payment.id,
        merchant_id=payment.merchant_id,
        user_id=user.id,
        amount=refund_amount,
        currency="USD",
        refund_type=refund_type,
        reason=request.reason,
        description=request.description,
        status=RefundStatus.PENDING.value,
        reference_id=f"REF-{uuid.uuid4().hex[:12].upper()}",
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    
    # Send webhook
    if payment.merchant_id:
        await webhook_service.dispatch_event(
            db=db,
            merchant_id=payment.merchant_id,
            event_type="payment.refund_requested",
            data={
                "refund_id": refund.id,
                "payment_id": payment.id,
                "amount": str(refund.amount),
                "reason": refund.reason,
            },
        )
    
    return RefundResponse(
        id=refund.id,
        payment_id=refund.payment_id,
        merchant_id=refund.merchant_id,
        user_id=refund.user_id,
        amount=refund.amount,
        currency=refund.currency,
        refund_type=refund.refund_type,
        reason=refund.reason,
        description=refund.description,
        status=refund.status,
        reference_id=refund.reference_id,
        created_at=refund.created_at,
    )


@router.get("", response_model=RefundListResponse, summary="List refunds")
def list_refunds(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RefundListResponse:
    """List refunds for the current user."""
    query = select(Refund).where(Refund.user_id == user.id)
    count_query = select(func.count(Refund.id)).where(Refund.user_id == user.id)
    
    if status_filter:
        query = query.where(Refund.status == status_filter)
        count_query = count_query.where(Refund.status == status_filter)
    
    total = db.scalar(count_query)
    
    refunds = db.execute(
        query.order_by(Refund.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    
    return RefundListResponse(
        items=[
            RefundResponse(
                id=r.id,
                payment_id=r.payment_id,
                merchant_id=r.merchant_id,
                user_id=r.user_id,
                amount=r.amount,
                currency=r.currency,
                refund_type=r.refund_type,
                reason=r.reason,
                description=r.description,
                status=r.status,
                processed_at=r.processed_at,
                rejection_reason=r.rejection_reason,
                reference_id=r.reference_id,
                created_at=r.created_at,
            )
            for r in refunds
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{refund_id}", response_model=RefundResponse, summary="Get refund details")
def get_refund(
    refund_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RefundResponse:
    """Get details of a specific refund."""
    refund = db.scalar(
        select(Refund).where(
            Refund.id == refund_id,
            Refund.user_id == user.id,
        )
    )
    
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    
    return RefundResponse(
        id=refund.id,
        payment_id=refund.payment_id,
        merchant_id=refund.merchant_id,
        user_id=refund.user_id,
        amount=refund.amount,
        currency=refund.currency,
        refund_type=refund.refund_type,
        reason=refund.reason,
        description=refund.description,
        status=refund.status,
        processed_at=refund.processed_at,
        rejection_reason=refund.rejection_reason,
        reference_id=refund.reference_id,
        created_at=refund.created_at,
    )


# ============================================================================
# Admin Refund Endpoints
# ============================================================================

@router.get("/admin/pending", response_model=RefundListResponse, summary="List pending refunds (admin)")
def list_pending_refunds(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> RefundListResponse:
    """List all pending refunds for admin review."""
    total = db.scalar(
        select(func.count(Refund.id)).where(Refund.status == RefundStatus.PENDING.value)
    )
    
    refunds = db.execute(
        select(Refund)
        .where(Refund.status == RefundStatus.PENDING.value)
        .order_by(Refund.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    
    return RefundListResponse(
        items=[
            RefundResponse(
                id=r.id,
                payment_id=r.payment_id,
                merchant_id=r.merchant_id,
                user_id=r.user_id,
                amount=r.amount,
                currency=r.currency,
                refund_type=r.refund_type,
                reason=r.reason,
                description=r.description,
                status=r.status,
                processed_at=r.processed_at,
                rejection_reason=r.rejection_reason,
                reference_id=r.reference_id,
                created_at=r.created_at,
            )
            for r in refunds
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/{refund_id}/process", response_model=RefundResponse, summary="Process refund (admin)")
async def process_refund(
    refund_id: int,
    request: RefundProcessRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> RefundResponse:
    """
    Process (approve or reject) a refund request.
    
    If approved, the refund will be processed and the user's credit restored.
    """
    refund = db.scalar(select(Refund).where(Refund.id == refund_id))
    
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    
    if refund.status != RefundStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process refund with status: {refund.status}",
        )
    
    if request.action == "reject":
        if not request.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required.",
            )
        refund.status = RefundStatus.REJECTED.value
        refund.rejection_reason = request.rejection_reason
    elif request.action == "approve":
        refund.status = RefundStatus.COMPLETED.value
        
        # TODO: Restore credit to user's account
        # This would involve updating the credit_account balance
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'.",
        )
    
    refund.processed_by = admin.id
    refund.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(refund)
    
    # Send notification
    user = db.scalar(select(User).where(User.id == refund.user_id))
    if user:
        # TODO: Send email notification about refund status
        pass
    
    # Send webhook
    if refund.merchant_id:
        event_type = "payment.refunded" if request.action == "approve" else "payment.refund_rejected"
        await webhook_service.dispatch_event(
            db=db,
            merchant_id=refund.merchant_id,
            event_type=event_type,
            data={
                "refund_id": refund.id,
                "payment_id": refund.payment_id,
                "amount": str(refund.amount),
                "status": refund.status,
            },
        )
    
    return RefundResponse(
        id=refund.id,
        payment_id=refund.payment_id,
        merchant_id=refund.merchant_id,
        user_id=refund.user_id,
        amount=refund.amount,
        currency=refund.currency,
        refund_type=refund.refund_type,
        reason=refund.reason,
        description=refund.description,
        status=refund.status,
        processed_at=refund.processed_at,
        rejection_reason=refund.rejection_reason,
        reference_id=refund.reference_id,
        created_at=refund.created_at,
    )


# ============================================================================
# Chargeback Endpoints (Admin only)
# ============================================================================

chargeback_router = APIRouter(prefix="/chargebacks", tags=["chargebacks"])


@chargeback_router.post("", response_model=ChargebackResponse, summary="Record a chargeback")
def create_chargeback(
    request: ChargebackCreateRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ChargebackResponse:
    """
    Record a new chargeback received from the bank.
    
    This is typically used when a customer disputes a charge with their bank.
    """
    payment = db.scalar(select(Payment).where(Payment.id == request.payment_id))
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    
    # Check for existing chargeback
    existing = db.scalar(
        select(Chargeback).where(Chargeback.payment_id == payment.id)
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A chargeback already exists for this payment.",
        )
    
    chargeback = Chargeback(
        payment_id=payment.id,
        merchant_id=payment.merchant_id,
        user_id=payment.user_id,
        amount=request.amount,
        currency="USD",
        reason_code=request.reason_code,
        reason_description=request.reason_description,
        bank_reference=request.bank_reference,
        evidence_due_by=request.evidence_due_by,
        status=ChargebackStatus.RECEIVED.value,
    )
    db.add(chargeback)
    db.commit()
    db.refresh(chargeback)
    
    return ChargebackResponse(
        id=chargeback.id,
        payment_id=chargeback.payment_id,
        merchant_id=chargeback.merchant_id,
        user_id=chargeback.user_id,
        amount=chargeback.amount,
        currency=chargeback.currency,
        reason_code=chargeback.reason_code,
        reason_description=chargeback.reason_description,
        status=chargeback.status,
        evidence_due_by=chargeback.evidence_due_by,
        evidence_submitted=chargeback.evidence_submitted,
        bank_reference=chargeback.bank_reference,
        received_at=chargeback.received_at,
        created_at=chargeback.created_at,
    )


@chargeback_router.get("", response_model=ChargebackListResponse, summary="List chargebacks")
def list_chargebacks(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ChargebackListResponse:
    """List all chargebacks."""
    query = select(Chargeback)
    count_query = select(func.count(Chargeback.id))
    
    if status_filter:
        query = query.where(Chargeback.status == status_filter)
        count_query = count_query.where(Chargeback.status == status_filter)
    
    total = db.scalar(count_query)
    
    chargebacks = db.execute(
        query.order_by(Chargeback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    
    return ChargebackListResponse(
        items=[
            ChargebackResponse(
                id=c.id,
                payment_id=c.payment_id,
                merchant_id=c.merchant_id,
                user_id=c.user_id,
                amount=c.amount,
                currency=c.currency,
                reason_code=c.reason_code,
                reason_description=c.reason_description,
                status=c.status,
                evidence_due_by=c.evidence_due_by,
                evidence_submitted=c.evidence_submitted,
                resolved_at=c.resolved_at,
                fee_amount=c.fee_amount,
                recovered_amount=c.recovered_amount,
                bank_reference=c.bank_reference,
                received_at=c.received_at,
                created_at=c.created_at,
            )
            for c in chargebacks
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@chargeback_router.patch("/{chargeback_id}", response_model=ChargebackResponse, summary="Update chargeback")
def update_chargeback(
    chargeback_id: int,
    request: ChargebackUpdateRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ChargebackResponse:
    """Update a chargeback status or evidence."""
    chargeback = db.scalar(select(Chargeback).where(Chargeback.id == chargeback_id))
    
    if not chargeback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chargeback not found.",
        )
    
    if request.status:
        chargeback.status = request.status
        if request.status in [ChargebackStatus.WON.value, ChargebackStatus.LOST.value, ChargebackStatus.ACCEPTED.value]:
            chargeback.resolved_at = datetime.utcnow()
            chargeback.resolved_by = admin.id
    
    if request.evidence_details:
        chargeback.evidence_details = request.evidence_details
        chargeback.evidence_submitted = True
    
    if request.resolution_notes:
        chargeback.resolution_notes = request.resolution_notes
    
    db.commit()
    db.refresh(chargeback)
    
    return ChargebackResponse(
        id=chargeback.id,
        payment_id=chargeback.payment_id,
        merchant_id=chargeback.merchant_id,
        user_id=chargeback.user_id,
        amount=chargeback.amount,
        currency=chargeback.currency,
        reason_code=chargeback.reason_code,
        reason_description=chargeback.reason_description,
        status=chargeback.status,
        evidence_due_by=chargeback.evidence_due_by,
        evidence_submitted=chargeback.evidence_submitted,
        resolved_at=chargeback.resolved_at,
        fee_amount=chargeback.fee_amount,
        recovered_amount=chargeback.recovered_amount,
        bank_reference=chargeback.bank_reference,
        received_at=chargeback.received_at,
        created_at=chargeback.created_at,
    )
