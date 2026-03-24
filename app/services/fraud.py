from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transaction import Transaction

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover
    IsolationForest = None


@dataclass
class FraudDecision:
    score: float
    decision: str


class FraudEngine:
    def __init__(self) -> None:
        self.model = None
        if IsolationForest is not None and np is not None:
            rng = np.random.RandomState(42)
            train = rng.normal(loc=[120.0, 2.0], scale=[40.0, 1.0], size=(400, 2))
            self.model = IsolationForest(contamination=0.04, random_state=42)
            self.model.fit(train)

    def evaluate(self, db: Session, user_id: int, amount: float, geo: str) -> FraudDecision:
        score = 0.0

        # High-value transaction check (configurable weight)
        if amount >= settings.high_value_threshold:
            score += settings.fraud_weight_high_value

        # Velocity check (configurable weight)
        window_start = datetime.utcnow() - timedelta(seconds=settings.velocity_window_seconds)
        recent_count = db.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == user_id, Transaction.created_at >= window_start
            )
        )
        if recent_count and recent_count >= settings.velocity_max_txn_count:
            score += settings.fraud_weight_velocity

        # Geo-mismatch check (configurable weight)
        last_geo = db.scalar(
            select(Transaction.geo)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        if last_geo and last_geo != geo:
            score += settings.fraud_weight_geo_mismatch

        # ML model signal (configurable max contribution)
        if self.model is not None and np is not None:
            features = np.array([[amount, float(recent_count or 0)]])
            model_signal = self.model.decision_function(features)[0]
            score += float(max(0.0, min(settings.fraud_weight_ml_max, -model_signal)))

        # Decision based on configurable thresholds
        if score >= settings.fraud_threshold_reject:
            decision = "rejected"
        elif score >= settings.fraud_threshold_flag:
            decision = "flagged"
        else:
            decision = "approved"
        return FraudDecision(score=round(min(score, 0.99), 4), decision=decision)
