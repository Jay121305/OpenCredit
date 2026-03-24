"""
Middleware components for OpenCredit.

Includes:
- Security headers middleware
- Request ID middleware
- Exception handling middleware
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import OpenCreditError


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Request Context
# ─────────────────────────────────────────────────────────────────────────────

# Thread-local storage for request context (for logging)
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request ID."""
    return request_id_var.get()


# ─────────────────────────────────────────────────────────────────────────────
# Security Headers Middleware
# ─────────────────────────────────────────────────────────────────────────────


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Cache-Control: no-store (for API responses)
    - Content-Security-Policy: default-src 'self'
    
    In production (ENV != 'dev'):
    - Strict-Transport-Security (HSTS)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Core security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Prevent caching of API responses
        if request.url.path.startswith(settings.api_prefix):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        # Content Security Policy (relaxed for API, strict for HTML)
        if "text/html" in response.headers.get("content-type", ""):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )

        # HSTS in production only (requires HTTPS)
        if settings.env not in ("dev", "test"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Remove server identification headers
        response.headers.pop("server", None)

        return response


# ─────────────────────────────────────────────────────────────────────────────
# Request ID Middleware
# ─────────────────────────────────────────────────────────────────────────────


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Adds a unique request ID to each request for tracing.
    
    The request ID is:
    - Generated as a UUID v4
    - Stored in context var for logging
    - Returned in X-Request-ID response header
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Use provided request ID or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Store in context var for logging
        token = request_id_var.set(request_id)
        
        # Store in request state for easy access
        request.state.request_id = request_id

        try:
            # Log request start
            logger.info(
                "Request started",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )

            start_time = time.perf_counter()
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add request ID to response
            response.headers["X-Request-ID"] = request_id

            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )

            return response
        finally:
            request_id_var.reset(token)


# ─────────────────────────────────────────────────────────────────────────────
# Exception Handler Middleware
# ─────────────────────────────────────────────────────────────────────────────


async def opencredit_exception_handler(request: Request, exc: OpenCreditError) -> JSONResponse:
    """
    Handle OpenCredit custom exceptions with consistent response format.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the error
    logger.error(
        f"OpenCredit error: {exc.error_code}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with consistent response format.
    Hides internal error details in production.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log full error details
    logger.exception(
        f"Unexpected error: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
        }
    )

    # Hide internal details in production
    if settings.env in ("dev", "test"):
        message = str(exc)
        details = {"exception_type": type(exc).__name__}
    else:
        message = "An internal error occurred"
        details = {}

    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": message,
            "details": details,
            "request_id": request_id,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting Setup
# ─────────────────────────────────────────────────────────────────────────────


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Set up rate limiting using slowapi.
    
    Rate limits are configured per-endpoint type:
    - Auth endpoints: 5/minute (prevent brute force)
    - Payment endpoints: 100/minute (business limit)
    - Other endpoints: 60/minute (general protection)
    """
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded

        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        logger.info("Rate limiting enabled")
    except ImportError:
        logger.warning("slowapi not installed, rate limiting disabled")


def get_limiter():
    """Get the rate limiter instance."""
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        return Limiter(key_func=get_remote_address)
    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Middleware Registration
# ─────────────────────────────────────────────────────────────────────────────


def setup_middleware(app: FastAPI) -> None:
    """
    Register all middleware in the correct order.
    
    Order matters! Middleware is executed in reverse order:
    1. RequestIdMiddleware (first to run, last to complete)
    2. SecurityHeadersMiddleware
    3. CORS (if enabled)
    4. Rate limiting
    """
    from fastapi.middleware.cors import CORSMiddleware

    # CORS middleware (must be added before security headers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID (should be outermost)
    app.add_middleware(RequestIdMiddleware)

    # Rate limiting
    setup_rate_limiting(app)

    # Exception handlers
    app.add_exception_handler(OpenCreditError, opencredit_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Middleware configured successfully")
