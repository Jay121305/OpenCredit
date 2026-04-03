"""
User Management API routes (Admin only).

Endpoints:
- GET    /users              List all users (admin)
- GET    /users/stats        Get user statistics (admin)
- GET    /users/{id}         Get user details (admin)
- PATCH  /users/{id}/role    Update user role (admin)
- POST   /users/{id}/deactivate  Deactivate user (admin)
- POST   /users/{id}/activate    Activate user (admin)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    UserFilter,
    UserListResponse,
    UserPaginationParams,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.services.user_management import UserManagementService


router = APIRouter(prefix="/users", tags=["User Management"])


def get_user_service(db: Session = Depends(get_db)) -> UserManagementService:
    """Dependency to get UserManagementService instance."""
    return UserManagementService(db)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users",
    description="Get paginated list of all users. Admin only.",
)
def list_users(
    # Filter parameters
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, max_length=100, description="Search in email or name"),
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    # Dependencies
    admin: User = Depends(get_current_admin_user),
    service: UserManagementService = Depends(get_user_service),
) -> UserListResponse:
    """List all users with filtering and pagination."""
    filters = UserFilter(
        role=role,
        is_active=is_active,
        search=search,
    )
    pagination = UserPaginationParams(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return service.list_users(filters, pagination)


@router.get(
    "/stats",
    summary="Get user statistics",
    description="Get aggregate user statistics. Admin only.",
)
def get_user_stats(
    admin: User = Depends(get_current_admin_user),
    service: UserManagementService = Depends(get_user_service),
) -> dict:
    """Get aggregate user statistics."""
    return service.get_user_stats()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details",
    description="Get details of a specific user. Admin only.",
)
def get_user(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    service: UserManagementService = Depends(get_user_service),
) -> UserResponse:
    """Get a single user by ID."""
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return service._to_response(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role",
    description="Change a user's role. Admin only. Cannot demote yourself.",
)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    admin: User = Depends(get_current_admin_user),
    service: UserManagementService = Depends(get_user_service),
) -> UserResponse:
    """Update a user's role."""
    try:
        user = service.update_user_role(user_id, data, admin.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return service._to_response(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user",
    description="Deactivate a user account. Admin only. Cannot deactivate yourself.",
)
def deactivate_user(
    user_id: int,
    data: Optional[UserStatusUpdate] = None,
    admin: User = Depends(get_current_admin_user),
    service: UserManagementService = Depends(get_user_service),
) -> UserResponse:
    """Deactivate a user account."""
    reason = data.reason if data else None
    try:
        user = service.deactivate_user(user_id, admin.id, reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return service._to_response(user)


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user",
    description="Reactivate a deactivated user account. Admin only.",
)
def activate_user(
    user_id: int,
    admin: User = Depends(get_current_admin_user),
    service: UserManagementService = Depends(get_user_service),
) -> UserResponse:
    """Activate a user account."""
    user = service.activate_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return service._to_response(user)
