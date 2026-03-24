from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import analytics, auth, health, merchants, payments
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import setup_middleware
from app.db.base import Base
from app.db.session import engine


configure_logging()

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
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


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
