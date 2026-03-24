"""
Shared test fixtures for the OpenCredit test suite.

Uses an in-memory SQLite database so tests run fast and require
no external services (no Postgres, no Redis).
"""
import os

# --- Override env BEFORE any application imports --------------------------
os.environ["DATABASE_URL"] = "sqlite:///./test_opencredit.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET"] = "test-jwt-secret-that-is-long-enough"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.security import (
    hash_password,
    generate_merchant_api_key,
    hash_api_key,
    create_access_token,
)
from app.models.user import User
from app.models.merchant import Merchant
from app.models.credit import CreditAccount


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///./test_opencredit.db"
_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db() -> Session:
    """Yield a raw SQLAlchemy session for data-setup helpers."""
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------
@pytest.fixture()
def seed_user(db: Session):
    """Create a user + credit account and return (user, jwt_token)."""
    def _create(
        email: str = "alice@example.com",
        full_name: str = "Alice Example",
        password: str = "SuperStrong123",
        credit_limit: float = 5000.0,
    ):
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
        db.add(CreditAccount(user_id=user.id, credit_limit=credit_limit, available_credit=credit_limit))
        db.commit()
        db.refresh(user)
        token = create_access_token(subject=user.email)
        return user, token

    return _create


@pytest.fixture()
def seed_merchant(db: Session):
    """Create a merchant and return (merchant, plain_api_key)."""
    def _create(name: str = "Demo Merchant"):
        api_key = generate_merchant_api_key()
        merchant = Merchant(name=name, api_key_hash=hash_api_key(api_key))
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        return merchant, api_key

    return _create


@pytest.fixture()
def auth_headers(seed_user, seed_merchant):
    """Convenience: creates a user + merchant and returns (headers_dict, user, merchant)."""
    user, token = seed_user()
    merchant, api_key = seed_merchant()
    headers = {"Authorization": f"Bearer {token}", "X-API-Key": api_key}
    return headers, user, merchant
