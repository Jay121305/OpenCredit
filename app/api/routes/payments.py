"""
Payment Processing API Routes
=============================

Endpoints for processing payments with ML fraud detection.

Flow:
    1. Client sends POST /api/v1/payments with amount, currency, etc.
    2. Requires both JWT token (user auth) and X-API-Key header (merchant auth)
    3. Fraud engine scores transaction (0.0-1.0)
    4. Transaction created with status: approved/flagged/rejected
    5. Ledger block appended (hash-chained audit trail)
    6. Response includes transaction_id, status, fraud_score, remaining credit

Example Request:
    POST /api/v1/payments
    Headers:
        Authorization: Bearer <jwt_token>
        X-API-Key: oc_live_xxxxx
    Body:
        {
            "amount": 150.00,
            "currency": "USD",
            "category": "food",
            "geo": "US",
            "idempotency_key": "unique-123"
        }
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
import traceback

from app.api.deps import get_current_user, get_merchant_by_api_key
from app.db.session import get_db
from app.models.credit import CreditAccount
from app.models.merchant import Merchant
from app.models.user import User
from app.schemas.payment import PaymentRequest, PaymentResponse
from app.services.event_bus import EventBus
from app.services.fraud import FraudEngine
from app.services.payment import PaymentService


router = APIRouter(prefix="/payments", tags=["payments"])

# Initialize services (singleton instances)
fraud_engine = FraudEngine()
event_bus = EventBus()
payment_service = PaymentService(fraud_engine=fraud_engine, event_bus=event_bus)


@router.post("", response_model=PaymentResponse)
def create_payment(
    payload: PaymentRequest,
    user: User = Depends(get_current_user),
    merchant: Merchant = Depends(get_merchant_by_api_key),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """
    Process a payment with ML fraud detection.
    
    Requires:
        - JWT token in Authorization header (user authentication)
        - X-API-Key header (merchant authentication)
        
    The payment flows through fraud detection, credit limit check,
    and creates an immutable ledger block for audit purposes.
    
    Returns:
        PaymentResponse with transaction_id, status, fraud_score, and remaining credit
        
    Raises:
        400: Merchant inactive or credit account not found
        401: Invalid authentication
        500: Processing error
    """
    try:
        tx = payment_service.process(db=db, user_id=user.id, merchant=merchant, req=payload)
        db.commit()
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user.id))
        return PaymentResponse(
            transaction_id=tx.id,
            status=tx.status.value,
            fraud_score=tx.fraud_score,
            available_credit=account.available_credit if account else 0.0,
            created_at=tx.created_at,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        print(f"Payment error: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(exc)}") from exc
