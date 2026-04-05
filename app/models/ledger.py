"""
Ledger Block Model - Hash-Chained Audit Trail
==============================================

Each block represents an immutable record of a transaction, cryptographically
linked to the previous block via SHA-256 hashing.

Chain Structure:
    Block 1: prev="GENESIS", hash="abc123"
    Block 2: prev="abc123", hash="def456"
    Block 3: prev="def456", hash="ghi789"

Fields:
    - transaction_id: Links to the transaction being recorded
    - previous_hash: Hash of the preceding block (or "GENESIS")
    - payload: JSON data about the transaction
    - block_hash: SHA-256 hash of this block's content
    - created_at: Timestamp of block creation

Security:
    Modifying any field (including payload) would change the block_hash,
    which would break the chain link with subsequent blocks.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LedgerBlock(Base):
    """
    Immutable ledger block for transaction audit trail.
    
    Each block's hash incorporates the previous block's hash,
    creating a tamper-evident chain similar to blockchain.
    """
    
    __tablename__ = "ledger_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # "GENESIS" or previous block's hash
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON transaction data
    block_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)  # SHA-256
