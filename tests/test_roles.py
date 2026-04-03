"""
Tests for Role-Based Access Control.

Covers:
- Viewer role restrictions
- Analyst role permissions
- Admin role permissions
- Deactivated user blocking
- Role hierarchy enforcement
"""

import pytest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.record import FinancialRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def create_user_with_role(db: Session):
    """Factory to create users with specific roles."""
    def _create(role: UserRole, email: str = None):
        email = email or f"{role.value}@example.com"
        user = User(
            email=email,
            full_name=f"{role.value.title()} User",
            password_hash=hash_password("TestPass123!"),
            role=role.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(subject=user.email)
        return user, {"Authorization": f"Bearer {token}"}
    return _create


# ---------------------------------------------------------------------------
# Viewer Role Tests
# ---------------------------------------------------------------------------
class TestViewerRole:
    """Tests for viewer role restrictions."""

    def test_viewer_can_access_dashboard_summary(self, client: TestClient, create_user_with_role):
        """Viewer can access dashboard summary."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        response = client.get("/api/v1/dashboard/summary", headers=headers)
        assert response.status_code == 200

    def test_viewer_can_access_recent_activity(self, client: TestClient, create_user_with_role):
        """Viewer can access recent activity."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        response = client.get("/api/v1/dashboard/recent", headers=headers)
        assert response.status_code == 200

    def test_viewer_cannot_access_categories(self, client: TestClient, create_user_with_role):
        """Viewer cannot access category breakdown (analyst+)."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        response = client.get("/api/v1/dashboard/categories", headers=headers)
        assert response.status_code == 403

    def test_viewer_cannot_access_trends(self, client: TestClient, create_user_with_role):
        """Viewer cannot access trends (analyst+)."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        response = client.get("/api/v1/dashboard/trends", headers=headers)
        assert response.status_code == 403

    def test_viewer_can_list_records(self, client: TestClient, create_user_with_role):
        """Viewer can list records."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        response = client.get("/api/v1/records", headers=headers)
        assert response.status_code == 200

    def test_viewer_cannot_create_record(self, client: TestClient, create_user_with_role):
        """Viewer cannot create records."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        data = {"amount": 100, "type": "expense", "category": "food", "record_date": str(date.today())}
        response = client.post("/api/v1/records", json=data, headers=headers)
        assert response.status_code == 403

    def test_viewer_cannot_update_record(self, client: TestClient, create_user_with_role, db):
        """Viewer cannot update records."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        
        record = FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today())
        db.add(record)
        db.commit()
        
        response = client.put(f"/api/v1/records/{record.id}", json={"amount": 100}, headers=headers)
        assert response.status_code == 403

    def test_viewer_cannot_delete_record(self, client: TestClient, create_user_with_role, db):
        """Viewer cannot delete records."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        
        record = FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today())
        db.add(record)
        db.commit()
        
        response = client.delete(f"/api/v1/records/{record.id}", headers=headers)
        assert response.status_code == 403

    def test_viewer_cannot_access_user_management(self, client: TestClient, create_user_with_role):
        """Viewer cannot access user management."""
        user, headers = create_user_with_role(UserRole.VIEWER)
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Analyst Role Tests
# ---------------------------------------------------------------------------
class TestAnalystRole:
    """Tests for analyst role permissions."""

    def test_analyst_can_access_all_dashboard(self, client: TestClient, create_user_with_role):
        """Analyst can access all dashboard endpoints."""
        user, headers = create_user_with_role(UserRole.ANALYST)
        
        assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 200
        assert client.get("/api/v1/dashboard/categories", headers=headers).status_code == 200
        assert client.get("/api/v1/dashboard/trends", headers=headers).status_code == 200
        assert client.get("/api/v1/dashboard/recent", headers=headers).status_code == 200

    def test_analyst_can_create_record(self, client: TestClient, create_user_with_role):
        """Analyst can create records."""
        user, headers = create_user_with_role(UserRole.ANALYST)
        data = {"amount": 100, "type": "expense", "category": "food", "record_date": str(date.today())}
        response = client.post("/api/v1/records", json=data, headers=headers)
        assert response.status_code == 201

    def test_analyst_can_update_record(self, client: TestClient, create_user_with_role, db):
        """Analyst can update records."""
        user, headers = create_user_with_role(UserRole.ANALYST)
        
        record = FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today())
        db.add(record)
        db.commit()
        db.refresh(record)
        
        response = client.put(f"/api/v1/records/{record.id}", json={"amount": 100}, headers=headers)
        assert response.status_code == 200

    def test_analyst_can_delete_record(self, client: TestClient, create_user_with_role, db):
        """Analyst can delete records."""
        user, headers = create_user_with_role(UserRole.ANALYST)
        
        record = FinancialRecord(user_id=user.id, amount=Decimal("50"), type="expense", category="food", record_date=date.today())
        db.add(record)
        db.commit()
        db.refresh(record)
        
        response = client.delete(f"/api/v1/records/{record.id}", headers=headers)
        assert response.status_code == 204

    def test_analyst_cannot_access_user_management(self, client: TestClient, create_user_with_role):
        """Analyst cannot access user management."""
        user, headers = create_user_with_role(UserRole.ANALYST)
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Admin Role Tests
# ---------------------------------------------------------------------------
class TestAdminRole:
    """Tests for admin role permissions."""

    def test_admin_can_access_all_dashboard(self, client: TestClient, create_user_with_role):
        """Admin can access all dashboard endpoints."""
        user, headers = create_user_with_role(UserRole.ADMIN)
        
        assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 200
        assert client.get("/api/v1/dashboard/categories", headers=headers).status_code == 200
        assert client.get("/api/v1/dashboard/trends", headers=headers).status_code == 200
        assert client.get("/api/v1/dashboard/recent", headers=headers).status_code == 200

    def test_admin_can_manage_records(self, client: TestClient, create_user_with_role):
        """Admin can perform all record operations."""
        user, headers = create_user_with_role(UserRole.ADMIN)
        
        # Create
        data = {"amount": 100, "type": "expense", "category": "food", "record_date": str(date.today())}
        create_resp = client.post("/api/v1/records", json=data, headers=headers)
        assert create_resp.status_code == 201
        record_id = create_resp.json()["id"]
        
        # Read
        assert client.get(f"/api/v1/records/{record_id}", headers=headers).status_code == 200
        
        # Update
        assert client.put(f"/api/v1/records/{record_id}", json={"amount": 200}, headers=headers).status_code == 200
        
        # Delete
        assert client.delete(f"/api/v1/records/{record_id}", headers=headers).status_code == 204

    def test_admin_can_access_user_management(self, client: TestClient, create_user_with_role):
        """Admin can access user management."""
        user, headers = create_user_with_role(UserRole.ADMIN)
        
        assert client.get("/api/v1/users", headers=headers).status_code == 200
        assert client.get("/api/v1/users/stats", headers=headers).status_code == 200


