#!/bin/bash
# =============================================================================
# Render.com Startup Script
# =============================================================================
# This script runs database migrations before starting the server
# =============================================================================

set -e  # Exit on error

echo "🚀 Starting OpenCredit API deployment..."

# Run database migrations
echo "📊 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete!"

# Start the FastAPI server
echo "🌐 Starting API server on port ${PORT:-8000}..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --log-level info
