#!/usr/bin/env python3
"""
Seed script to create the initial admin user.

Usage:
    python -m scripts.seed_admin

Environment variables required:
    - ADMIN_EMAIL: Admin email address
    - ADMIN_PASSWORD: Admin password (must meet security requirements)
    - ADMIN_NAME: Admin full name (optional, defaults to "System Admin")
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.credit import CreditAccount


def create_admin_user(
    email: str,
    password: str,
    full_name: str = "System Admin",
) -> None:
    """Create an admin user if one doesn't exist."""
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            if existing.role == UserRole.ADMIN.value:
                print(f"✓ Admin user '{email}' already exists")
            else:
                # Upgrade to admin
                existing.role = UserRole.ADMIN.value
                db.commit()
                print(f"✓ User '{email}' upgraded to admin")
            return

        # Create new admin user
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(user)
        db.flush()

        # Create credit account
        credit = CreditAccount(
            user_id=user.id,
            credit_limit=settings.default_credit_limit,
            available_credit=settings.default_credit_limit,
        )
        db.add(credit)
        db.commit()

        print(f"✓ Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Name: {full_name}")
        print(f"  Role: admin")
        print(f"\n⚠️  Store the password securely - it cannot be recovered!")

    except Exception as e:
        db.rollback()
        print(f"✗ Failed to create admin user: {e}")
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    # Get credentials from environment or prompt
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    full_name = os.environ.get("ADMIN_NAME", "System Admin")

    if not email:
        email = input("Enter admin email: ").strip()
    if not password:
        import getpass
        password = getpass.getpass("Enter admin password: ")

    # Validate password strength
    import re
    if len(password) < 8:
        print("✗ Password must be at least 8 characters")
        sys.exit(1)
    if not re.search(r"[A-Z]", password):
        print("✗ Password must contain at least one uppercase letter")
        sys.exit(1)
    if not re.search(r"[a-z]", password):
        print("✗ Password must contain at least one lowercase letter")
        sys.exit(1)
    if not re.search(r"\d", password):
        print("✗ Password must contain at least one digit")
        sys.exit(1)

    create_admin_user(email=email, password=password, full_name=full_name)


if __name__ == "__main__":
    main()
