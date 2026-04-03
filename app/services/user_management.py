"""
User management service for admin operations.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.schemas.user import (
    UserFilter,
    UserListResponse,
    UserPaginationParams,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)


class UserManagementService:
    """Service for admin user management operations."""

    def __init__(self, db: Session):
        self.db = db

    def list_users(
        self,
        filters: Optional[UserFilter] = None,
        pagination: Optional[UserPaginationParams] = None,
    ) -> UserListResponse:
        """
        List all users with filtering and pagination.
        
        Args:
            filters: Optional filter parameters
            pagination: Optional pagination parameters
            
        Returns:
            UserListResponse with users and pagination info
        """
        filters = filters or UserFilter()
        pagination = pagination or UserPaginationParams()

        query = select(User)

        # Apply filters
        if filters.role:
            query = query.where(User.role == filters.role.value)

        if filters.is_active is not None:
            query = query.where(User.is_active == filters.is_active)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query) or 0

        # Apply sorting
        sort_column = getattr(User, pagination.sort_by, User.created_at)
        if pagination.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (pagination.page - 1) * pagination.per_page
        query = query.offset(offset).limit(pagination.per_page)

        # Execute
        users = list(self.db.scalars(query).all())

        total_pages = (total + pagination.per_page - 1) // pagination.per_page

        return UserListResponse(
            items=[self._to_response(u) for u in users],
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=total_pages,
        )

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User if found, None otherwise
        """
        return self.db.scalar(select(User).where(User.id == user_id))

    def update_user_role(
        self, user_id: int, data: UserRoleUpdate, admin_user_id: int
    ) -> Optional[User]:
        """
        Update a user's role.
        
        Args:
            user_id: Target user ID
            data: Role update data
            admin_user_id: Admin performing the action (for audit)
            
        Returns:
            Updated User if found, None otherwise
        """
        user = self.get_user(user_id)
        if not user:
            return None

        # Prevent admin from demoting themselves
        if user_id == admin_user_id and data.role != UserRole.ADMIN:
            raise ValueError("Cannot demote your own admin account")

        user.role = data.role.value
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate_user(
        self, user_id: int, admin_user_id: int, reason: Optional[str] = None
    ) -> Optional[User]:
        """
        Deactivate a user account.
        
        Args:
            user_id: Target user ID
            admin_user_id: Admin performing the action
            reason: Optional reason for deactivation
            
        Returns:
            Updated User if found, None otherwise
        """
        user = self.get_user(user_id)
        if not user:
            return None

        # Prevent admin from deactivating themselves
        if user_id == admin_user_id:
            raise ValueError("Cannot deactivate your own account")

        user.is_active = False
        user.deactivated_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate_user(self, user_id: int) -> Optional[User]:
        """
        Reactivate a user account.
        
        Args:
            user_id: Target user ID
            
        Returns:
            Updated User if found, None otherwise
        """
        user = self.get_user(user_id)
        if not user:
            return None

        user.is_active = True
        user.deactivated_at = None
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_stats(self) -> dict:
        """
        Get aggregate user statistics.
        
        Returns:
            Dictionary with user counts by role and status
        """
        # Total users
        total = self.db.scalar(select(func.count()).select_from(User)) or 0

        # Active users
        active = self.db.scalar(
            select(func.count()).where(User.is_active == True)
        ) or 0

        # Users by role
        role_query = (
            select(User.role, func.count().label("count"))
            .group_by(User.role)
        )
        role_results = self.db.execute(role_query).all()
        by_role = {r.role: r.count for r in role_results}

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "by_role": by_role,
        }

    def _to_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else None,
            deactivated_at=user.deactivated_at.isoformat() if user.deactivated_at else None,
        )


def get_user_management_service(db: Session) -> UserManagementService:
    """Factory function to create UserManagementService instance."""
    return UserManagementService(db)
