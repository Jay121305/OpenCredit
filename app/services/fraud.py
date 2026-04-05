"""
Fraud Detection Engine with Machine Learning
=============================================

This module implements real-time fraud scoring for payment transactions using
a combination of rule-based checks and machine learning (Isolation Forest).

Scoring Factors:
    1. High-Value Check: Flags transactions above threshold (default $5,000)
    2. Velocity Check: Flags rapid successive transactions (5+ in 60 seconds)
    3. Geo-Mismatch: Flags location changes between transactions
    4. ML Model: Anomaly detection using Isolation Forest algorithm

Decision Thresholds:
    - score < 0.50: APPROVED (low risk)
    - score 0.50-0.75: FLAGGED (manual review required)
    - score >= 0.75: REJECTED (high risk)

All thresholds and weights are configurable via environment variables.

Example:
    >>> engine = FraudEngine()
    >>> decision = engine.evaluate(db, user_id=1, amount=6000.0, geo="US")
    >>> print(decision.score, decision.decision)
    0.52 flagged
"""

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
    """
    Fraud evaluation result.
    
    Attributes:
        score: Risk score between 0.0 (safe) and 1.0 (high risk)
        decision: One of 'approved', 'flagged', or 'rejected'
    """
    score: float
    decision: str


class FraudEngine:
    """
    ML-powered fraud detection engine.
    
    Uses Isolation Forest algorithm trained on synthetic normal transaction
    patterns to detect anomalies. Combined with rule-based checks for
    comprehensive fraud scoring.
    """
    def __init__(self) -> None:
        """
        Initialize the fraud engine with ML model.
        
        The Isolation Forest model is trained on synthetic data representing
        normal transaction patterns (mean amount ~$120, ~2 transactions/minute).
        Contamination rate of 4% means ~4% of normal transactions may trigger.
        """
        self.model = None
        if IsolationForest is not None and np is not None:
            rng = np.random.RandomState(42)
            # Synthetic training data: [amount, transaction_count]
            # Normal: ~$120 avg amount, ~2 transactions per minute
            train = rng.normal(loc=[120.0, 2.0], scale=[40.0, 1.0], size=(400, 2))
            self.model = IsolationForest(contamination=0.04, random_state=42)
            self.model.fit(train)

    def evaluate(self, db: Session, user_id: int, amount: float, geo: str) -> FraudDecision:
        """
        Evaluate a transaction for fraud risk.
        
        Args:
            db: Database session for querying transaction history
            user_id: ID of the user making the transaction
            amount: Transaction amount in dollars
            geo: Geographic location code (e.g., 'US', 'UK')
            
        Returns:
            FraudDecision with risk score (0.0-1.0) and decision string
            
        Scoring Breakdown:
            - High-value (>$5000): +0.45 points
            - Velocity (5+ txn/min): +0.25 points  
            - Geo-mismatch: +0.10 points
            - ML anomaly: up to +0.30 points
        """
        score = 0.0

        # Factor 1: High-value transaction check (configurable weight)
        if amount >= settings.high_value_threshold:
            score += settings.fraud_weight_high_value

        # Factor 2: Velocity check - too many transactions in short window
        window_start = datetime.utcnow() - timedelta(seconds=settings.velocity_window_seconds)
        recent_count = db.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == user_id, Transaction.created_at >= window_start
            )
        )
        if recent_count and recent_count >= settings.velocity_max_txn_count:
            score += settings.fraud_weight_velocity

        # Factor 3: Geo-mismatch - location changed from last transaction
        last_geo = db.scalar(
            select(Transaction.geo)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        if last_geo and last_geo != geo:
            score += settings.fraud_weight_geo_mismatch

        # Factor 4: ML model anomaly detection
        if self.model is not None and np is not None:
            features = np.array([[amount, float(recent_count or 0)]])
            # Negative decision_function = anomaly, positive = normal
            model_signal = self.model.decision_function(features)[0]
            score += float(max(0.0, min(settings.fraud_weight_ml_max, -model_signal)))

        # Final decision based on configurable thresholds
        if score >= settings.fraud_threshold_reject:
            decision = "rejected"
        elif score >= settings.fraud_threshold_flag:
            decision = "flagged"
        else:
            decision = "approved"
        return FraudDecision(score=round(min(score, 0.99), 4), decision=decision)
