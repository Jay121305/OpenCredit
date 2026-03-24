# OpenCredit

OpenCredit is a production-style simulation of a digital credit and payment infrastructure platform.

## What Is Included

- FastAPI API layer for auth, merchant onboarding, payments, and analytics
- Payment orchestration with idempotency and atomic credit updates
- Fraud detection engine with rule checks and Isolation Forest signal
- Hash-chained transaction ledger for tamper-evident storage
- Redis Streams event pipeline and analytics worker
- PostgreSQL + Redis infrastructure via Docker Compose
- Comprehensive test suite (security, auth, merchants, payments, analytics, fraud, ledger)

## Architecture Snapshot

1. Client authenticates and receives JWT
2. Merchant signs requests with API key
3. Payment endpoint validates identity and request
4. Fraud engine scores transaction
5. Payment engine applies credit logic and status decision
6. Ledger service appends hash-linked block
7. Event bus publishes transaction event to Redis stream
8. Analytics worker consumes stream for downstream processing

```
                          ┌───────────────┐
                          │   Client App  │
                          └──────┬────────┘
                                 │  POST /api/v1/payments
                          ┌──────▼────────┐
                          │   FastAPI     │
                          │   (JWT + Key) │
                          └──┬───┬───┬────┘
                   ┌─────────┘   │   └──────────┐
             ┌─────▼─────┐  ┌───▼────┐   ┌─────▼──────┐
             │  Fraud     │  │ Payment│   │ Ledger     │
             │  Engine    │  │ Service│   │ Service    │
             └────────────┘  └───┬────┘   └────────────┘
                                 │
                          ┌──────▼────────┐
                          │ Event Bus     │─────► Redis Streams
                          └───────────────┘         │
                                              ┌─────▼─────┐
                                              │ Analytics  │
                                              │ Worker     │
                                              └────────────┘
```

## Project Structure

```
opencredit/
├── app/
│   ├── api/
│   │   ├── deps.py                  # Dependency injection (JWT, API-key)
│   │   └── routes/
│   │       ├── analytics.py         # GET  /api/v1/analytics/spending-summary
│   │       ├── auth.py              # POST /api/v1/auth/register & login
│   │       ├── health.py            # GET  /health
│   │       ├── merchants.py         # POST /api/v1/merchants
│   │       └── payments.py          # POST /api/v1/payments
│   ├── core/
│   │   ├── config.py                # Pydantic settings (env vars)
│   │   ├── logging.py               # Logging config
│   │   └── security.py              # JWT, password hashing, API keys
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy declarative base
│   │   └── session.py               # Engine & session factory
│   ├── models/
│   │   ├── credit.py                # CreditAccount
│   │   ├── ledger.py                # LedgerBlock (hash-chained)
│   │   ├── merchant.py              # Merchant
│   │   ├── transaction.py           # Transaction + status enum
│   │   └── user.py                  # User
│   ├── schemas/                     # Pydantic request / response schemas
│   ├── services/
│   │   ├── event_bus.py             # Redis Streams publisher
│   │   ├── fraud.py                 # Rule-based + ML fraud engine
│   │   ├── idempotency.py           # Redis-backed idempotency store
│   │   ├── ledger.py                # Append hash-chained blocks
│   │   └── payment.py              # Payment orchestration
│   ├── workers/
│   │   └── analytics_worker.py      # Redis Streams consumer
│   └── main.py                      # FastAPI app entry point
├── tests/
│   ├── conftest.py                  # Shared fixtures (DB, client, factories)
│   ├── test_analytics.py
│   ├── test_auth.py
│   ├── test_fraud.py
│   ├── test_health.py
│   ├── test_ledger.py
│   ├── test_merchants.py
│   ├── test_payments.py
│   └── test_security.py
├── .env.example                     # Template for environment variables
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Required Environment Variables / Secrets

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

| Variable | Default | Required | Description |
|---|---|---|---|
| `JWT_SECRET` | *none* | **Yes** | Must be ≥ 16 chars. Used to sign/verify JWTs. |
| `JWT_ALGORITHM` | `HS256` | No | HMAC algorithm for JWT signing |
| `JWT_EXPIRE_MINUTES` | `60` | No | JWT token lifetime in minutes |
| `DATABASE_URL` | `postgresql+psycopg://opencredit:opencredit@postgres:5432/opencredit` | Yes (Docker default works) | SQLAlchemy database URL |
| `REDIS_URL` | `redis://redis:6379/0` | Yes (Docker default works) | Redis connection URL |
| `APP_NAME` | `OpenCredit` | No | Application name shown in API docs |
| `ENV` | `dev` | No | Environment label (`dev`, `staging`, `prod`) |
| `API_PREFIX` | `/api/v1` | No | URL prefix for all API routes |
| `STREAM_NAME` | `opencredit.transactions` | No | Redis Streams key for transaction events |
| `IDEMPOTENCY_TTL_SECONDS` | `3600` | No | TTL for idempotency keys in Redis |
| `HIGH_VALUE_THRESHOLD` | `5000` | No | Amount ($) triggering high-value fraud flag |
| `VELOCITY_WINDOW_SECONDS` | `60` | No | Sliding window for velocity checks |
| `VELOCITY_MAX_TXN_COUNT` | `5` | No | Max transactions in window before flag |

