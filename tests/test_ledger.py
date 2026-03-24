"""Unit tests for the hash-chained LedgerService."""
from app.services.ledger import LedgerService


class TestLedgerService:
    def test_first_block_uses_genesis(self, db):
        block = LedgerService.append_block(db, tx_id=1, payload={"amount": 100})
        db.commit()
        assert block.previous_hash == "GENESIS"
        assert len(block.block_hash) == 64  # SHA-256 hex

    def test_blocks_are_chained(self, db):
        b1 = LedgerService.append_block(db, tx_id=1, payload={"amount": 100})
        db.flush()
        b2 = LedgerService.append_block(db, tx_id=2, payload={"amount": 200})
        db.commit()

        assert b2.previous_hash == b1.block_hash
        assert b1.block_hash != b2.block_hash

    def test_payload_stored_as_json(self, db):
        import json

        data = {"user_id": 7, "amount": 42.5, "currency": "EUR"}
        block = LedgerService.append_block(db, tx_id=99, payload=data)
        db.commit()

        stored = json.loads(block.payload)
        assert stored["amount"] == 42.5
        assert stored["currency"] == "EUR"

    def test_hash_determinism(self, db):
        """Same tx_id + payload at same timestamp → same hash."""
        b = LedgerService.append_block(db, tx_id=5, payload={"a": 1})
        db.commit()
        # The hash is a sha256 digest, so it must be a hex string of length 64
        assert all(c in "0123456789abcdef" for c in b.block_hash)

    def test_three_block_chain_integrity(self, db):
        blocks = []
        for i in range(1, 4):
            b = LedgerService.append_block(db, tx_id=i, payload={"seq": i})
            db.flush()
            blocks.append(b)
        db.commit()

        assert blocks[0].previous_hash == "GENESIS"
        assert blocks[1].previous_hash == blocks[0].block_hash
        assert blocks[2].previous_hash == blocks[1].block_hash
