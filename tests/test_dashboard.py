"""
Tests for Dashboard Analytics API.

Covers:
- Summary calculations
- Category breakdown accuracy
- Trend data format
- Date range filtering
- Recent activity
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.record import FinancialRecord, RecordType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def analyst_with_records(db: Session):
    """Create analyst with sample records and return (user, headers)."""
    user = User(
        email="dashboard_analyst@example.com",
        full_name="Dashboard Analyst",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.ANALYST.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Add sample records
    today = date.today()
    records = [
        # Income
        FinancialRecord(user_id=user.id, amount=Decimal("5000"), type="income", category="salary", record_date=today),
        FinancialRecord(user_id=user.id, amount=Decimal("500"), type="income", category="freelance", record_date=today - timedelta(days=5)),
        # Expenses
        FinancialRecord(user_id=user.id, amount=Decimal("200"), type="expense", category="food", record_date=today),
        FinancialRecord(user_id=user.id, amount=Decimal("150"), type="expense", category="food", record_date=today - timedelta(days=2)),
        FinancialRecord(user_id=user.id, amount=Decimal("100"), type="expense", category="transportation", record_date=today - timedelta(days=3)),
        FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="entertainment", record_date=today - timedelta(days=10)),
    ]
    db.add_all(records)
    db.commit()
    
    token = create_access_token(subject=user.email)
    return user, {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Summary Tests
# ---------------------------------------------------------------------------
class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary endpoint."""

    def test_summary_empty(self, client: TestClient, create_user_with_role):
        """Summary with no records returns zeros."""
        from tests.test_roles import create_user_with_role as _  # Import fixture
        
    def test_summary_calculations(self, client: TestClient, analyst_with_records):
        """Summary calculations are accurate."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/summary", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Total income: 5000 + 500 = 5500
        assert Decimal(data["total_income"]) == Decimal("5500")
        
        # Total expenses: 200 + 150 + 100 + 50 = 500
        assert Decimal(data["total_expenses"]) == Decimal("500")
        
        # Net balance: 5500 - 500 = 5000
        assert Decimal(data["net_balance"]) == Decimal("5000")
        
        # Counts
        assert data["total_records"] == 6
        assert data["income_count"] == 2
        assert data["expense_count"] == 4

    def test_summary_with_date_filter(self, client: TestClient, analyst_with_records):
        """Summary respects date filters."""
        user, headers = analyst_with_records
        today = date.today()
        
        # Filter to today only
        response = client.get(f"/api/v1/dashboard/summary?date_from={today}&date_to={today}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Only today's records: 5000 income, 200 expense
        assert Decimal(data["total_income"]) == Decimal("5000")
        assert Decimal(data["total_expenses"]) == Decimal("200")


# ---------------------------------------------------------------------------
# Category Breakdown Tests
# ---------------------------------------------------------------------------
class TestCategoryBreakdown:
    """Tests for GET /api/v1/dashboard/categories endpoint."""

    def test_expense_breakdown(self, client: TestClient, analyst_with_records):
        """Expense category breakdown is accurate."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/categories?type=expense", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["type"] == "expense"
        assert Decimal(data["total"]) == Decimal("500")
        
        # Check categories
        categories = {c["category"]: c for c in data["categories"]}
        
        # Food: 200 + 150 = 350 (70%)
        assert Decimal(categories["food"]["total"]) == Decimal("350")
        assert categories["food"]["count"] == 2
        
        # Transportation: 100 (20%)
        assert Decimal(categories["transportation"]["total"]) == Decimal("100")
        
        # Entertainment: 50 (10%)
        assert Decimal(categories["entertainment"]["total"]) == Decimal("50")

    def test_income_breakdown(self, client: TestClient, analyst_with_records):
        """Income category breakdown is accurate."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/categories?type=income", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["type"] == "income"
        categories = {c["category"]: c for c in data["categories"]}
        
        assert Decimal(categories["salary"]["total"]) == Decimal("5000")
        assert Decimal(categories["freelance"]["total"]) == Decimal("500")

    def test_breakdown_percentages(self, client: TestClient, analyst_with_records):
        """Category percentages sum to ~100%."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/categories?type=expense", headers=headers)
        
        data = response.json()
        total_percentage = sum(Decimal(c["percentage"]) for c in data["categories"])
        
        # Should be approximately 100% (allowing for rounding)
        assert Decimal("99") <= total_percentage <= Decimal("101")


