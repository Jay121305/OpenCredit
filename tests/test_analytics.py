"""Tests for analytics / spending-summary endpoint."""


class TestSpendingSummary:
    def _pay(self, client, headers, amount, category, key):
        return client.post(
            "/api/v1/payments",
            json={
                "amount": amount,
                "currency": "USD",
                "category": category,
                "geo": "US",
                "idempotency_key": key,
            },
            headers=headers,
        )

    def test_empty_summary(self, client, seed_user):
        """No transactions → zeroes."""
        user, token = seed_user()
        resp = client.get(
            "/api/v1/analytics/spending-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["month_total"] == 0.0
        assert body["by_category"] == []

    def test_summary_with_transactions(self, client, auth_headers):
        headers, _, _ = auth_headers
        r1 = self._pay(client, headers, 100.0, "food", "analytics-key-001")
        r2 = self._pay(client, headers, 200.0, "electronics", "analytics-key-002")
        r3 = self._pay(client, headers, 50.0, "food", "analytics-key-003")
        assert r1.status_code == 200, f"Payment 1 failed: {r1.text}"
        assert r2.status_code == 200, f"Payment 2 failed: {r2.text}"
        assert r3.status_code == 200, f"Payment 3 failed: {r3.text}"

        resp = client.get("/api/v1/analytics/spending-summary", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        # Only approved/flagged transactions count
        assert body["month_total"] > 0

    def test_summary_unauthenticated(self, client):
        resp = client.get("/api/v1/analytics/spending-summary")
        assert resp.status_code == 401

    def test_utilization_increases_after_payment(self, client, auth_headers):
        headers, _, _ = auth_headers
        r = self._pay(client, headers, 500.0, "travel", "util-pay-key-001")
        assert r.status_code == 200, f"Payment failed: {r.text}"

        resp = client.get("/api/v1/analytics/spending-summary", headers=headers)
        body = resp.json()
        assert body["utilization_pct"] > 0
