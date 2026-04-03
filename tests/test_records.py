"""
Tests for Financial Records CRUD API.

Covers:
- Create, read, update, delete operations
- Ownership enforcement
- Filtering and pagination
- Soft delete behavior
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.record import FinancialRecord, RecordType, RecordStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def seed_analyst(db: Session):
    """Create an analyst user and return (user, jwt_token)."""
    def _create(
        email: str = "analyst@example.com",
        full_name: str = "Analyst User",
    ):
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password("AnalystPass123!"),
            role=UserRole.ANALYST.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(subject=user.email)
        return user, token
    return _create


@pytest.fixture()
def seed_viewer(db: Session):
    """Create a viewer user and return (user, jwt_token)."""
    def _create(
        email: str = "viewer@example.com",
        full_name: str = "Viewer User",
    ):
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password("ViewerPass123!"),
            role=UserRole.VIEWER.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(subject=user.email)
        return user, token
    return _create


@pytest.fixture()
def analyst_headers(seed_analyst):
    """Create analyst and return headers."""
    user, token = seed_analyst()
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture()
def viewer_headers(seed_viewer):
    """Create viewer and return headers."""
    user, token = seed_viewer()
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture()
def sample_record_data():
    """Sample record creation data."""
    return {
        "amount": 150.50,
        "type": "expense",
        "category": "food",
        "description": "Lunch at restaurant",
        "record_date": str(date.today()),
    }


# ---------------------------------------------------------------------------
# Create Record Tests
# ---------------------------------------------------------------------------
class TestCreateRecord:
    """Tests for POST /api/v1/records endpoint."""

    def test_create_record_success(self, client: TestClient, analyst_headers, sample_record_data):
        """Analyst can create a record."""
        headers, user = analyst_headers
        response = client.post("/api/v1/records", json=sample_record_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "150.50"
        assert data["type"] == "expense"
        assert data["category"] == "food"
        assert data["user_id"] == user.id
        assert data["status"] == "active"
        assert data["is_deleted"] is False

    def test_create_income_record(self, client: TestClient, analyst_headers):
        """Can create income record."""
        headers, _ = analyst_headers
        data = {
            "amount": 5000.00,
            "type": "income",
            "category": "salary",
            "description": "Monthly salary",
            "record_date": str(date.today()),
        }
        response = client.post("/api/v1/records", json=data, headers=headers)
        
        assert response.status_code == 201
        assert response.json()["type"] == "income"

    def test_create_record_viewer_forbidden(self, client: TestClient, viewer_headers, sample_record_data):
        """Viewer cannot create records."""
        headers, _ = viewer_headers
        response = client.post("/api/v1/records", json=sample_record_data, headers=headers)
        
        assert response.status_code == 403
        assert "Analyst privileges required" in response.json()["detail"]

    def test_create_record_unauthenticated(self, client: TestClient, sample_record_data):
        """Unauthenticated request is rejected."""
        response = client.post("/api/v1/records", json=sample_record_data)
        assert response.status_code == 401

    def test_create_record_invalid_amount(self, client: TestClient, analyst_headers):
        """Invalid amount is rejected."""
        headers, _ = analyst_headers
        data = {
            "amount": -50,
            "type": "expense",
            "category": "food",
            "record_date": str(date.today()),
        }
        response = client.post("/api/v1/records", json=data, headers=headers)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Read Record Tests
# ---------------------------------------------------------------------------
class TestGetRecord:
    """Tests for GET /api/v1/records/{id} endpoint."""

    def test_get_record_success(self, client: TestClient, analyst_headers, sample_record_data):
        """Can retrieve own record."""
        headers, _ = analyst_headers
        create_resp = client.post("/api/v1/records", json=sample_record_data, headers=headers)
        record_id = create_resp.json()["id"]
        
        response = client.get(f"/api/v1/records/{record_id}", headers=headers)
        
        assert response.status_code == 200
        assert response.json()["id"] == record_id

    def test_get_record_not_found(self, client: TestClient, analyst_headers):
        """Non-existent record returns 404."""
        headers, _ = analyst_headers
        response = client.get("/api/v1/records/99999", headers=headers)
        assert response.status_code == 404

    def test_get_other_user_record_not_found(self, client: TestClient, analyst_headers, seed_analyst, db):
        """Cannot access another user's record."""
        headers, user1 = analyst_headers
        
        # Create record for user1
        record = FinancialRecord(
            user_id=user1.id,
            amount=Decimal("100"),
            type=RecordType.EXPENSE.value,
            category="food",
            record_date=date.today(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        # Create another analyst
        user2, token2 = seed_analyst(email="analyst2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # user2 cannot see user1's record
        response = client.get(f"/api/v1/records/{record.id}", headers=headers2)
        assert response.status_code == 404

    def test_viewer_can_read_records(self, client: TestClient, viewer_headers, db):
        """Viewer can read their own records."""
        headers, user = viewer_headers
        
        # Create record for viewer
        record = FinancialRecord(
            user_id=user.id,
            amount=Decimal("100"),
            type=RecordType.EXPENSE.value,
            category="food",
            record_date=date.today(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        response = client.get(f"/api/v1/records/{record.id}", headers=headers)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# List Records Tests
# ---------------------------------------------------------------------------
class TestListRecords:
    """Tests for GET /api/v1/records endpoint."""

    def test_list_records_empty(self, client: TestClient, analyst_headers):
        """Empty list when no records."""
        headers, _ = analyst_headers
        response = client.get("/api/v1/records", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["total_items"] == 0

    def test_list_records_with_data(self, client: TestClient, analyst_headers, db):
        """List returns user's records."""
        headers, user = analyst_headers
        
        # Create multiple records
        for i in range(5):
            record = FinancialRecord(
                user_id=user.id,
                amount=Decimal(str(100 + i * 10)),
                type=RecordType.EXPENSE.value,
                category="food",
                record_date=date.today() - timedelta(days=i),
            )
            db.add(record)
        db.commit()
        
        response = client.get("/api/v1/records", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["pagination"]["total_items"] == 5

    def test_list_records_filter_by_type(self, client: TestClient, analyst_headers, db):
        """Can filter by record type."""
        headers, user = analyst_headers
        
        # Create income and expense records
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("500"), type="income", category="salary", record_date=date.today()))
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today()))
        db.commit()
        
        response = client.get("/api/v1/records?type=income", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "income"

    def test_list_records_filter_by_category(self, client: TestClient, analyst_headers, db):
        """Can filter by category."""
        headers, user = analyst_headers
        
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today()))
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("100"), type="expense", category="transportation", record_date=date.today()))
        db.commit()
        
        response = client.get("/api/v1/records?category=food", headers=headers)
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    def test_list_records_filter_by_date_range(self, client: TestClient, analyst_headers, db):
        """Can filter by date range."""
        headers, user = analyst_headers
        today = date.today()
        
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=today))
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("100"), type="expense", category="food", record_date=today - timedelta(days=30)))
        db.commit()
        
        response = client.get(f"/api/v1/records?date_from={today}", headers=headers)
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    def test_list_records_pagination(self, client: TestClient, analyst_headers, db):
        """Pagination works correctly."""
        headers, user = analyst_headers
        
        # Create 25 records
        for i in range(25):
            db.add(FinancialRecord(user_id=user.id, amount=Decimal("10"), type="expense", category="food", record_date=date.today()))
        db.commit()
        
        # Get first page
        response = client.get("/api/v1/records?page=1&per_page=10", headers=headers)
        data = response.json()
        
        assert len(data["items"]) == 10
        assert data["pagination"]["total_items"] == 25
        assert data["pagination"]["total_pages"] == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False

    def test_list_excludes_deleted(self, client: TestClient, analyst_headers, db):
        """Soft-deleted records excluded by default."""
        headers, user = analyst_headers
        
        db.add(FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today()))
        deleted = FinancialRecord(user_id=user.id, amount=Decimal("100"), type="expense", category="food", record_date=date.today(), is_deleted=True)
        db.add(deleted)
        db.commit()
        
        response = client.get("/api/v1/records", headers=headers)
        assert len(response.json()["items"]) == 1
        
        # Include deleted
        response = client.get("/api/v1/records?include_deleted=true", headers=headers)
        assert len(response.json()["items"]) == 2