# ---------------------------------------------------------------------------
# Trends Tests
# ---------------------------------------------------------------------------
class TestTrends:
    """Tests for GET /api/v1/dashboard/trends endpoint."""

    def test_monthly_trends(self, client: TestClient, analyst_with_records):
        """Monthly trends return correct format."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/trends?granularity=monthly", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["granularity"] == "monthly"
        assert "data_points" in data
        assert len(data["data_points"]) > 0
        
        # Check data point structure
        point = data["data_points"][0]
        assert "date" in point
        assert "income" in point
        assert "expenses" in point
        assert "net" in point
        assert "record_count" in point

    def test_daily_trends(self, client: TestClient, analyst_with_records):
        """Daily trends return correct format."""
        user, headers = analyst_with_records
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        response = client.get(
            f"/api/v1/dashboard/trends?granularity=daily&date_from={week_ago}&date_to={today}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["granularity"] == "daily"
        # Should have data points for each day
        assert len(data["data_points"]) >= 7

    def test_weekly_trends(self, client: TestClient, analyst_with_records):
        """Weekly trends return correct format."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/trends?granularity=weekly", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["granularity"] == "weekly"

    def test_trends_totals(self, client: TestClient, analyst_with_records):
        """Trends include correct totals."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/trends?granularity=monthly", headers=headers)
        
        data = response.json()
        
        # Totals should match sum of data points
        total_income = sum(Decimal(p["income"]) for p in data["data_points"])
        total_expenses = sum(Decimal(p["expenses"]) for p in data["data_points"])
        
        assert Decimal(data["total_income"]) == total_income
        assert Decimal(data["total_expenses"]) == total_expenses


# ---------------------------------------------------------------------------
# Recent Activity Tests
# ---------------------------------------------------------------------------
class TestRecentActivity:
    """Tests for GET /api/v1/dashboard/recent endpoint."""

    def test_recent_activity_default(self, client: TestClient, analyst_with_records):
        """Recent activity returns latest records."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/recent", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "records" in data
        assert "total_count" in data
        assert data["total_count"] == 6
        assert len(data["records"]) <= 10  # Default limit

    def test_recent_activity_limit(self, client: TestClient, analyst_with_records):
        """Recent activity respects limit parameter."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/recent?limit=3", headers=headers)
        
        data = response.json()
        assert len(data["records"]) == 3

    def test_recent_activity_order(self, client: TestClient, analyst_with_records):
        """Recent activity is sorted by created_at desc."""
        user, headers = analyst_with_records
        response = client.get("/api/v1/dashboard/recent?limit=6", headers=headers)
        
        data = response.json()
        records = data["records"]
        
        # Check descending order by created_at
        for i in range(len(records) - 1):
            assert records[i]["created_at"] >= records[i + 1]["created_at"]

    def test_recent_excludes_deleted(self, client: TestClient, analyst_with_records, db):
        """Recent activity excludes soft-deleted records."""
        user, headers = analyst_with_records
        
        # Add a deleted record
        deleted = FinancialRecord(
            user_id=user.id,
            amount=Decimal("999"),
            type="expense",
            category="deleted",
            record_date=date.today(),
            is_deleted=True,
        )
        db.add(deleted)
        db.commit()
        
        response = client.get("/api/v1/dashboard/recent?limit=50", headers=headers)
        
        data = response.json()
        # Should not include the deleted record
        categories = [r["category"] for r in data["records"]]
        assert "deleted" not in categories


# ---------------------------------------------------------------------------
# Empty State Tests
# ---------------------------------------------------------------------------
class TestEmptyDashboard:
    """Tests for dashboard with no data."""

    def test_empty_summary(self, client: TestClient, db):
        """Summary returns zeros with no records."""
        user = User(
            email="empty@example.com",
            full_name="Empty User",
            password_hash=hash_password("TestPass123!"),
            role=UserRole.ANALYST.value,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(subject=user.email)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/dashboard/summary", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["total_income"]) == Decimal("0")
        assert Decimal(data["total_expenses"]) == Decimal("0")
        assert data["total_records"] == 0

    def test_empty_categories(self, client: TestClient, db):
        """Category breakdown returns empty list with no records."""
        user = User(
            email="empty2@example.com",
            full_name="Empty User",
            password_hash=hash_password("TestPass123!"),
            role=UserRole.ANALYST.value,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(subject=user.email)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/dashboard/categories", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["categories"] == []
        assert Decimal(data["total"]) == Decimal("0")
