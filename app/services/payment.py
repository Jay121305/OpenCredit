"""
Payment Processing Service
==========================

This module orchestrates the complete payment flow including:
- Fraud detection and scoring
- Credit limit validation
- Transaction creation
- Ledger block recording
- Webhook event publishing

Payment Flow:
    1. Validate merchant is active
    2. Check idempotency key (prevent duplicate charges)
    3. Lock credit account (SELECT FOR UPDATE)
    4. Run fraud detection → score and decision
    5. Check credit limit if not rejected
    6. Deduct from available credit
    7. Create transaction record
    8. Create ledger block (hash-chained audit)
    9. Publish webhook event
    10. Return result

Idempotency:
    Each payment requires a unique idempotency_key. If the same key is
    submitted twice, the original transaction is returned without
    creating a duplicate charge.
"""

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
    """
    Orchestrates payment processing with fraud detection and ledger recording.
    
    Attributes:
        fraud_engine: ML-powered fraud detection engine
        event_bus: Webhook event publisher
    """
    
    def __init__(self, fraud_engine: FraudEngine, event_bus: EventBus) -> None:
        """Initialize with fraud engine and event bus dependencies."""
        self.fraud_engine = fraud_engine
        self.event_bus = event_bus

    def process(self, db: Session, user_id: int, merchant: Merchant, req: PaymentRequest) -> Transaction:
        """
        Process a payment request through the complete payment flow.
        
        Args:
            db: Database session (will be modified, caller must commit)
            user_id: ID of the user making the payment
            merchant: Merchant receiving the payment
            req: Payment request with amount, currency, etc.
            
        Returns:
            Transaction: The created (or existing if idempotent) transaction
            
        Raises:
            ValueError: If merchant inactive or credit account not found
            
        Side Effects:
            - Deducts from user's available credit (if approved/flagged)
            - Creates transaction record
            - Creates ledger block
            - Publishes webhook event
        """
        # Step 1: Validate merchant
        if not merchant.is_active:
            raise ValueError("Merchant is inactive")

        # Step 2: Idempotency check - return existing transaction if duplicate
        existing = db.scalar(select(Transaction).where(Transaction.idempotency_key == req.idempotency_key))
        if existing:
            return existing

        # Step 3: Lock credit account for atomic update
        account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update())
        if not account:
            raise ValueError("Credit account not found")

        # Step 4: Fraud detection - get risk score and decision
        fraud = self.fraud_engine.evaluate(db=db, user_id=user_id, amount=req.amount, geo=req.geo)
        status = TransactionStatus(fraud.decision)

        # Step 5: Credit limit check (only if not already rejected by fraud)
        if status in {TransactionStatus.approved, TransactionStatus.flagged} and account.available_credit < req.amount:
            status = TransactionStatus.rejected

        # Step 6: Deduct from available credit (if approved or flagged)
        if status in {TransactionStatus.approved, TransactionStatus.flagged}:
            account.available_credit -= req.amount

        # Step 7: Create transaction record

        # Step 7: Create transaction record
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
        db.flush()  # Get tx.id without committing

        # Step 8: Create hash-chained ledger block for audit trail
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
        
        # Step 9: Publish webhook event (async, non-blocking)
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
