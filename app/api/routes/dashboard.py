"""
Dashboard Analytics API routes.

Endpoints:
- GET /dashboard/summary     Overall financial summary (viewer+)
- GET /dashboard/categories  Category breakdown (analyst+)
- GET /dashboard/trends      Time-series trends (analyst+)
- GET /dashboard/recent      Recent activity (viewer+)
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_analyst_user, get_current_viewer_user
from app.db.session import get_db
from app.models.record import RecordType
from app.models.user import User
from app.schemas.dashboard import (
    CategoryBreakdown,
    DashboardSummary,
    RecentActivity,
    TrendData,
)
from app.services.dashboard import DashboardService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """Dependency to get DashboardService instance."""
    return DashboardService(db)


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get financial summary",
    description="Get overall financial summary including total income, expenses, and net balance. Requires viewer role or higher.",
)
def get_summary(
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    user: User = Depends(get_current_viewer_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    """Get overall financial summary for dashboard."""
    return service.get_summary(user.id, date_from, date_to)


@router.get(
    "/categories",
    response_model=CategoryBreakdown,
    summary="Get category breakdown",
    description="Get spending or income breakdown by category with percentages. Requires analyst role or higher.",
)
def get_category_breakdown(
    type: RecordType = Query(RecordType.EXPENSE, description="Record type to analyze"),
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    user: User = Depends(get_current_analyst_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> CategoryBreakdown:
    """Get category breakdown for expenses or income."""
    return service.get_category_breakdown(user.id, type, date_from, date_to)


@router.get(
    "/trends",
    response_model=TrendData,
    summary="Get financial trends",
    description="Get time-series trend data for income and expenses. Requires analyst role or higher.",
)
def get_trends(
    date_from: Optional[date] = Query(None, description="Start date (defaults based on granularity)"),
    date_to: Optional[date] = Query(None, description="End date (defaults to today)"),
    granularity: str = Query(
        "monthly",
        pattern="^(daily|weekly|monthly)$",
        description="Time granularity: daily, weekly, or monthly",
    ),
    user: User = Depends(get_current_analyst_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> TrendData:
    """Get time-series trend data."""
    return service.get_trends(user.id, date_from, date_to, granularity)


@router.get(
    "/recent",
    response_model=RecentActivity,
    summary="Get recent activity",
    description="Get most recent financial records. Requires viewer role or higher.",
)
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of records to return"),
    user: User = Depends(get_current_viewer_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> RecentActivity:
    """Get recent financial activity."""
    return service.get_recent_activity(user.id, limit)
