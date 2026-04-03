import hashlib
import json
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.ledger import LedgerBlock


class LedgerService:
    @staticmethod
    def append_block(db: Session, tx_id: int, payload: dict) -> LedgerBlock:
        previous_block = db.scalar(select(LedgerBlock).order_by(desc(LedgerBlock.id)).limit(1))
        previous_hash = previous_block.block_hash if previous_block else "GENESIS"
        payload_json = json.dumps(payload, sort_keys=True)
        created_at = datetime.utcnow()
        raw = f"{tx_id}|{created_at.isoformat()}|{previous_hash}|{payload_json}"
        block_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        block = LedgerBlock(
            transaction_id=tx_id,
            created_at=created_at,
            previous_hash=previous_hash,
            payload=payload_json,
            block_hash=block_hash,
        )
        db.add(block)
        return block
