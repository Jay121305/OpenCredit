"""
API route exports.
"""

from app.api.routes import (
    analytics,
    auth,
    dashboard,
    disputes,
    fx,
    health,
    kyc,
    merchants,
    mfa,
    payments,
    records,
    refunds,
    users,
    webhooks,
)

__all__ = [
    "analytics",
    "auth",
    "dashboard",
    "disputes",
    "fx",
    "health",
    "kyc",
    "merchants",
    "mfa",
    "payments",
    "records",
    "refunds",
    "users",
    "webhooks",
]