"""
Financial Record service for CRUD operations with ownership enforcement.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.record import FinancialRecord, RecordStatus, RecordType
from app.schemas.record import (
    PaginationMeta,
    PaginationParams,
    RecordCreate,
    RecordFilter,
    RecordListResponse,
    RecordResponse,
    RecordUpdate,
)


class RecordService:
    """Service for managing financial records."""

    def __init__(self, db: Session):
        self.db = db

    def create_record(self, user_id: int, data: RecordCreate) -> FinancialRecord:
        """
        Create a new financial record for a user.
        
        Args:
            user_id: Owner user ID
            data: Record creation data
            
        Returns:
            Created FinancialRecord instance
        """
        record = FinancialRecord(
            user_id=user_id,
            amount=data.amount,
            type=data.type.value,
            category=data.category,
            description=data.description,
            record_date=data.record_date,
            status=RecordStatus.ACTIVE.value,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_record(self, record_id: int, user_id: int) -> Optional[FinancialRecord]:
        """
        Get a single record by ID with ownership check.
        
        Args:
            record_id: Record ID
            user_id: User ID for ownership verification
            
        Returns:
            FinancialRecord if found and owned by user, None otherwise
        """
        return self.db.scalar(
            select(FinancialRecord).where(
                and_(
                    FinancialRecord.id == record_id,
                    FinancialRecord.user_id == user_id,
                    FinancialRecord.is_deleted == False,
                )
            )
        )

    def get_record_admin(self, record_id: int) -> Optional[FinancialRecord]:
        """
        Get a single record by ID (admin access - no ownership check).
        
        Args:
            record_id: Record ID
            
        Returns:
            FinancialRecord if found, None otherwise
        """
        return self.db.scalar(
            select(FinancialRecord).where(FinancialRecord.id == record_id)
        )

    def update_record(
        self, record_id: int, user_id: int, data: RecordUpdate
    ) -> Optional[FinancialRecord]:
        """
        Update a record with ownership check.
        
        Args:
            record_id: Record ID
            user_id: User ID for ownership verification
            data: Update data (only non-None fields applied)
            
        Returns:
            Updated FinancialRecord if found, None otherwise
        """
        record = self.get_record(record_id, user_id)
        if not record:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        
        for field, value in update_data.items():
            if field == "type" and value:
                setattr(record, field, value.value)
            elif field == "status" and value:
                setattr(record, field, value.value)
            else:
                setattr(record, field, value)

        record.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_record(self, record_id: int, user_id: int) -> bool:
        """
        Soft-delete a record with ownership check.
        
        Args:
            record_id: Record ID
            user_id: User ID for ownership verification
            
        Returns:
            True if deleted, False if not found
        """
        record = self.get_record(record_id, user_id)
        if not record:
            return False

        record.soft_delete()
        self.db.commit()
        return True

    def list_records(
        self,
        user_id: int,
        filters: Optional[RecordFilter] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> RecordListResponse:
        """
        List records with filtering and pagination.
        
        Args:
            user_id: User ID to filter records
            filters: Optional filter parameters
            pagination: Optional pagination parameters
            
        Returns:
            RecordListResponse with items and pagination metadata
        """
        filters = filters or RecordFilter()
        pagination = pagination or PaginationParams()

        # Base query - user's records
        query = select(FinancialRecord).where(FinancialRecord.user_id == user_id)

        # Apply filters
        if not filters.include_deleted:
            query = query.where(FinancialRecord.is_deleted == False)

        if filters.type:
            query = query.where(FinancialRecord.type == filters.type.value)

        if filters.category:
            query = query.where(FinancialRecord.category == filters.category.lower())

        if filters.status:
            query = query.where(FinancialRecord.status == filters.status.value)

        if filters.date_from:
            query = query.where(FinancialRecord.record_date >= filters.date_from)

        if filters.date_to:
            query = query.where(FinancialRecord.record_date <= filters.date_to)

        if filters.min_amount is not None:
            query = query.where(FinancialRecord.amount >= filters.min_amount)

        if filters.max_amount is not None:
            query = query.where(FinancialRecord.amount <= filters.max_amount)

        if filters.search:
            query = query.where(
                FinancialRecord.description.ilike(f"%{filters.search}%")
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_items = self.db.scalar(count_query) or 0

        # Apply sorting
        sort_column = getattr(FinancialRecord, pagination.sort_by, FinancialRecord.record_date)
        if pagination.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (pagination.page - 1) * pagination.per_page
        query = query.offset(offset).limit(pagination.per_page)

        # Execute query
        records = list(self.db.scalars(query).all())

        # Calculate pagination metadata
        total_pages = (total_items + pagination.per_page - 1) // pagination.per_page
        
        return RecordListResponse(
            items=[self._to_response(r) for r in records],
            pagination=PaginationMeta(
                page=pagination.page,
                per_page=pagination.per_page,
                total_items=total_items,
                total_pages=total_pages,
                has_next=pagination.page < total_pages,
                has_prev=pagination.page > 1,
            ),
        )

    def _to_response(self, record: FinancialRecord) -> RecordResponse:
        """Convert a FinancialRecord to RecordResponse schema."""
        return RecordResponse(
            id=record.id,
            user_id=record.user_id,
            amount=record.amount,
            type=record.type,
            category=record.category,
            description=record.description,
            record_date=record.record_date,
            status=record.status,
            is_deleted=record.is_deleted,
            created_at=record.created_at.isoformat() if record.created_at else None,
            updated_at=record.updated_at.isoformat() if record.updated_at else None,
        )


def get_record_service(db: Session) -> RecordService:
    """Factory function to create RecordService instance."""
    return RecordService(db)
