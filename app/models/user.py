"""
User model with role-based access control.

Roles:
- viewer: Read-only dashboard access
- user: Standard user (default) - can view records
- analyst: Can create/edit records and view analytics
- admin: Full administrative access (can manage merchants and users)
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, Enum):
    """User role enumeration with hierarchical access levels."""
    VIEWER = "viewer"      # Read-only dashboard access
    USER = "user"          # Standard user (default)
    ANALYST = "analyst"    # Can create/edit records + analytics
    ADMIN = "admin"        # Full administrative access

    @classmethod
    def get_access_level(cls, role: str) -> int:
        """Get numeric access level for role comparison."""
        levels = {
            cls.VIEWER.value: 1,
            cls.USER.value: 2,
            cls.ANALYST.value: 3,
            cls.ADMIN.value: 4,
        }
        return levels.get(role, 0)


class User(Base):
    """User account model."""
    
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.USER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN.value

    @property
    def is_analyst(self) -> bool:
        """Check if user has analyst role or higher."""
        return UserRole.get_access_level(self.role) >= UserRole.get_access_level(UserRole.ANALYST.value)

    @property
    def is_viewer(self) -> bool:
        """Check if user has at least viewer role (any authenticated user)."""
        return UserRole.get_access_level(self.role) >= UserRole.get_access_level(UserRole.VIEWER.value)

    @property
    def access_level(self) -> int:
        """Get numeric access level for this user."""
        return UserRole.get_access_level(self.role)
