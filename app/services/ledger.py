"""
Hash-Chained Ledger Service (Blockchain-Style Audit Trail)
==========================================================

This module implements an immutable, tamper-evident ledger using SHA-256
cryptographic hashing. Each transaction creates a "block" that links to
the previous block via its hash, forming an unbreakable chain.

How It Works:
    1. New transaction is processed
    2. Fetch the latest block's hash (or "GENESIS" for first block)
    3. Combine: transaction_id | timestamp | previous_hash | payload
    4. Hash with SHA-256 to create block_hash
    5. Store block with both previous_hash and block_hash

Security Properties:
    - Tamper-Evident: Changing any block invalidates all subsequent hashes
    - Immutable: Historical records cannot be altered without detection
    - Verifiable: Entire chain can be verified by recomputing hashes

Example Chain:
    Block 1: hash=abc123, prev=GENESIS
    Block 2: hash=def456, prev=abc123  (linked to Block 1)
    Block 3: hash=ghi789, prev=def456  (linked to Block 2)

Note: This is NOT a distributed blockchain. It's a centralized audit log
using blockchain's hash-chain concept for data integrity.
"""

import hashlib
import json
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.ledger import LedgerBlock


class LedgerService:
    """Service for managing the hash-chained transaction ledger."""
    
    @staticmethod
    def append_block(db: Session, tx_id: int, payload: dict) -> LedgerBlock:
        """
        Create a new block linked to the previous block via hash chain.
        
        Args:
            db: Database session
            tx_id: Transaction ID this block records
            payload: Transaction data to store (amount, status, etc.)
            
        Returns:
            LedgerBlock: The newly created block with computed hash
            
        Algorithm:
            raw_string = "{tx_id}|{timestamp}|{previous_hash}|{payload_json}"
            block_hash = SHA256(raw_string)
        """
        # Step 1: Get previous block's hash (or GENESIS for first block)
        previous_block = db.scalar(select(LedgerBlock).order_by(desc(LedgerBlock.id)).limit(1))
        previous_hash = previous_block.block_hash if previous_block else "GENESIS"
        
        # Step 2: Prepare payload as sorted JSON for consistency
        payload_json = json.dumps(payload, sort_keys=True)
        created_at = datetime.utcnow()
        
        # Step 3: Create raw string and compute SHA-256 hash
        raw = f"{tx_id}|{created_at.isoformat()}|{previous_hash}|{payload_json}"
        block_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # Step 4: Create and persist the block
        block = LedgerBlock(
            transaction_id=tx_id,
            created_at=created_at,
            previous_hash=previous_hash,
            payload=payload_json,
            block_hash=block_hash,
        )
        db.add(block)
        return block
