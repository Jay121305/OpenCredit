"""Tests for merchant onboarding endpoint."""


class TestMerchantCreate:
    def test_create_merchant_success(self, client):
        resp = client.post("/api/v1/merchants", json={"name": "Test Store"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Test Store"
        assert body["merchant_id"] > 0
        assert body["api_key"].startswith("oc_live_")

    def test_create_merchant_short_name_rejected(self, client):
        resp = client.post("/api/v1/merchants", json={"name": "A"})
        assert resp.status_code == 422

    def test_create_multiple_merchants(self, client):
        resp1 = client.post("/api/v1/merchants", json={"name": "Store Alpha"})
        resp2 = client.post("/api/v1/merchants", json={"name": "Store Beta"})
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["api_key"] != resp2.json()["api_key"]
