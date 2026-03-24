# =============================================================================
# OpenCredit Production Dockerfile
# =============================================================================
# Multi-stage build for optimal image size and security
# Final image: ~200MB (vs ~1GB for full python image)
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder - Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Production - Minimal runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Labels for container metadata
LABEL org.opencontainers.image.title="OpenCredit API"
LABEL org.opencontainers.image.description="Digital credit and payment infrastructure platform"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="OpenCredit"

# Security: Run as non-root user
RUN groupadd --gid 1000 opencredit && \
    useradd --uid 1000 --gid opencredit --shell /bin/bash --create-home opencredit

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=opencredit:opencredit app ./app
COPY --chown=opencredit:opencredit alembic ./alembic
COPY --chown=opencredit:opencredit alembic.ini ./alembic.ini
COPY --chown=opencredit:opencredit scripts ./scripts
COPY --chown=opencredit:opencredit pyproject.toml ./pyproject.toml

# Switch to non-root user
USER opencredit

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: Development - With dev tools
# ─────────────────────────────────────────────────────────────────────────────
FROM production AS development

USER root

# Install dev dependencies
RUN pip install --no-cache-dir pytest httpx pytest-cov

USER opencredit

# Override command for development (with reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