# ---------------------------------------------------------------------------
# Deactivated User Tests
# ---------------------------------------------------------------------------
class TestDeactivatedUser:
    """Tests for deactivated user blocking."""

    def test_deactivated_user_cannot_access_api(self, client: TestClient, db):
        """Deactivated user is blocked from all endpoints."""
        user = User(
            email="deactivated@example.com",
            full_name="Deactivated User",
            password_hash=hash_password("TestPass123!"),
            role=UserRole.ANALYST.value,
            is_active=False,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(subject=user.email)
        headers = {"Authorization": f"Bearer {token}"}
        
        # All endpoints should return 403
        assert client.get("/api/v1/records", headers=headers).status_code == 403
        assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 403

    def test_deactivated_admin_cannot_access_api(self, client: TestClient, db):
        """Deactivated admin is blocked from all endpoints."""
        user = User(
            email="deactivated-admin@example.com",
            full_name="Deactivated Admin",
            password_hash=hash_password("TestPass123!"),
            role=UserRole.ADMIN.value,
            is_active=False,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(subject=user.email)
        headers = {"Authorization": f"Bearer {token}"}
        
        assert client.get("/api/v1/users", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# Role Hierarchy Tests
# ---------------------------------------------------------------------------
class TestRoleHierarchy:
    """Tests for role hierarchy enforcement."""

    def test_higher_role_inherits_lower_permissions(self, client: TestClient, create_user_with_role):
        """Higher roles can do everything lower roles can."""
        # Analyst can do viewer things
        analyst, analyst_headers = create_user_with_role(UserRole.ANALYST, "analyst_hier@example.com")
        assert client.get("/api/v1/dashboard/summary", headers=analyst_headers).status_code == 200
        assert client.get("/api/v1/records", headers=analyst_headers).status_code == 200
        
        # Admin can do analyst things
        admin, admin_headers = create_user_with_role(UserRole.ADMIN, "admin_hier@example.com")
        data = {"amount": 100, "type": "expense", "category": "food", "record_date": str(date.today())}
        assert client.post("/api/v1/records", json=data, headers=admin_headers).status_code == 201
        assert client.get("/api/v1/dashboard/categories", headers=admin_headers).status_code == 200

    def test_standard_user_has_viewer_access(self, client: TestClient, create_user_with_role):
        """Standard user role has at least viewer access level."""
        user, headers = create_user_with_role(UserRole.USER)
        
        # Can read dashboard
        assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 200
        assert client.get("/api/v1/records", headers=headers).status_code == 200
        
        # Cannot create records (below analyst)
        data = {"amount": 100, "type": "expense", "category": "food", "record_date": str(date.today())}
        assert client.post("/api/v1/records", json=data, headers=headers).status_code == 403
