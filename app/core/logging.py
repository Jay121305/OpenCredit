"""
Structured logging configuration for OpenCredit.

Provides JSON-formatted logs in production and human-readable logs
in development. Includes request correlation via request IDs.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for production use.
    
    Outputs logs as single-line JSON objects for easy parsing
    by log aggregation systems (ELK, Datadog, CloudWatch, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields (request_id, user_id, etc.)
        for key in ("request_id", "user_id", "method", "path", "status_code", 
                    "duration_ms", "client_ip", "error_code", "details"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Add any other extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in (
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "pathname", "process", "processName", "relativeCreated",
                    "stack_info", "exc_info", "exc_text", "thread", "threadName",
                    "message", "request_id", "user_id", "method", "path",
                    "status_code", "duration_ms", "client_ip", "error_code", "details"
                ):
                    if not key.startswith("_"):
                        log_data[key] = value

        return json.dumps(log_data, default=str)


class DevFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    
    Includes colors and structured layout for easy reading.
    """

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Build base message
        base = f"{timestamp} {color}{record.levelname:8}{self.RESET} [{record.name}] {record.getMessage()}"

        # Add request_id if present
        if hasattr(record, "request_id") and record.request_id:
            base = f"{timestamp} {color}{record.levelname:8}{self.RESET} [{record.request_id[:8]}] [{record.name}] {record.getMessage()}"

        # Add extra fields
        extras = []
        for key in ("method", "path", "status_code", "duration_ms", "client_ip", "error_code"):
            if hasattr(record, key):
                extras.append(f"{key}={getattr(record, key)}")
        
        if extras:
            base += f" | {' '.join(extras)}"

        # Add exception info
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def configure_logging() -> None:
    """
    Configure application logging based on environment.
    
    - Production (ENV != 'dev'): JSON format for log aggregation
    - Development (ENV == 'dev'): Human-readable colored output
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Set formatter based on environment
    if settings.env in ("dev", "test"):
        formatter = DevFormatter()
    else:
        formatter = JSONFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured",
        extra={
            "environment": settings.env,
            "format": "json" if settings.env not in ("dev", "test") else "dev",
        }
    )
