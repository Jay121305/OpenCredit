"""
Financial Records API routes.

Endpoints:
- POST   /records         Create a new record (analyst+)
- GET    /records         List records with filters (viewer+)
- GET    /records/{id}    Get single record (viewer+)
- PUT    /records/{id}    Update record (analyst+)
- DELETE /records/{id}    Soft delete record (analyst+)
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_analyst_user, get_current_viewer_user
from app.db.session import get_db
from app.models.record import RecordStatus, RecordType
from app.models.user import User
from app.schemas.record import (
    PaginationParams,
    RecordCreate,
    RecordFilter,
    RecordListResponse,
    RecordResponse,
    RecordUpdate,
)
from app.services.record import RecordService


router = APIRouter(prefix="/records", tags=["Records"])


def get_record_service(db: Session = Depends(get_db)) -> RecordService:
    """Dependency to get RecordService instance."""
    return RecordService(db)


@router.post(
    "",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new financial record",
    description="Create a new income, expense, or transfer record. Requires analyst role or higher.",
)
def create_record(
    data: RecordCreate,
    user: User = Depends(get_current_analyst_user),
    service: RecordService = Depends(get_record_service),
) -> RecordResponse:
    """Create a new financial record."""
    record = service.create_record(user.id, data)
    return service._to_response(record)


@router.get(
    "",
    response_model=RecordListResponse,
    summary="List financial records",
    description="Get paginated list of user's records with optional filters. Requires viewer role or higher.",
)
def list_records(
    # Filter parameters
    type: Optional[RecordType] = Query(None, description="Filter by record type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[RecordStatus] = Query(None, description="Filter by status"),
    date_from: Optional[date] = Query(None, description="Start date (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date (inclusive)"),
    min_amount: Optional[Decimal] = Query(None, ge=0, description="Minimum amount"),
    max_amount: Optional[Decimal] = Query(None, ge=0, description="Maximum amount"),
    search: Optional[str] = Query(None, max_length=100, description="Search in description"),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("record_date", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    # Dependencies
    user: User = Depends(get_current_viewer_user),
    service: RecordService = Depends(get_record_service),
) -> RecordListResponse:
    """List user's financial records with filtering and pagination."""
    filters = RecordFilter(
        type=type,
        category=category,
        status=status,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
        include_deleted=include_deleted,
    )
    pagination = PaginationParams(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return service.list_records(user.id, filters, pagination)


@router.get(
    "/{record_id}",
    response_model=RecordResponse,
    summary="Get a single record",
    description="Get details of a specific financial record. Requires viewer role or higher.",
)
def get_record(
    record_id: int,
    user: User = Depends(get_current_viewer_user),
    service: RecordService = Depends(get_record_service),
) -> RecordResponse:
    """Get a single financial record by ID."""
    record = service.get_record(record_id, user.id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    return service._to_response(record)


@router.put(
    "/{record_id}",
    response_model=RecordResponse,
    summary="Update a record",
    description="Update an existing financial record. Requires analyst role or higher.",
)
def update_record(
    record_id: int,
    data: RecordUpdate,
    user: User = Depends(get_current_analyst_user),
    service: RecordService = Depends(get_record_service),
) -> RecordResponse:
    """Update a financial record."""
    record = service.update_record(record_id, user.id, data)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    return service._to_response(record)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a record",
    description="Soft-delete a financial record. Requires analyst role or higher.",
)
def delete_record(
    record_id: int,
    user: User = Depends(get_current_analyst_user),
    service: RecordService = Depends(get_record_service),
) -> None:
    """Soft-delete a financial record."""
    deleted = service.delete_record(record_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
