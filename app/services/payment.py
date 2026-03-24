from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.credit import CreditAccount
from app.models.merchant import Merchant
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.payment import PaymentRequest
from app.services.event_bus import EventBus
from app.services.fraud import FraudEngine
from app.services.ledger import LedgerService


class PaymentService:
    def __init__(self, fraud_engine: FraudEngine, event_bus: EventBus) -> None:
        self.fraud_engine = fraud_engine
        self.event_bus = event_bus

    def process(self, db: Session, user_id: int, merchant: Merchant, req: PaymentRequest) -> Transaction:
        if not merchant.is_active:
            raise ValueError("Merchant is inactive")

        existing = db.scalar(select(Transaction).where(Transaction.idempotency_key == req.idempotency_key))
        if existing:
            return existing

        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update())
        if not account:
            raise ValueError("Credit account not found")

        fraud = self.fraud_engine.evaluate(db=db, user_id=user_id, amount=req.amount, geo=req.geo)
        status = TransactionStatus(fraud.decision)

        if status in {TransactionStatus.approved, TransactionStatus.flagged} and account.available_credit < req.amount:
            status = TransactionStatus.rejected

        if status in {TransactionStatus.approved, TransactionStatus.flagged}:
            account.available_credit -= req.amount

        tx = Transaction(
            user_id=user_id,
            merchant_id=merchant.id,
            amount=req.amount,
            currency=req.currency.upper(),
            category=req.category.lower(),
            geo=req.geo.upper(),
            status=status,
            fraud_score=fraud.score,
            idempotency_key=req.idempotency_key,
        )
        db.add(tx)
        db.flush()

        LedgerService.append_block(
            db,
            tx_id=tx.id,
            payload={
                "user_id": user_id,
                "merchant_id": merchant.id,
                "amount": req.amount,
                "currency": req.currency,
                "status": status.value,
                "fraud_score": fraud.score,
            },
        )
        self.event_bus.publish_transaction(
            {
                "transaction_id": str(tx.id),
                "user_id": str(tx.user_id),
                "merchant_id": str(tx.merchant_id),
                "amount": str(tx.amount),
                "status": tx.status.value,
                "category": tx.category,
            }
        )
        return tx
