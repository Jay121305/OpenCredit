"""Tests for the payment flow (end-to-end via API)."""


class TestPaymentFlow:
    def _make_payment(self, client, headers, amount=120.0, key="idem-default-001"):
        return client.post(
            "/api/v1/payments",
            json={
                "amount": amount,
                "currency": "USD",
                "category": "food",
                "geo": "US",
                "idempotency_key": key,
            },
            headers=headers,
        )

    def test_payment_approved(self, client, auth_headers):
        headers, user, _ = auth_headers
        resp = self._make_payment(client, headers, amount=100.0, key="pay-ok-key-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in {"approved", "flagged"}
        assert body["transaction_id"] > 0
        assert body["available_credit"] < 5000.0

    def test_payment_idempotency(self, client, auth_headers):
        headers, _, _ = auth_headers
        first = self._make_payment(client, headers, amount=80.0, key="idem-dup-key-001")
        second = self._make_payment(client, headers, amount=80.0, key="idem-dup-key-001")
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["transaction_id"] == second.json()["transaction_id"]

    def test_payment_exceeds_credit_rejected(self, client, auth_headers):
        headers, _, _ = auth_headers
        resp = self._make_payment(client, headers, amount=6000.0, key="over-limit-001")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_payment_missing_auth_rejected(self, client):
        resp = client.post(
            "/api/v1/payments",
            json={
                "amount": 50.0,
                "currency": "USD",
                "category": "misc",
                "geo": "US",
                "idempotency_key": "no-auth-key-001",
            },
        )
        assert resp.status_code == 401

    def test_payment_missing_api_key(self, client, seed_user):
        user, token = seed_user()
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            "/api/v1/payments",
            json={
                "amount": 50.0,
                "currency": "USD",
                "category": "misc",
                "geo": "US",
                "idempotency_key": "no-apikey-001",
            },
            headers=headers,
        )
        assert resp.status_code == 401

    def test_payment_invalid_amount(self, client, auth_headers):
        headers, _, _ = auth_headers
        resp = client.post(
            "/api/v1/payments",
            json={
                "amount": -10.0,
                "currency": "USD",
                "category": "food",
                "geo": "US",
                "idempotency_key": "neg-amt-key-001",
            },
            headers=headers,
        )
        assert resp.status_code == 422

    def test_multiple_payments_decrease_credit(self, client, auth_headers):
        headers, _, _ = auth_headers
        r1 = self._make_payment(client, headers, amount=1000.0, key="multi-pay-001")
        assert r1.status_code == 200, f"Payment 1 failed: {r1.text}"
        r2 = self._make_payment(client, headers, amount=1000.0, key="multi-pay-002")
        assert r2.status_code == 200, f"Payment 2 failed: {r2.text}"
        body = r2.json()
        if body["status"] in {"approved", "flagged"}:
            assert body["available_credit"] <= 3000.0
