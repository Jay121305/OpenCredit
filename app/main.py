"""
OpenCredit - Production-Grade Fintech Backend
==============================================

This is the main FastAPI application entry point. It initializes:
- Middleware (CORS, rate limiting, request logging)
- Metrics collection (Prometheus-compatible)
- Static file serving (dashboard UI)
- All API route handlers

API Prefix: /api/v1

Route Modules:
    - auth: User registration, login, profile
    - merchants: Merchant management, API keys
    - payments: Payment processing with fraud detection
    - analytics: Spending summaries and insights
    - records: Financial records CRUD
    - dashboard: Dashboard summary data
    - users: User management (admin)
    - mfa: Multi-factor authentication
    - kyc: Know Your Customer verification
    - webhooks: Webhook endpoint management
    - refunds: Refund processing
    - disputes: Dispute management
    - fx: Foreign exchange rates
    - ledger: Hash-chained audit trail

Run:
    uvicorn app.main:app --reload
    
Docs:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    analytics,
    auth,
    dashboard,
    disputes,
    fx,
    health,
    kyc,
    ledger,
    merchants,
    mfa,
    payments,
    records,
    refunds,
    users,
    webhooks,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import setup_middleware
from app.db.base import Base
from app.db.session import engine


# Initialize logging
configure_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Production-style digital credit and payment infrastructure platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware Setup ─────────────────────────────────────────────
setup_middleware(app)

# ── Metrics Setup ────────────────────────────────────────────────
setup_metrics(app)

# ── Static files & frontend ──────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend() -> HTMLResponse:
    """Serve the main dashboard UI."""
    content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Startup ───────────────────────────────────────────────────
@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(merchants.router, prefix=settings.api_prefix)
app.include_router(payments.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(records.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(mfa.router, prefix=settings.api_prefix)
app.include_router(kyc.router, prefix=settings.api_prefix)
app.include_router(webhooks.router, prefix=settings.api_prefix)
app.include_router(refunds.router, prefix=settings.api_prefix)
app.include_router(refunds.chargeback_router, prefix=settings.api_prefix)
app.include_router(disputes.router, prefix=settings.api_prefix)
app.include_router(fx.router, prefix=settings.api_prefix)
app.include_router(ledger.router, prefix=settings.api_prefix)
