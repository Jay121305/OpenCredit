"""Tests for auth routes: register and login."""
import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "bob@example.com",
                "full_name": "Bob Tester",
                "password": "StrongPass99!",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_register_duplicate_email(self, client):
        payload = {
            "email": "dup@example.com",
            "full_name": "Dup User",
            "password": "StrongPass99!",
        }
        first = client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 400
        assert "already exists" in second.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "full_name": "Bad Email",
                "password": "StrongPass99",
            },
        )
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "full_name": "Short Pw",
                "password": "Abc1!",
            },
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login_user@example.com",
                "full_name": "Login User",
                "password": "StrongPass99!",
            },
        )

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "login_user@example.com", "password": "StrongPass99!"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "wp@example.com",
                "full_name": "Wrong Pass",
                "password": "StrongPass99!",
            },
        )

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wp@example.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever123"},
        )
        assert resp.status_code == 401
