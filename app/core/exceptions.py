"""
Custom exception classes for OpenCredit.

These exceptions provide structured error handling with consistent
error codes and messages across the application.
"""

from typing import Any


class OpenCreditError(Exception):
    """Base exception for all OpenCredit errors."""

    error_code: str = "OPENCREDIT_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Authentication & Authorization Errors
# ─────────────────────────────────────────────────────────────────────────────


class AuthenticationError(OpenCreditError):
    """Raised when authentication fails."""

    error_code = "AUTHENTICATION_FAILED"
    status_code = 401
    message = "Authentication failed"


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    error_code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or expired."""

    error_code = "INVALID_TOKEN"
    message = "Invalid or expired token"


class InsufficientPermissionsError(OpenCreditError):
    """Raised when user lacks required permissions."""

    error_code = "INSUFFICIENT_PERMISSIONS"
    status_code = 403
    message = "You do not have permission to perform this action"


# ─────────────────────────────────────────────────────────────────────────────
# Credit & Payment Errors
# ─────────────────────────────────────────────────────────────────────────────


class InsufficientCreditError(OpenCreditError):
    """Raised when user doesn't have enough credit for a transaction."""

    error_code = "INSUFFICIENT_CREDIT"
    status_code = 400
    message = "Insufficient credit available"

    def __init__(self, available: float, required: float) -> None:
        super().__init__(
            message=f"Insufficient credit: {available:.2f} available, {required:.2f} required",
            details={"available_credit": available, "required_amount": required},
        )


class CreditAccountNotFoundError(OpenCreditError):
    """Raised when credit account doesn't exist for user."""

    error_code = "CREDIT_ACCOUNT_NOT_FOUND"
    status_code = 404
    message = "Credit account not found"


class TransactionLimitExceededError(OpenCreditError):
    """Raised when transaction amount exceeds maximum allowed."""

    error_code = "TRANSACTION_LIMIT_EXCEEDED"
    status_code = 400
    message = "Transaction amount exceeds maximum limit"

    def __init__(self, amount: float, max_amount: float) -> None:
        super().__init__(
            message=f"Transaction amount {amount:.2f} exceeds maximum {max_amount:.2f}",
            details={"amount": amount, "max_amount": max_amount},
        )


class DuplicateTransactionError(OpenCreditError):
    """Raised when idempotency key has already been used."""

    error_code = "DUPLICATE_TRANSACTION"
    status_code = 409
    message = "Transaction with this idempotency key already exists"


# ─────────────────────────────────────────────────────────────────────────────
# Fraud Errors
# ─────────────────────────────────────────────────────────────────────────────


class FraudDetectedError(OpenCreditError):
    """Raised when transaction is rejected due to fraud detection."""

    error_code = "FRAUD_DETECTED"
    status_code = 403
    message = "Transaction rejected due to suspicious activity"

    def __init__(self, fraud_score: float, decision: str) -> None:
        super().__init__(
            message=f"Transaction {decision} due to fraud detection (score: {fraud_score:.2f})",
            details={"fraud_score": fraud_score, "decision": decision},
        )


class VelocityLimitExceededError(OpenCreditError):
    """Raised when user exceeds transaction velocity limits."""

    error_code = "VELOCITY_LIMIT_EXCEEDED"
    status_code = 429
    message = "Too many transactions in a short time period"


# ─────────────────────────────────────────────────────────────────────────────
# Merchant Errors
# ─────────────────────────────────────────────────────────────────────────────


class MerchantNotFoundError(OpenCreditError):
    """Raised when merchant doesn't exist."""

    error_code = "MERCHANT_NOT_FOUND"
    status_code = 404
    message = "Merchant not found"


class MerchantInactiveError(OpenCreditError):
    """Raised when merchant account is inactive."""

    error_code = "MERCHANT_INACTIVE"
    status_code = 403
    message = "Merchant account is inactive"


class InvalidApiKeyError(OpenCreditError):
    """Raised when merchant API key is invalid."""

    error_code = "INVALID_API_KEY"
    status_code = 401
    message = "Invalid or missing API key"


# ─────────────────────────────────────────────────────────────────────────────
# User Errors
# ─────────────────────────────────────────────────────────────────────────────


class UserNotFoundError(OpenCreditError):
    """Raised when user doesn't exist."""

    error_code = "USER_NOT_FOUND"
    status_code = 404
    message = "User not found"


class EmailAlreadyExistsError(OpenCreditError):
    """Raised when email is already registered."""

    error_code = "EMAIL_ALREADY_EXISTS"
    status_code = 400
    message = "Email address is already registered"


class InvalidPasswordError(OpenCreditError):
    """Raised when password doesn't meet requirements."""

    error_code = "INVALID_PASSWORD"
    status_code = 400
    message = "Password does not meet security requirements"


# ─────────────────────────────────────────────────────────────────────────────
# Validation Errors
# ─────────────────────────────────────────────────────────────────────────────


class ValidationError(OpenCreditError):
    """Raised when request validation fails."""

    error_code = "VALIDATION_ERROR"
    status_code = 422
    message = "Request validation failed"


class InvalidIdempotencyKeyError(ValidationError):
    """Raised when idempotency key format is invalid."""

    error_code = "INVALID_IDEMPOTENCY_KEY"
    message = "Idempotency key must be a valid UUID v4"


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting Errors
# ─────────────────────────────────────────────────────────────────────────────


class RateLimitExceededError(OpenCreditError):
    """Raised when rate limit is exceeded."""

    error_code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    message = "Rate limit exceeded. Please try again later."

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            details={"retry_after": retry_after},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure Errors
# ─────────────────────────────────────────────────────────────────────────────


class DatabaseError(OpenCreditError):
    """Raised when database operation fails."""

    error_code = "DATABASE_ERROR"
    status_code = 503
    message = "Database operation failed"


class RedisError(OpenCreditError):
    """Raised when Redis operation fails."""

    error_code = "REDIS_ERROR"
    status_code = 503
    message = "Cache service unavailable"


class ServiceUnavailableError(OpenCreditError):
    """Raised when a required service is unavailable."""

    error_code = "SERVICE_UNAVAILABLE"
    status_code = 503
    message = "Service temporarily unavailable"