> **⚠️ Production**: Generate a strong `JWT_SECRET` (`openssl rand -hex 32`) and use a proper PostgreSQL connection string with TLS.

## Run Locally (Docker)

1. Copy `.env.example` to `.env` and set `JWT_SECRET`:

```bash
cp .env.example .env
# edit .env and set JWT_SECRET=<your-secret>
```

2. Start the full stack:

```bash
docker compose up --build
```

3. API docs available at:

```
http://localhost:8000/docs
```

## Run Without Docker (Development)

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set env vars (SQLite for local dev)
set DATABASE_URL=sqlite:///./opencredit.db        # Windows
export DATABASE_URL=sqlite:///./opencredit.db      # macOS/Linux
set JWT_SECRET=dev-secret-at-least-sixteen
export JWT_SECRET=dev-secret-at-least-sixteen

# Run the API server
uvicorn app.main:app --reload --port 8000
```

> **Note**: Redis features (event bus, idempotency store) require a running Redis instance. Without it, the API still works but event publishing will log errors.

## Core Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | None | Register new user, returns JWT |
| `POST` | `/api/v1/auth/login` | None | Login, returns JWT |
| `POST` | `/api/v1/merchants` | **Admin JWT** | Create merchant, returns API key |
| `POST` | `/api/v1/payments` | JWT + `X-API-Key` | Process a payment |
| `GET` | `/api/v1/analytics/spending-summary` | JWT | Monthly spending summary |
| `GET` | `/health` | None | Simple liveness check |
| `GET` | `/ready` | None | Comprehensive readiness probe |
| `GET` | `/info` | None | Service information |

## Testing

```bash
# Run all tests (SQLite, no Docker needed)
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

The test suite uses an in-memory SQLite database and mocked services — **no Docker, Redis, or PostgreSQL required** to run tests.

## Database Migrations

This project uses Alembic for database migrations:

```bash
# Create a new migration (after model changes)
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Admin User Setup

Create the initial admin user (required for merchant management):

```bash
# Interactive mode
python -m scripts.seed_admin

# Non-interactive (for CI/CD)
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=SecurePass123! python -m scripts.seed_admin
```

## Production Features

### ✅ Security
- **Rate limiting** - Configurable per-endpoint limits (5/min for auth, 100/min for payments)
- **CORS** - Configurable allowed origins
- **Security headers** - X-Content-Type-Options, X-Frame-Options, CSP, HSTS (in prod)
- **Request ID tracing** - Unique ID for each request (X-Request-ID header)
- **Input validation** - Strong password requirements, email validation, amount limits
- **Role-based access** - Admin role required for merchant creation

### ✅ Observability
- **Structured logging** - JSON format in production, colored output in dev
- **Health checks** - `/health` (liveness), `/ready` (readiness with dependency checks)
- **Request logging** - Method, path, status, duration for every request

### ✅ Configuration
- **Environment-based config** - All settings via environment variables
- **No hardcoded secrets** - Secrets loaded from .env or environment
- **Configurable fraud thresholds** - All weights and limits are configurable

### ✅ Database
- **Alembic migrations** - Version-controlled schema changes
- **Connection pooling** - Built-in SQLAlchemy pool with pre-ping

## Notes For Further Production Hardening

- Add Prometheus metrics exporter (`prometheus-fastapi-instrumentator`)
- Add distributed tracing (OpenTelemetry)
- Add HTTPS with nginx/Traefik reverse proxy
- Add API key rotation endpoint
- Add circuit breakers for external services
- Add PgBouncer for connection pooling at scale
- Add Kubernetes deployment manifests
