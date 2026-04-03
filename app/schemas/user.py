"""
User management schemas for admin operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserResponse(BaseModel):
    """Public user information response."""
    
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: Optional[str]
    deactivated_at: Optional[str]

    model_config = {"from_attributes": True}

    @field_validator("created_at", "updated_at", "deactivated_at", mode="before")
    @classmethod
    def serialize_datetime(cls, v):
        if v is None:
            return None
        return v.isoformat() if hasattr(v, "isoformat") else str(v)


class UserListResponse(BaseModel):
    """Paginated list of users."""
    
    items: list[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class UserRoleUpdate(BaseModel):
    """Schema for updating a user's role."""
    
    role: UserRole = Field(
        ...,
        description="New role to assign",
        json_schema_extra={"example": "analyst"}
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        """Ensure role is valid."""
        if v not in UserRole:
            raise ValueError(f"Invalid role. Must be one of: {[r.value for r in UserRole]}")
        return v


class UserStatusUpdate(BaseModel):
    """Schema for activating/deactivating a user."""
    
    is_active: bool = Field(
        ...,
        description="Whether the user should be active"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for status change (optional)"
    )


class UserFilter(BaseModel):
    """Filter parameters for user listing."""
    
    role: Optional[UserRole] = Field(
        None,
        description="Filter by role"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Filter by active status"
    )
    search: Optional[str] = Field(
        None,
        max_length=100,
        description="Search in email or name"
    )


class UserPaginationParams(BaseModel):
    """Pagination parameters for user listing."""
    
    page: int = Field(
        1,
        ge=1,
        description="Page number"
    )
    per_page: int = Field(
        20,
        ge=1,
        le=100,
        description="Items per page"
    )
    sort_by: str = Field(
        "created_at",
        description="Sort field"
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order"
    )
