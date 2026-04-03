"""
Dashboard analytics service for summaries, breakdowns, and trends.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.orm import Session

from app.models.record import FinancialRecord, RecordStatus, RecordType
from app.schemas.dashboard import (
    CategoryBreakdown,
    CategoryTotal,
    DashboardSummary,
    RecentActivity,
    RecentRecord,
    TrendData,
    TrendPoint,
)


class DashboardService:
    """Service for dashboard analytics and summaries."""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self,
        user_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> DashboardSummary:
        """
        Get overall financial summary for dashboard.
        
        Args:
            user_id: User ID
            date_from: Optional start date filter
            date_to: Optional end date filter
            
        Returns:
            DashboardSummary with totals and counts
        """
        # Base conditions
        conditions = [
            FinancialRecord.user_id == user_id,
            FinancialRecord.is_deleted == False,
            FinancialRecord.status == RecordStatus.ACTIVE.value,
        ]

        if date_from:
            conditions.append(FinancialRecord.record_date >= date_from)
        if date_to:
            conditions.append(FinancialRecord.record_date <= date_to)

        # Query aggregates
        query = select(
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.INCOME.value, FinancialRecord.amount),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_income"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialRecord.type == RecordType.EXPENSE.value, FinancialRecord.amount),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_expenses"),
            func.count().label("total_records"),
            func.sum(
                case(
                    (FinancialRecord.type == RecordType.INCOME.value, 1),
                    else_=0,
                )
            ).label("income_count"),
            func.sum(
                case(
                    (FinancialRecord.type == RecordType.EXPENSE.value, 1),
                    else_=0,
                )
            ).label("expense_count"),
        ).where(and_(*conditions))

        result = self.db.execute(query).first()

        total_income = Decimal(str(result.total_income or 0))
        total_expenses = Decimal(str(result.total_expenses or 0))

        return DashboardSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net_balance=total_income - total_expenses,
            total_records=result.total_records or 0,
            income_count=result.income_count or 0,
            expense_count=result.expense_count or 0,
            period_start=date_from,
            period_end=date_to,
        )

    def get_category_breakdown(
        self,
        user_id: int,
        record_type: RecordType = RecordType.EXPENSE,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> CategoryBreakdown:
        """
        Get spending/income breakdown by category.
        
        Args:
            user_id: User ID
            record_type: Type of records to analyze (income or expense)
            date_from: Optional start date
            date_to: Optional end date
            
        Returns:
            CategoryBreakdown with category totals and percentages
        """
        conditions = [
            FinancialRecord.user_id == user_id,
            FinancialRecord.is_deleted == False,
            FinancialRecord.status == RecordStatus.ACTIVE.value,
            FinancialRecord.type == record_type.value,
        ]

        if date_from:
            conditions.append(FinancialRecord.record_date >= date_from)
        if date_to:
            conditions.append(FinancialRecord.record_date <= date_to)

        # Query category aggregates
        query = (
            select(
                FinancialRecord.category,
                func.sum(FinancialRecord.amount).label("total"),
                func.count().label("count"),
            )
            .where(and_(*conditions))
            .group_by(FinancialRecord.category)
            .order_by(func.sum(FinancialRecord.amount).desc())
        )

        results = self.db.execute(query).all()

        # Calculate grand total for percentages
        grand_total = sum(Decimal(str(r.total or 0)) for r in results)
        
        categories = []
        for r in results:
            total = Decimal(str(r.total or 0))
            percentage = (total / grand_total * 100) if grand_total > 0 else Decimal("0")
            categories.append(
                CategoryTotal(
                    category=r.category,
                    total=total,
                    count=r.count,
                    percentage=round(percentage, 2),
                )
            )

        return CategoryBreakdown(
            type=record_type.value,
            total=grand_total,
            categories=categories,
            period_start=date_from,
            period_end=date_to,
        )

    def get_trends(
        self,
        user_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        granularity: str = "monthly",
    ) -> TrendData:
        """
        Get time-series trend data.
        
        Args:
            user_id: User ID
            date_from: Start date (defaults to 6 months ago)
            date_to: End date (defaults to today)
            granularity: daily, weekly, or monthly
            
        Returns:
            TrendData with data points over time
        """
        # Default date range
        if not date_to:
            date_to = date.today()
        if not date_from:
            if granularity == "daily":
                date_from = date_to - timedelta(days=30)
            elif granularity == "weekly":
                date_from = date_to - timedelta(weeks=12)
            else:  # monthly
                date_from = date_to - timedelta(days=180)

        conditions = [
            FinancialRecord.user_id == user_id,
            FinancialRecord.is_deleted == False,
            FinancialRecord.status == RecordStatus.ACTIVE.value,
            FinancialRecord.record_date >= date_from,
            FinancialRecord.record_date <= date_to,
        ]

        # Get all records in range
        query = select(FinancialRecord).where(and_(*conditions))
        records = list(self.db.scalars(query).all())

        # Group by period
        data_points = self._aggregate_by_period(records, granularity, date_from, date_to)

        total_income = sum(p.income for p in data_points)
        total_expenses = sum(p.expenses for p in data_points)

        return TrendData(
            granularity=granularity,
            data_points=data_points,
            period_start=date_from,
            period_end=date_to,
            total_income=total_income,
            total_expenses=total_expenses,
        )

    def _aggregate_by_period(
        self,
        records: list[FinancialRecord],
        granularity: str,
        date_from: date,
        date_to: date,
    ) -> list[TrendPoint]:
        """Aggregate records by time period."""
        
        def get_period_key(d: date) -> str:
            if granularity == "daily":
                return d.isoformat()
            elif granularity == "weekly":
                # ISO week
                return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
            else:  # monthly
                return f"{d.year}-{d.month:02d}"

        # Initialize buckets
        period_data = defaultdict(lambda: {"income": Decimal("0"), "expenses": Decimal("0"), "count": 0})

        # Aggregate records
        for record in records:
            key = get_period_key(record.record_date)
            if record.type == RecordType.INCOME.value:
                period_data[key]["income"] += record.amount
            elif record.type == RecordType.EXPENSE.value:
                period_data[key]["expenses"] += record.amount
            period_data[key]["count"] += 1

        # Generate all periods in range
        all_periods = self._generate_period_keys(date_from, date_to, granularity)

        # Build result
        data_points = []
        for period_key in all_periods:
            data = period_data.get(period_key, {"income": Decimal("0"), "expenses": Decimal("0"), "count": 0})
            data_points.append(
                TrendPoint(
                    date=period_key,
                    income=data["income"],
                    expenses=data["expenses"],
                    net=data["income"] - data["expenses"],
                    record_count=data["count"],
                )
            )

        return data_points

    def _generate_period_keys(self, date_from: date, date_to: date, granularity: str) -> list[str]:
        """Generate all period keys in date range."""
        keys = []
        current = date_from

        while current <= date_to:
            if granularity == "daily":
                keys.append(current.isoformat())
                current += timedelta(days=1)
            elif granularity == "weekly":
                keys.append(f"{current.isocalendar()[0]}-W{current.isocalendar()[1]:02d}")
                current += timedelta(weeks=1)
            else:  # monthly
                keys.append(f"{current.year}-{current.month:02d}")
                # Move to next month
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)

        # Remove duplicates while preserving order
        seen = set()
        unique_keys = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                unique_keys.append(k)

        return unique_keys

    def get_recent_activity(self, user_id: int, limit: int = 10) -> RecentActivity:
        """
        Get recent financial activity.
        
        Args:
            user_id: User ID
            limit: Max number of records to return (default 10)
            
        Returns:
            RecentActivity with recent records
        """
        # Get recent records
        query = (
            select(FinancialRecord)
            .where(
                and_(
                    FinancialRecord.user_id == user_id,
                    FinancialRecord.is_deleted == False,
                )
            )
            .order_by(FinancialRecord.created_at.desc())
            .limit(limit)
        )
        records = list(self.db.scalars(query).all())

        # Get total count
        count_query = select(func.count()).where(
            and_(
                FinancialRecord.user_id == user_id,
                FinancialRecord.is_deleted == False,
            )
        )
        total_count = self.db.scalar(count_query) or 0

        return RecentActivity(
            records=[
                RecentRecord(
                    id=r.id,
                    amount=r.amount,
                    type=r.type,
                    category=r.category,
                    description=r.description,
                    record_date=r.record_date,
                    created_at=r.created_at.isoformat() if r.created_at else "",
                )
                for r in records
            ],
            total_count=total_count,
        )


def get_dashboard_service(db: Session) -> DashboardService:
    """Factory function to create DashboardService instance."""
    return DashboardService(db)
