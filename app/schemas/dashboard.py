"""
Dashboard analytics schemas for summaries, breakdowns, and trends.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    """Overall financial summary for the dashboard."""
    
    total_income: Decimal = Field(
        ...,
        description="Total income amount",
        json_schema_extra={"example": 5000.00}
    )
    total_expenses: Decimal = Field(
        ...,
        description="Total expenses amount",
        json_schema_extra={"example": 3500.00}
    )
    net_balance: Decimal = Field(
        ...,
        description="Net balance (income - expenses)",
        json_schema_extra={"example": 1500.00}
    )
    total_records: int = Field(
        ...,
        description="Total number of records",
        json_schema_extra={"example": 42}
    )
    income_count: int = Field(
        ...,
        description="Number of income records",
        json_schema_extra={"example": 5}
    )
    expense_count: int = Field(
        ...,
        description="Number of expense records",
        json_schema_extra={"example": 37}
    )
    period_start: Optional[date] = Field(
        None,
        description="Start of the period"
    )
    period_end: Optional[date] = Field(
        None,
        description="End of the period"
    )


class CategoryTotal(BaseModel):
    """Spending/income total for a single category."""
    
    category: str = Field(
        ...,
        description="Category name",
        json_schema_extra={"example": "food"}
    )
    total: Decimal = Field(
        ...,
        description="Total amount in this category",
        json_schema_extra={"example": 450.00}
    )
    count: int = Field(
        ...,
        description="Number of records in this category",
        json_schema_extra={"example": 15}
    )
    percentage: Decimal = Field(
        ...,
        description="Percentage of total",
        json_schema_extra={"example": 12.5}
    )


class CategoryBreakdown(BaseModel):
    """Category breakdown for expenses or income."""
    
    type: str = Field(
        ...,
        description="Record type (income or expense)",
        json_schema_extra={"example": "expense"}
    )
    total: Decimal = Field(
        ...,
        description="Total amount across all categories",
        json_schema_extra={"example": 3500.00}
    )
    categories: list[CategoryTotal] = Field(
        ...,
        description="Breakdown by category"
    )
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class TrendPoint(BaseModel):
    """Single data point in a trend series."""
    
    date: str = Field(
        ...,
        description="Date or period label",
        json_schema_extra={"example": "2026-04"}
    )
    income: Decimal = Field(
        ...,
        description="Income for this period",
        json_schema_extra={"example": 5000.00}
    )
    expenses: Decimal = Field(
        ...,
        description="Expenses for this period",
        json_schema_extra={"example": 3500.00}
    )
    net: Decimal = Field(
        ...,
        description="Net amount for this period",
        json_schema_extra={"example": 1500.00}
    )
    record_count: int = Field(
        ...,
        description="Number of records",
        json_schema_extra={"example": 12}
    )


class TrendData(BaseModel):
    """Time-series trend data."""
    
    granularity: str = Field(
        ...,
        description="Time granularity: daily, weekly, or monthly",
        json_schema_extra={"example": "monthly"}
    )
    data_points: list[TrendPoint] = Field(
        ...,
        description="Trend data points"
    )
    period_start: date = Field(
        ...,
        description="Start of trend period"
    )
    period_end: date = Field(
        ...,
        description="End of trend period"
    )
    total_income: Decimal = Field(
        ...,
        description="Total income across period"
    )
    total_expenses: Decimal = Field(
        ...,
        description="Total expenses across period"
    )


class RecentRecord(BaseModel):
    """Simplified record for recent activity display."""
    
    id: int
    amount: Decimal
    type: str
    category: str
    description: Optional[str]
    record_date: date
    created_at: str

    model_config = {"from_attributes": True}


class RecentActivity(BaseModel):
    """Recent activity for dashboard."""
    
    records: list[RecentRecord] = Field(
        ...,
        description="Recent financial records"
    )
    total_count: int = Field(
        ...,
        description="Total number of records (not just recent)"
    )


class DateRangeParams(BaseModel):
    """Common date range parameters for dashboard queries."""
    
    date_from: Optional[date] = Field(
        None,
        description="Start date for filtering"
    )
    date_to: Optional[date] = Field(
        None,
        description="End date for filtering"
    )


class TrendParams(BaseModel):
    """Parameters for trend data queries."""
    
    date_from: Optional[date] = Field(
        None,
        description="Start date"
    )
    date_to: Optional[date] = Field(
        None,
        description="End date"
    )
    granularity: str = Field(
        "monthly",
        pattern="^(daily|weekly|monthly)$",
        description="Time granularity"
    )