# ---------------------------------------------------------------------------
# Update Record Tests
# ---------------------------------------------------------------------------
class TestUpdateRecord:
    """Tests for PUT /api/v1/records/{id} endpoint."""

    def test_update_record_success(self, client: TestClient, analyst_headers, sample_record_data):
        """Can update own record."""
        headers, _ = analyst_headers
        create_resp = client.post("/api/v1/records", json=sample_record_data, headers=headers)
        record_id = create_resp.json()["id"]
        
        update_data = {"amount": 200.00, "description": "Updated description"}
        response = client.put(f"/api/v1/records/{record_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == "200.00"
        assert data["description"] == "Updated description"

    def test_update_record_viewer_forbidden(self, client: TestClient, viewer_headers, db):
        """Viewer cannot update records."""
        headers, user = viewer_headers
        
        record = FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today())
        db.add(record)
        db.commit()
        db.refresh(record)
        
        response = client.put(f"/api/v1/records/{record.id}", json={"amount": 100}, headers=headers)
        assert response.status_code == 403

    def test_update_nonexistent_record(self, client: TestClient, analyst_headers):
        """Updating non-existent record returns 404."""
        headers, _ = analyst_headers
        response = client.put("/api/v1/records/99999", json={"amount": 100}, headers=headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Record Tests
# ---------------------------------------------------------------------------
class TestDeleteRecord:
    """Tests for DELETE /api/v1/records/{id} endpoint."""

    def test_delete_record_success(self, client: TestClient, analyst_headers, sample_record_data):
        """Can soft-delete own record."""
        headers, _ = analyst_headers
        create_resp = client.post("/api/v1/records", json=sample_record_data, headers=headers)
        record_id = create_resp.json()["id"]
        
        response = client.delete(f"/api/v1/records/{record_id}", headers=headers)
        assert response.status_code == 204
        
        # Record should not be visible
        get_resp = client.get(f"/api/v1/records/{record_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_delete_record_viewer_forbidden(self, client: TestClient, viewer_headers, db):
        """Viewer cannot delete records."""
        headers, user = viewer_headers
        
        record = FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today())
        db.add(record)
        db.commit()
        db.refresh(record)
        
        response = client.delete(f"/api/v1/records/{record.id}", headers=headers)
        assert response.status_code == 403

    def test_delete_nonexistent_record(self, client: TestClient, analyst_headers):
        """Deleting non-existent record returns 404."""
        headers, _ = analyst_headers
        response = client.delete("/api/v1/records/99999", headers=headers)
        assert response.status_code == 404
