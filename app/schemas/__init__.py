"""
Schema exports for the OpenCredit API.
"""

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.dashboard import (
    CategoryBreakdown,
    CategoryTotal,
    DashboardSummary,
    DateRangeParams,
    RecentActivity,
    RecentRecord,
    TrendData,
    TrendParams,
    TrendPoint,
)
from app.schemas.record import (
    PaginationMeta,
    PaginationParams,
    RecordCreate,
    RecordFilter,
    RecordListResponse,
    RecordResponse,
    RecordUpdate,
)
from app.schemas.user import (
    UserFilter,
    UserListResponse,
    UserPaginationParams,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    # Records
    "RecordCreate",
    "RecordUpdate",
    "RecordResponse",
    "RecordFilter",
    "RecordListResponse",
    "PaginationParams",
    "PaginationMeta",
    # Dashboard
    "DashboardSummary",
    "CategoryTotal",
    "CategoryBreakdown",
    "TrendPoint",
    "TrendData",
    "RecentRecord",
    "RecentActivity",
    "DateRangeParams",
    "TrendParams",
    # User Management
    "UserResponse",
    "UserListResponse",
    "UserRoleUpdate",
    "UserStatusUpdate",
    "UserFilter",
    "UserPaginationParams",
]