"""
Ledger API routes - Hash-chained audit trail.

Endpoints:
- GET /ledger              List ledger blocks with pagination
- GET /ledger/{block_id}   Get specific block details
- GET /ledger/verify       Verify ledger integrity
- GET /ledger/stats        Get ledger statistics
"""

import hashlib
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_viewer_user, get_current_analyst_user
from app.db.session import get_db
from app.models.ledger import LedgerBlock
from app.models.user import User


class LedgerBlockResponse(BaseModel):
    """Single ledger block."""
    id: int
    transaction_id: int
    created_at: str
    previous_hash: str
    block_hash: str
    payload: dict
    
    class Config:
        from_attributes = True


class LedgerListResponse(BaseModel):
    """Paginated list of ledger blocks."""
    blocks: List[LedgerBlockResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class LedgerVerifyResponse(BaseModel):
    """Ledger integrity verification result."""
    is_valid: bool
    total_blocks: int
    verified_blocks: int
    first_invalid_block: Optional[int] = None
    error_message: Optional[str] = None


class LedgerStatsResponse(BaseModel):
    """Ledger statistics."""
    total_blocks: int
    first_block_date: Optional[str] = None
    last_block_date: Optional[str] = None
    chain_hash: str  # Hash of the latest block


router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get("", response_model=LedgerListResponse, summary="List ledger blocks")
def list_ledger_blocks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    transaction_id: Optional[int] = Query(None, description="Filter by transaction ID"),
    user: User = Depends(get_current_viewer_user),
    db: Session = Depends(get_db),
) -> LedgerListResponse:
    """Get paginated list of ledger blocks (most recent first)."""
    query = select(LedgerBlock)
    count_query = select(func.count(LedgerBlock.id))
    
    if transaction_id:
        query = query.where(LedgerBlock.transaction_id == transaction_id)
        count_query = count_query.where(LedgerBlock.transaction_id == transaction_id)
    
    total = db.scalar(count_query) or 0
    total_pages = (total + per_page - 1) // per_page
    
    blocks = db.scalars(
        query.order_by(desc(LedgerBlock.id))
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    
    return LedgerListResponse(
        blocks=[
            LedgerBlockResponse(
                id=b.id,
                transaction_id=b.transaction_id,
                created_at=b.created_at.isoformat(),
                previous_hash=b.previous_hash,
                block_hash=b.block_hash,
                payload=json.loads(b.payload) if b.payload else {},
            )
            for b in blocks
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=LedgerStatsResponse, summary="Get ledger statistics")
def get_ledger_stats(
    user: User = Depends(get_current_viewer_user),
    db: Session = Depends(get_db),
) -> LedgerStatsResponse:
    """Get ledger chain statistics."""
    total = db.scalar(select(func.count(LedgerBlock.id))) or 0
    
    first_block = db.scalar(select(LedgerBlock).order_by(LedgerBlock.id).limit(1))
    last_block = db.scalar(select(LedgerBlock).order_by(desc(LedgerBlock.id)).limit(1))
    
    return LedgerStatsResponse(
        total_blocks=total,
        first_block_date=first_block.created_at.isoformat() if first_block else None,
        last_block_date=last_block.created_at.isoformat() if last_block else None,
        chain_hash=last_block.block_hash if last_block else "GENESIS",
    )


@router.get("/verify", response_model=LedgerVerifyResponse, summary="Verify ledger integrity")
def verify_ledger_integrity(
    user: User = Depends(get_current_analyst_user),
    db: Session = Depends(get_db),
) -> LedgerVerifyResponse:
    """
    Verify the integrity of the entire ledger chain.
    Checks that each block's hash is correctly computed and links to the previous block.
    """
    blocks = db.scalars(select(LedgerBlock).order_by(LedgerBlock.id)).all()
    
    if not blocks:
        return LedgerVerifyResponse(
            is_valid=True,
            total_blocks=0,
            verified_blocks=0,
        )
    
    verified = 0
    expected_previous = "GENESIS"
    
    for block in blocks:
        # Check previous hash link
        if block.previous_hash != expected_previous:
            return LedgerVerifyResponse(
                is_valid=False,
                total_blocks=len(blocks),
                verified_blocks=verified,
                first_invalid_block=block.id,
                error_message=f"Block {block.id}: Previous hash mismatch. Expected {expected_previous[:16]}..., got {block.previous_hash[:16]}...",
            )
        
        # Recompute and verify block hash
        raw = f"{block.transaction_id}|{block.created_at.isoformat()}|{block.previous_hash}|{block.payload}"
        computed_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        
        if computed_hash != block.block_hash:
            return LedgerVerifyResponse(
                is_valid=False,
                total_blocks=len(blocks),
                verified_blocks=verified,
                first_invalid_block=block.id,
                error_message=f"Block {block.id}: Hash verification failed. Data may have been tampered.",
            )
        
        verified += 1
        expected_previous = block.block_hash
    
    return LedgerVerifyResponse(
        is_valid=True,
        total_blocks=len(blocks),
        verified_blocks=verified,
    )


@router.get("/{block_id}", response_model=LedgerBlockResponse, summary="Get block details")
def get_ledger_block(
    block_id: int,
    user: User = Depends(get_current_viewer_user),
    db: Session = Depends(get_db),
) -> LedgerBlockResponse:
    """Get details of a specific ledger block."""
    block = db.scalar(select(LedgerBlock).where(LedgerBlock.id == block_id))
    
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ledger block not found",
        )
    
    return LedgerBlockResponse(
        id=block.id,
        transaction_id=block.transaction_id,
        created_at=block.created_at.isoformat(),
        previous_hash=block.previous_hash,
        block_hash=block.block_hash,
        payload=json.loads(block.payload) if block.payload else {},
    )
