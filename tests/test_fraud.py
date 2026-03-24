"""Unit tests for the FraudEngine."""
from unittest.mock import MagicMock
from app.services.fraud import FraudEngine


class TestFraudEngine:
    def setup_method(self):
        self.engine = FraudEngine()

    def _mock_db(self, recent_count=0, last_geo=None):
        """Return a mock DB session that stubs the scalar queries."""
        db = MagicMock()
        db.scalar = MagicMock(side_effect=[recent_count, last_geo])
        return db

    def test_low_amount_approved(self):
        db = self._mock_db(recent_count=0, last_geo="US")
        result = self.engine.evaluate(db, user_id=1, amount=50.0, geo="US")
        assert result.decision == "approved"
        assert result.score < 0.5

    def test_high_value_increases_score(self):
        db = self._mock_db(recent_count=0, last_geo="US")
        result = self.engine.evaluate(db, user_id=1, amount=6000.0, geo="US")
        assert result.score >= 0.45

    def test_velocity_breach_increases_score(self):
        db = self._mock_db(recent_count=10, last_geo="US")
        result = self.engine.evaluate(db, user_id=1, amount=100.0, geo="US")
        assert result.score >= 0.25

    def test_geo_change_increases_score(self):
        db = self._mock_db(recent_count=0, last_geo="US")
        result = self.engine.evaluate(db, user_id=1, amount=100.0, geo="NG")
        assert result.score >= 0.1

    def test_combined_flags_rejected(self):
        """High-value + velocity + geo change → should be rejected."""
        db = self._mock_db(recent_count=10, last_geo="US")
        result = self.engine.evaluate(db, user_id=1, amount=6000.0, geo="NG")
        assert result.decision in {"flagged", "rejected"}
        assert result.score >= 0.5

    def test_score_capped_at_099(self):
        db = self._mock_db(recent_count=100, last_geo="JP")
        result = self.engine.evaluate(db, user_id=1, amount=99999.0, geo="BR")
        assert result.score <= 0.99
