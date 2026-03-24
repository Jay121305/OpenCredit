"""
Health check endpoints for OpenCredit.

Provides:
- /health: Simple liveness probe
- /ready: Comprehensive readiness probe checking all dependencies
"""

import logging
import os
import platform
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db


logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


def check_database(db: Session) -> dict[str, Any]:
    """Check database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        from redis import Redis
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        start = datetime.now(timezone.utc)
        client.ping()
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        client.close()
        return {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def get_system_info() -> dict[str, Any]:
    """Get system resource information."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "cpu_count": os.cpu_count(),
        }
    except ImportError:
        return {
            "memory_percent": None,
            "disk_percent": None,
            "cpu_count": os.cpu_count(),
            "note": "Install psutil for detailed system metrics",
        }


@router.get("/health")
def health() -> dict[str, Any]:
    """
    Simple liveness probe.
    
    Returns 200 if the service is running. Used by load balancers
    and container orchestrators for basic health checking.
    
    Returns:
        dict: Status and timestamp
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.app_name,
        "version": "1.0.0",
    }


@router.get("/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Comprehensive readiness probe.
    
    Checks all dependencies (database, Redis) and returns detailed
    status. Used by Kubernetes for readiness probes.
    
    Returns:
        dict: Detailed health status of all components
    """
    checks = {
        "database": check_database(db),
        "redis": check_redis(),
    }

    # Determine overall status
    all_healthy = all(check.get("status") == "healthy" for check in checks.values())
    
    # Database is required, Redis is optional
    db_healthy = checks["database"].get("status") == "healthy"

    response = {
        "status": "ready" if db_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.app_name,
        "version": "1.0.0",
        "environment": settings.env,
        "checks": checks,
        "system": get_system_info(),
        "all_healthy": all_healthy,
    }

    return response


@router.get("/info")
def info() -> dict[str, Any]:
    """
    Service information endpoint.
    
    Returns non-sensitive configuration and environment info.
    Useful for debugging and monitoring.
    
    Returns:
        dict: Service configuration details
    """
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "environment": settings.env,
        "api_prefix": settings.api_prefix,
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": {
            "jwt_auth": True,
            "fraud_detection": True,
            "hash_chained_ledger": True,
            "event_streaming": True,
            "rate_limiting": True,
        },
    }
