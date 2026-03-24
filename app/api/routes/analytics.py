from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.credit import CreditAccount
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.schemas.analytics import SpendingCategoryItem, SpendingSummaryResponse


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spending-summary", response_model=SpendingSummaryResponse)
def spending_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SpendingSummaryResponse:
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.user_id == user.id,
            Transaction.created_at >= month_start,
            Transaction.status.in_([TransactionStatus.approved, TransactionStatus.flagged]),
        )
    )

    category_rows = db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user.id,
            Transaction.created_at >= month_start,
            Transaction.status.in_([TransactionStatus.approved, TransactionStatus.flagged]),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()

    account = db.scalar(select(CreditAccount).where(CreditAccount.user_id == user.id))
    utilization_pct = 0.0
    if account and account.credit_limit > 0:
        utilized = account.credit_limit - account.available_credit
        utilization_pct = round((utilized / account.credit_limit) * 100.0, 2)

    return SpendingSummaryResponse(
        month_total=round(float(month_total or 0.0), 2),
        utilization_pct=utilization_pct,
        by_category=[
            SpendingCategoryItem(category=row[0], total_amount=round(float(row[1] or 0.0), 2)) for row in category_rows
        ],
    )
