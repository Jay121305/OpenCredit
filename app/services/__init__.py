"""
Service exports for the OpenCredit platform.
"""

from app.services.dashboard import DashboardService, get_dashboard_service
from app.services.record import RecordService, get_record_service
from app.services.user_management import UserManagementService, get_user_management_service

__all__ = [
    "RecordService",
    "get_record_service",
    "DashboardService",
    "get_dashboard_service",
    "UserManagementService",
    "get_user_management_service",
]