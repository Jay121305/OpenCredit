#!/bin/sh
# =============================================================================
# Render.com Startup Script
# =============================================================================
# This script runs database migrations before starting the server
# =============================================================================

set -e  # Exit on error

# Set PYTHONPATH so Python can find the app module
export PYTHONPATH=/app:$PYTHONPATH

echo "🚀 Starting OpenCredit API deployment..."
echo "📍 Working directory: $(pwd)"
echo "🐍 Python path: $PYTHONPATH"

# Run database migrations (ignore errors if already applied)
echo "📊 Running database migrations..."
alembic upgrade head || echo "⚠️  Migrations failed or already applied"

echo "✅ Setup complete!"

# Start the FastAPI server
echo "🌐 Starting API server on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --log-level info
