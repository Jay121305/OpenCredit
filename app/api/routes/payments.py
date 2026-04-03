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
