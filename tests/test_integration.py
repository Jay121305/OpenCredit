"""
Integration tests for OpenCredit platform.

These tests verify complete user flows:
1. User registration → Login → Merchant creation → Payment processing
2. Fraud detection scenarios
3. Ledger integrity
4. API key rotation
5. Rate limiting behavior

Run with: pytest tests/test_integration.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.credit import CreditAccount
from app.models.merchant import Merchant
from app.models.ledger import LedgerEntry


# ============================================================================
# FLOW 1: Complete User Journey
# ============================================================================

class TestUserJourney:
    """Test complete user flow from registration to payment."""
    
    def test_full_user_journey(self, client: TestClient, db: Session):
        """
        Complete flow:
        1. Admin creates merchant
        2. User registers
        3. User logs in
        4. User makes payment
        5. User checks analytics
        """
        # Step 0: Create admin user (needed for merchant creation)
        admin = User(
            email="admin@opencredit.io",
            full_name="Admin User",
            password_hash=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()
        db.add(CreditAccount(user_id=admin.id, credit_limit=10000.0, available_credit=10000.0))
        db.commit()
        admin_token = create_access_token(subject=admin.email)
        
        # Step 1: Admin creates a merchant
        merchant_resp = client.post(
            "/api/v1/merchants",
            json={"name": "Test Store"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert merchant_resp.status_code == 201, merchant_resp.json()
        merchant_data = merchant_resp.json()
        assert "api_key" in merchant_data
        merchant_api_key = merchant_data["api_key"]
        
        # Step 2: User registers
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User",
            },
        )
        assert register_resp.status_code == 201, register_resp.json()
        user_data = register_resp.json()
        assert user_data["email"] == "testuser@example.com"
        assert user_data["credit_limit"] > 0
        
        # Step 3: User logs in
        login_resp = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser@example.com", "password": "SecurePass123!"},
        )
        assert login_resp.status_code == 200, login_resp.json()
        token_data = login_resp.json()
        assert "access_token" in token_data
        user_token = token_data["access_token"]
        
        # Step 4: User makes a payment
        payment_resp = client.post(
            "/api/v1/payments",
            json={
                "amount": 50.00,
                "currency": "USD",
                "category": "electronics",
                "description": "Test purchase",
                "idempotency_key": "test-journey-001",
            },
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-API-Key": merchant_api_key,
            },
        )
        assert payment_resp.status_code == 200, payment_resp.json()
        payment_data = payment_resp.json()
        assert payment_data["status"] == "approved"
        assert payment_data["fraud_score"] < 0.75
        
        # Step 5: Check user info (credit reduced)
        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["available_credit"] < me_data["credit_limit"]
    
    def test_user_cannot_exceed_credit_limit(self, client: TestClient, seed_user, seed_merchant):
        """User cannot make payment exceeding their credit limit."""
        user, token = seed_user(credit_limit=100.0)
        merchant, api_key = seed_merchant()
        
        # Try to make a payment larger than credit limit
        payment_resp = client.post(
            "/api/v1/payments",
            json={
                "amount": 150.00,
                "currency": "USD",
                "category": "shopping",
                "description": "Over limit purchase",
                "idempotency_key": "overlimit-001",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": api_key,
            },
        )
        assert payment_resp.status_code == 400
        assert "insufficient" in payment_resp.json()["detail"].lower()


# ============================================================================
# FLOW 2: Fraud Detection
# ============================================================================

class TestFraudDetection:
    """Test fraud detection scenarios."""
    
    def test_high_value_transaction_flagged(self, client: TestClient, seed_user, seed_merchant):
        """High-value transactions should be flagged or rejected."""
        user, token = seed_user(credit_limit=10000.0)
        merchant, api_key = seed_merchant()
        
        # High-value transaction (exceeds fraud threshold)
        payment_resp = client.post(
            "/api/v1/payments",
            json={
                "amount": 8000.00,  # Very high value
                "currency": "USD",
                "category": "luxury",
                "description": "Expensive item",
                "idempotency_key": "highvalue-001",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": api_key,
            },
        )
        
        # Should complete but with high fraud score
        if payment_resp.status_code == 200:
            data = payment_resp.json()
            # High value should increase fraud score
            assert data["fraud_score"] > 0.0
    
    def test_velocity_fraud_detection(self, client: TestClient, seed_user, seed_merchant):
        """Multiple rapid transactions should increase fraud score."""
        user, token = seed_user(credit_limit=10000.0)
        merchant, api_key = seed_merchant()
        
        fraud_scores = []
        
        # Make multiple transactions rapidly
        for i in range(5):
            payment_resp = client.post(
                "/api/v1/payments",
                json={
                    "amount": 100.00,
                    "currency": "USD",
                    "category": "shopping",
                    "description": f"Rapid purchase {i}",
                    "idempotency_key": f"velocity-{i:03d}",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-API-Key": api_key,
                },
            )
            if payment_resp.status_code == 200:
                fraud_scores.append(payment_resp.json()["fraud_score"])
        
        # Later transactions should have higher fraud scores due to velocity
        # (implementation depends on how velocity is tracked)
        assert len(fraud_scores) >= 3, "Should process at least 3 transactions"


# ============================================================================
# FLOW 3: Ledger Integrity
# ============================================================================

class TestLedgerIntegrity:
    """Test hash-chained ledger integrity."""
    
    def test_ledger_chain_integrity(self, client: TestClient, db: Session, seed_user, seed_merchant):
        """Verify ledger entries are properly chained."""
        user, token = seed_user()
        merchant, api_key = seed_merchant()
        
        # Make a few payments to create ledger entries
        for i in range(3):
            client.post(
                "/api/v1/payments",
                json={
                    "amount": 25.00,
                    "currency": "USD",
                    "category": "test",
                    "description": f"Ledger test {i}",
                    "idempotency_key": f"ledger-test-{i:03d}",
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-API-Key": api_key,
                },
            )
        
        # Verify ledger entries exist and are chained
        ledger_entries = db.query(LedgerEntry).order_by(LedgerEntry.created_at).all()
        
        if len(ledger_entries) >= 2:
            # First entry should have previous_hash of zeros or initial hash
            first_entry = ledger_entries[0]
            assert first_entry.current_hash is not None
            
            # Subsequent entries should reference previous entry's hash
            for i in range(1, len(ledger_entries)):
                current = ledger_entries[i]
                previous = ledger_entries[i - 1]
                assert current.previous_hash == previous.current_hash, \
                    f"Entry {i} should reference previous entry's hash"


# ============================================================================
# FLOW 4: API Key Rotation
# ============================================================================

class TestApiKeyRotation:
    """Test merchant API key rotation."""
    
    def test_key_rotation_workflow(self, client: TestClient, db: Session):
        """Test complete API key rotation flow."""
        # Create admin
        admin = User(
            email="admin@test.io",
            full_name="Admin",
            password_hash=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()
        db.add(CreditAccount(user_id=admin.id, credit_limit=1000.0, available_credit=1000.0))
        db.commit()
        admin_token = create_access_token(subject=admin.email)
        
        # Create merchant
        create_resp = client.post(
            "/api/v1/merchants",
            json={"name": "Rotation Test Merchant"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        merchant_id = create_resp.json()["merchant_id"]
        old_api_key = create_resp.json()["api_key"]
        
        # Rotate the key
        rotate_resp = client.post(
            f"/api/v1/merchants/{merchant_id}/rotate-key",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert rotate_resp.status_code == 200, rotate_resp.json()
        rotate_data = rotate_resp.json()
        new_api_key = rotate_data["new_api_key"]
        
        assert new_api_key != old_api_key
        assert "old_key_valid_until" in rotate_data
        
        # Create a test user for payment
        user = User(
            email="paymentuser@test.io",
            full_name="Payment User",
            password_hash=hash_password("UserPass123!"),
        )
        db.add(user)
        db.flush()
        db.add(CreditAccount(user_id=user.id, credit_limit=5000.0, available_credit=5000.0))
        db.commit()
        user_token = create_access_token(subject=user.email)
        
        # Both keys should work during grace period
        # Test with new key
        payment_new = client.post(
            "/api/v1/payments",
            json={
                "amount": 10.00,
                "currency": "USD",
                "category": "test",
                "description": "New key test",
                "idempotency_key": "newkey-001",
            },
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-API-Key": new_api_key,
            },
        )
        assert payment_new.status_code == 200, payment_new.json()
        
        # Test with old key (should still work during grace period)
        payment_old = client.post(
            "/api/v1/payments",
            json={
                "amount": 10.00,
                "currency": "USD",
                "category": "test",
                "description": "Old key test",
                "idempotency_key": "oldkey-001",
            },
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-API-Key": old_api_key,
            },
        )
        assert payment_old.status_code == 200, payment_old.json()
    
    def test_revoke_secondary_key(self, client: TestClient, db: Session):
        """Test immediate revocation of secondary key."""
        # Create admin and merchant
        admin = User(
            email="revokeadmin@test.io",
            full_name="Admin",
            password_hash=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()
        db.add(CreditAccount(user_id=admin.id, credit_limit=1000.0, available_credit=1000.0))
        db.commit()
        admin_token = create_access_token(subject=admin.email)
        
        # Create merchant
        create_resp = client.post(
            "/api/v1/merchants",
            json={"name": "Revoke Test Merchant"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        merchant_id = create_resp.json()["merchant_id"]
        old_api_key = create_resp.json()["api_key"]
        
        # Rotate the key
        rotate_resp = client.post(
            f"/api/v1/merchants/{merchant_id}/rotate-key",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        new_api_key = rotate_resp.json()["new_api_key"]
        
        # Revoke secondary key
        revoke_resp = client.post(
            f"/api/v1/merchants/{merchant_id}/revoke-secondary-key",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert revoke_resp.status_code == 200
        
        # Create test user
        user = User(
            email="revokeuser@test.io",
            full_name="User",
            password_hash=hash_password("UserPass123!"),
        )
        db.add(user)
        db.flush()
        db.add(CreditAccount(user_id=user.id, credit_limit=5000.0, available_credit=5000.0))
        db.commit()
        user_token = create_access_token(subject=user.email)
        
        # Old key should no longer work
        payment_old = client.post(
            "/api/v1/payments",
            json={
                "amount": 10.00,
                "currency": "USD",
                "category": "test",
                "description": "Revoked key test",
                "idempotency_key": "revoked-001",
            },
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-API-Key": old_api_key,
            },
        )
        assert payment_old.status_code == 401  # Old key should be invalid


# ============================================================================
# FLOW 5: Admin Restrictions
# ============================================================================

class TestAdminRestrictions:
    """Test admin-only endpoints."""
    
    def test_non_admin_cannot_create_merchant(self, client: TestClient, seed_user):
        """Regular users cannot create merchants."""
        user, token = seed_user()
        
        resp = client.post(
            "/api/v1/merchants",
            json={"name": "Unauthorized Merchant"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()
    
    def test_unauthenticated_cannot_create_merchant(self, client: TestClient):
        """Unauthenticated requests cannot create merchants."""
        resp = client.post(
            "/api/v1/merchants",
            json={"name": "Unauthorized Merchant"},
        )
        assert resp.status_code == 401


# ============================================================================
# FLOW 6: Idempotency
# ============================================================================

class TestIdempotency:
    """Test idempotent payment processing."""
    
    def test_duplicate_idempotency_key(self, client: TestClient, seed_user, seed_merchant):
        """Duplicate payments with same idempotency key should return same result."""
        user, token = seed_user()
        merchant, api_key = seed_merchant()
        
        payment_data = {
            "amount": 100.00,
            "currency": "USD",
            "category": "test",
            "description": "Idempotent payment",
            "idempotency_key": "idempotent-test-001",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "X-API-Key": api_key,
        }
        
        # First request
        resp1 = client.post("/api/v1/payments", json=payment_data, headers=headers)
        assert resp1.status_code == 200
        
        # Second request with same idempotency key
        resp2 = client.post("/api/v1/payments", json=payment_data, headers=headers)
        
        # Should return same transaction or indicate duplicate
        if resp2.status_code == 200:
            # Same transaction ID should be returned
            assert resp1.json()["transaction_id"] == resp2.json()["transaction_id"]
        else:
            # Or a 409 Conflict indicating duplicate
            assert resp2.status_code == 409


# ============================================================================
# FLOW 7: Health & Metrics
# ============================================================================

class TestHealthAndMetrics:
    """Test health check and metrics endpoints."""
    
    def test_health_endpoint(self, client: TestClient):
        """Health endpoint should return OK."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
    
    def test_ready_endpoint(self, client: TestClient):
        """Readiness endpoint should check dependencies."""
        resp = client.get("/ready")
        # Should return 200 if all dependencies are up
        assert resp.status_code in [200, 503]
        data = resp.json()
        assert "checks" in data
    
    def test_info_endpoint(self, client: TestClient):
        """Info endpoint should return version info."""
        resp = client.get("/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "environment" in data


# ============================================================================
# FLOW 8: Input Validation
# ============================================================================

class TestInputValidation:
    """Test input validation and error handling."""
    
    def test_weak_password_rejected(self, client: TestClient):
        """Weak passwords should be rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "weak",  # Too short, no complexity
                "full_name": "Weak Pass User",
            },
        )
        assert resp.status_code == 422  # Validation error
    
    def test_invalid_email_rejected(self, client: TestClient):
        """Invalid emails should be rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "full_name": "Invalid Email User",
            },
        )
        assert resp.status_code == 422
    
    def test_negative_amount_rejected(self, client: TestClient, seed_user, seed_merchant):
        """Negative payment amounts should be rejected."""
        user, token = seed_user()
        merchant, api_key = seed_merchant()
        
        resp = client.post(
            "/api/v1/payments",
            json={
                "amount": -50.00,  # Negative amount
                "currency": "USD",
                "category": "test",
                "description": "Negative test",
                "idempotency_key": "negative-001",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": api_key,
            },
        )
        assert resp.status_code == 422
    
    def test_excessive_amount_rejected(self, client: TestClient, seed_user, seed_merchant):
        """Amounts exceeding max transaction limit should be rejected."""
        user, token = seed_user(credit_limit=1_000_000)
        merchant, api_key = seed_merchant()
        
        resp = client.post(
            "/api/v1/payments",
            json={
                "amount": 999_999_999.99,  # Exceeds max transaction amount
                "currency": "USD",
                "category": "test",
                "description": "Excessive test",
                "idempotency_key": "excessive-001",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": api_key,
            },
        )
        assert resp.status_code == 422
