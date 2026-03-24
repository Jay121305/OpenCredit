"""Tests for core security helpers."""
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_merchant_api_key,
    hash_api_key,
)
import pytest


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "MySecure!Pass42"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-horse")
        assert not verify_password("wrong-horse", hashed)

    def test_different_salts(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # unique salts

    def test_malformed_hash_returns_false(self):
        assert not verify_password("pw", "not-a-valid-hash")


class TestJWT:
    def test_roundtrip(self):
        token = create_access_token("user@example.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "user@example.com"

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token("not.a.jwt")


class TestMerchantKeys:
    def test_key_format(self):
        key = generate_merchant_api_key()
        assert key.startswith("oc_live_")

    def test_hash_deterministic(self):
        key = generate_merchant_api_key()
        assert hash_api_key(key) == hash_api_key(key)

    def test_different_keys_different_hashes(self):
        k1 = generate_merchant_api_key()
        k2 = generate_merchant_api_key()
        assert hash_api_key(k1) != hash_api_key(k2)
