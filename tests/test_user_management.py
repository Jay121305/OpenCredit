"""
Tests for User Management API (Admin only).

Covers:
- List users with filtering
- User statistics
- Role assignment
- Activate/deactivate users
- Self-protection rules
"""

import pytest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def admin_user(db: Session):
    """Create admin user and return (user, headers)."""
    user = User(
        email="admin_mgmt@example.com",
        full_name="Admin Manager",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.email)
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_users(db: Session):
    """Create sample users of different roles."""
    users = [
        User(email="viewer1@example.com", full_name="Viewer One", password_hash=hash_password("Pass123!"), role=UserRole.VIEWER.value),
        User(email="viewer2@example.com", full_name="Viewer Two", password_hash=hash_password("Pass123!"), role=UserRole.VIEWER.value, is_active=False),
        User(email="analyst1@example.com", full_name="Analyst One", password_hash=hash_password("Pass123!"), role=UserRole.ANALYST.value),
        User(email="user1@example.com", full_name="User One", password_hash=hash_password("Pass123!"), role=UserRole.USER.value),
    ]
    db.add_all(users)
    db.commit()
    for u in users:
        db.refresh(u)
    return users


# ---------------------------------------------------------------------------
# List Users Tests
# ---------------------------------------------------------------------------
class TestListUsers:
    """Tests for GET /api/v1/users endpoint."""

    def test_list_users_success(self, client: TestClient, admin_user, sample_users):
        """Admin can list all users."""
        admin, headers = admin_user
        response = client.get("/api/v1/users", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 4 sample users + 1 admin
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_list_users_filter_by_role(self, client: TestClient, admin_user, sample_users):
        """Can filter users by role."""
        admin, headers = admin_user
        response = client.get("/api/v1/users?role=viewer", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(u["role"] == "viewer" for u in data["items"])

    def test_list_users_filter_by_active(self, client: TestClient, admin_user, sample_users):
        """Can filter users by active status."""
        admin, headers = admin_user
        
        # Active users
        response = client.get("/api/v1/users?is_active=true", headers=headers)
        data = response.json()
        assert all(u["is_active"] for u in data["items"])
        
        # Inactive users
        response = client.get("/api/v1/users?is_active=false", headers=headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "viewer2@example.com"

    def test_list_users_search(self, client: TestClient, admin_user, sample_users):
        """Can search users by email or name."""
        admin, headers = admin_user
        response = client.get("/api/v1/users?search=analyst", headers=headers)
        
        data = response.json()
        assert data["total"] == 1
        assert "analyst" in data["items"][0]["email"]

    def test_list_users_pagination(self, client: TestClient, admin_user, sample_users):
        """Pagination works correctly."""
        admin, headers = admin_user
        response = client.get("/api/v1/users?page=1&per_page=2", headers=headers)
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3

    def test_list_users_non_admin_forbidden(self, client: TestClient, db):
        """Non-admin cannot list users."""
        user = User(
            email="notadmin@example.com",
            full_name="Not Admin",
            password_hash=hash_password("Pass123!"),
            role=UserRole.ANALYST.value,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(subject=user.email)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# User Stats Tests
# ---------------------------------------------------------------------------
class TestUserStats:
    """Tests for GET /api/v1/users/stats endpoint."""

    def test_user_stats(self, client: TestClient, admin_user, sample_users):
        """Stats returns correct counts."""
        admin, headers = admin_user
        response = client.get("/api/v1/users/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5  # 4 sample + 1 admin
        assert data["active"] == 4  # 1 inactive
        assert data["inactive"] == 1
        assert "by_role" in data


# ---------------------------------------------------------------------------
# Get User Tests
# ---------------------------------------------------------------------------
class TestGetUser:
    """Tests for GET /api/v1/users/{id} endpoint."""

    def test_get_user_success(self, client: TestClient, admin_user, sample_users):
        """Admin can get user details."""
        admin, headers = admin_user
        target_user = sample_users[0]
        
        response = client.get(f"/api/v1/users/{target_user.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == target_user.email

    def test_get_user_not_found(self, client: TestClient, admin_user):
        """Non-existent user returns 404."""
        admin, headers = admin_user
        response = client.get("/api/v1/users/99999", headers=headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update Role Tests
# ---------------------------------------------------------------------------
class TestUpdateRole:
    """Tests for PATCH /api/v1/users/{id}/role endpoint."""

    def test_update_role_success(self, client: TestClient, admin_user, sample_users):
        """Admin can change user role."""
        admin, headers = admin_user
        target_user = sample_users[0]  # viewer
        
        response = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            json={"role": "analyst"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "analyst"

    def test_update_to_admin(self, client: TestClient, admin_user, sample_users):
        """Can promote user to admin."""
        admin, headers = admin_user
        target_user = sample_users[2]  # analyst
        
        response = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            json={"role": "admin"},
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_cannot_demote_self(self, client: TestClient, admin_user):
        """Admin cannot demote themselves."""
        admin, headers = admin_user
        
        response = client.patch(
            f"/api/v1/users/{admin.id}/role",
            json={"role": "viewer"},
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Cannot demote your own" in response.json()["detail"]

    def test_update_role_not_found(self, client: TestClient, admin_user):
        """Updating non-existent user returns 404."""
        admin, headers = admin_user
        response = client.patch(
            "/api/v1/users/99999/role",
            json={"role": "analyst"},
            headers=headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Deactivate User Tests
# ---------------------------------------------------------------------------
class TestDeactivateUser:
    """Tests for POST /api/v1/users/{id}/deactivate endpoint."""

    def test_deactivate_user_success(self, client: TestClient, admin_user, sample_users):
        """Admin can deactivate a user."""
        admin, headers = admin_user
        target_user = sample_users[0]  # viewer1
        
        response = client.post(
            f"/api/v1/users/{target_user.id}/deactivate",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["deactivated_at"] is not None

    def test_deactivate_with_reason(self, client: TestClient, admin_user, sample_users):
        """Can provide reason for deactivation."""
        admin, headers = admin_user
        target_user = sample_users[2]  # analyst1
        
        response = client.post(
            f"/api/v1/users/{target_user.id}/deactivate",
            json={"is_active": False, "reason": "Policy violation"},
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_cannot_deactivate_self(self, client: TestClient, admin_user):
        """Admin cannot deactivate themselves."""
        admin, headers = admin_user
        
        response = client.post(
            f"/api/v1/users/{admin.id}/deactivate",
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Cannot deactivate your own" in response.json()["detail"]

    def test_deactivate_not_found(self, client: TestClient, admin_user):
        """Deactivating non-existent user returns 404."""
        admin, headers = admin_user
        response = client.post("/api/v1/users/99999/deactivate", headers=headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Activate User Tests
# ---------------------------------------------------------------------------
class TestActivateUser:
    """Tests for POST /api/v1/users/{id}/activate endpoint."""

    def test_activate_user_success(self, client: TestClient, admin_user, sample_users):
        """Admin can activate a deactivated user."""
        admin, headers = admin_user
        target_user = sample_users[1]  # viewer2 (inactive)
        
        response = client.post(
            f"/api/v1/users/{target_user.id}/activate",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert data["deactivated_at"] is None

    def test_activate_already_active(self, client: TestClient, admin_user, sample_users):
        """Activating already active user is idempotent."""
        admin, headers = admin_user
        target_user = sample_users[0]  # viewer1 (active)
        
        response = client.post(
            f"/api/v1/users/{target_user.id}/activate",
            headers=headers
        )
        
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_activate_not_found(self, client: TestClient, admin_user):
        """Activating non-existent user returns 404."""
        admin, headers = admin_user
        response = client.post("/api/v1/users/99999/activate", headers=headers)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Full Workflow Tests
# ---------------------------------------------------------------------------
class TestUserManagementWorkflow:
    """Integration tests for complete user management workflows."""

    def test_deactivate_then_activate(self, client: TestClient, admin_user, sample_users):
        """Can deactivate and then reactivate a user."""
        admin, headers = admin_user
        target = sample_users[0]
        
        # Deactivate
        resp1 = client.post(f"/api/v1/users/{target.id}/deactivate", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["is_active"] is False
        
        # Verify in list
        list_resp = client.get("/api/v1/users?is_active=false", headers=headers)
        inactive_ids = [u["id"] for u in list_resp.json()["items"]]
        assert target.id in inactive_ids
        
        # Activate
        resp2 = client.post(f"/api/v1/users/{target.id}/activate", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is True

    def test_promote_user_workflow(self, client: TestClient, admin_user, sample_users):
        """Workflow: viewer -> analyst -> admin."""
        admin, headers = admin_user
        target = sample_users[0]  # viewer
        
        # Promote to analyst
        resp1 = client.patch(
            f"/api/v1/users/{target.id}/role",
            json={"role": "analyst"},
            headers=headers
        )
        assert resp1.json()["role"] == "analyst"
        
        # Promote to admin
        resp2 = client.patch(
            f"/api/v1/users/{target.id}/role",
            json={"role": "admin"},
            headers=headers
        )
        assert resp2.json()["role"] == "admin"
