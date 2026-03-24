"""
Prometheus metrics configuration for OpenCredit.

Provides:
- HTTP request metrics (count, duration, in-progress)
- Custom business metrics (transactions, fraud, credit)
- /metrics endpoint for Prometheus scraping
"""

import logging
from typing import Callable

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram

from app.core.config import settings


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Custom Business Metrics
# ─────────────────────────────────────────────────────────────────────────────

# Transaction metrics
TRANSACTIONS_TOTAL = Counter(
    "opencredit_transactions_total",
    "Total number of transactions processed",
    ["status", "category", "currency"],
)

TRANSACTION_AMOUNT = Histogram(
    "opencredit_transaction_amount_dollars",
    "Transaction amounts in dollars",
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)

# Fraud metrics
FRAUD_DECISIONS = Counter(
    "opencredit_fraud_decisions_total",
    "Fraud detection decisions",
    ["decision"],  # approved, flagged, rejected
)

FRAUD_SCORE = Histogram(
    "opencredit_fraud_score",
    "Fraud score distribution",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# Credit metrics
CREDIT_UTILIZATION = Gauge(
    "opencredit_credit_utilization_ratio",
    "Current credit utilization ratio (used/limit)",
    ["user_id"],
)

AVAILABLE_CREDIT = Gauge(
    "opencredit_available_credit_total",
    "Total available credit across all users",
)

# User metrics
ACTIVE_USERS = Gauge(
    "opencredit_active_users_total",
    "Total number of active users",
)

ACTIVE_MERCHANTS = Gauge(
    "opencredit_active_merchants_total",
    "Total number of active merchants",
)

# Authentication metrics
AUTH_ATTEMPTS = Counter(
    "opencredit_auth_attempts_total",
    "Authentication attempts",
    ["type", "result"],  # type: login/register, result: success/failure
)


# ─────────────────────────────────────────────────────────────────────────────
# Metric Recording Functions
# ─────────────────────────────────────────────────────────────────────────────


def record_transaction(status: str, category: str, currency: str, amount: float) -> None:
    """Record a transaction in metrics."""
    TRANSACTIONS_TOTAL.labels(status=status, category=category, currency=currency).inc()
    TRANSACTION_AMOUNT.observe(amount)


def record_fraud_decision(decision: str, score: float) -> None:
    """Record a fraud detection decision."""
    FRAUD_DECISIONS.labels(decision=decision).inc()
    FRAUD_SCORE.observe(score)


def record_auth_attempt(auth_type: str, success: bool) -> None:
    """Record an authentication attempt."""
    result = "success" if success else "failure"
    AUTH_ATTEMPTS.labels(type=auth_type, result=result).inc()


def update_credit_metrics(user_id: int, available: float, limit: float) -> None:
    """Update credit utilization metrics for a user."""
    if limit > 0:
        utilization = (limit - available) / limit
        CREDIT_UTILIZATION.labels(user_id=str(user_id)).set(utilization)


# ─────────────────────────────────────────────────────────────────────────────
# Prometheus FastAPI Integration
# ─────────────────────────────────────────────────────────────────────────────


def setup_metrics(app: FastAPI) -> None:
    """
    Set up Prometheus metrics instrumentation.
    
    Adds:
    - HTTP request metrics (automatic via instrumentator)
    - /metrics endpoint for Prometheus scraping
    - Custom business metrics
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        from prometheus_fastapi_instrumentator.metrics import Info

        # Create instrumentator with custom settings
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health", "/ready"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="opencredit_http_requests_inprogress",
            inprogress_labels=True,
        )

        # Add default metrics
        instrumentator.add(
            default_metrics_with_info()
        )

        # Instrument the app
        instrumentator.instrument(app)

        # Expose /metrics endpoint
        instrumentator.expose(
            app,
            endpoint="/metrics",
            include_in_schema=True,
            tags=["monitoring"],
        )

        logger.info("Prometheus metrics enabled at /metrics")

    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed, metrics disabled")
    except Exception as e:
        logger.error(f"Failed to setup metrics: {e}")


def default_metrics_with_info() -> Callable:
    """
    Return a callable that adds default metrics with app info.
    """
    def instrumentation(info: Info) -> None:
        # This is called for each request
        # We can add custom logic here if needed
        pass
    
    return instrumentation
