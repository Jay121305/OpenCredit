# 🏦 OpenCredit - Production-Grade Fintech Backend

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![CI](https://github.com/Jay121305/OpenCredit/actions/workflows/ci.yml/badge.svg)
![Coverage](https://codecov.io/gh/Jay121305/OpenCredit/branch/main/graph/badge.svg)

**A production-ready FastAPI fintech backend with ML fraud detection, blockchain-style ledger, and enterprise features**

[Quick Start](#-quick-start) • [Architecture](#-system-architecture) • [API Docs](#-api-documentation) • [Demo](#-demo-accounts)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features-at-a-glance)
- [Quick Start](#-quick-start)
- [System Architecture](#-system-architecture)
- [How It Works](#-how-it-works-deep-dive)
- [API Documentation](#-api-documentation)
- [Database Schema](#-database-schema)
- [Security](#-security)
- [Testing](#-testing)
- [Deployment](#-deployment)

---

## 🎯 Overview

### What is OpenCredit?

OpenCredit is a **production-grade fintech backend** that demonstrates enterprise-level engineering practices. Built to showcase:

- ✅ **Real-world architecture** (not just a tutorial project)
- ✅ **Machine Learning** integration (fraud detection)
- ✅ **Blockchain concepts** (hash-chained ledger)
- ✅ **Security best practices** (JWT, RBAC, MFA)
- ✅ **Clean code** (type hints, tests, documentation)

### One-Sentence Summary

> A FastAPI payment system with **ML fraud detection**, **hash-chained audit ledger** (like blockchain), and **role-based access control** across 50+ REST endpoints.

### Key Statistics

```
📊 50+ REST API Endpoints
🛡️ ML Fraud Detection (Isolation Forest algorithm)
⛓️ Hash-Chained Ledger (SHA-256 cryptography)
👥 4-Tier RBAC (Viewer → User → Analyst → Admin)
✅ 141 Passing Tests
🔐 MFA Support (TOTP + SMS)
📄 KYC Verification System
🔔 Webhook Event System
💱 Multi-Currency Support
```

---

## ✨ Features at a Glance

### 🛡️ ML-Powered Fraud Detection

Every payment is scored in real-time using **Isolation Forest** machine learning:

```
Transaction → Fraud Engine → Score (0.0-1.0) → Decision
              ↓
         4 Factors:
         • High-Value Check
         • Velocity Check (transaction frequency)
         • Geo-Mismatch Detection
         • ML Anomaly Model
              ↓
         Auto Decision:
         < 0.50 → ✅ APPROVE
         0.50-0.75 → ⚠️ FLAG for review
         > 0.75 → ❌ REJECT
```

### ⛓️ Hash-Chained Ledger (Blockchain-Style)

Immutable audit trail using **SHA-256** hashing (same as Bitcoin):

```
Block #1              Block #2              Block #3
┌────────────┐       ┌────────────┐       ┌────────────┐
│ TX: #5     │       │ TX: #6     │       │ TX: #7     │
│ Hash: abc──┼──────►│ Prev: abc  │       │ Prev: def  │
│ Prev: GEN  │       │ Hash: def──┼──────►│ Hash: ghi  │
└────────────┘       └────────────┘       └────────────┘
```

**Tamper-Evident**: Changing any block breaks the entire chain ⚠️

### 👥 Role-Based Access Control

```
┌───────────────────────────────────────┐
│ ADMIN → Full system access            │
│   ├─ Manage users                     │
│   ├─ Review KYC                       │
│   └─ All analyst permissions ↓        │
└───────────────────────────────────────┘
             ↓
┌───────────────────────────────────────┐
│ ANALYST → Analytics + data management │
│   ├─ Create/edit records              │
│   ├─ View analytics                   │
│   └─ All user permissions ↓           │
└───────────────────────────────────────┘
             ↓
┌───────────────────────────────────────┐
│ USER → Payment processing             │
│   ├─ Process payments                 │
│   ├─ Create merchants                 │
│   └─ All viewer permissions ↓         │
└───────────────────────────────────────┘
             ↓
┌───────────────────────────────────────┐
│ VIEWER → Read-only access             │
│   └─ View dashboard only              │
└───────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Installation (3 Commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
alembic upgrade head

# 3. Start server
uvicorn app.main:app --reload

# ✅ Running at http://localhost:8000
```

### Demo Accounts

```
┌──────────┬─────────────────────────────┬─────────────────┐
│ Role     │ Email                        │ Password        │
├──────────┼─────────────────────────────┼─────────────────┤
│ Admin    │ admin@demo.opencredit.com   │ AdminPass123!   │
│ Analyst  │ analyst@demo.opencredit.com │ AnalystPass123! │
│ User     │ user@demo.opencredit.com    │ UserPass123!    │
│ Viewer   │ viewer@demo.opencredit.com  │ ViewerPass123!  │
└──────────┴─────────────────────────────┴─────────────────┘
```

### Quick Test Flow

```
1. Open http://localhost:8000
2. Login as admin
3. Go to "Merchants" → Create merchant
4. Go to "Payments" → Process $100 payment
5. Go to "Fraud Detection" → See ML scoring
6. Go to "Ledger" → See hash-chained block
7. Click "Verify Chain" → ✅ Integrity verified
```

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                         │
│  Browser Dashboard │ Mobile App (future) │ API Keys     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               API GATEWAY (FastAPI)                      │
│  • CORS • Rate Limiting • Auth • Metrics                │
└──────────────────────────┬──────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │  AUTH   │      │ ROUTES  │      │ STATIC  │
    │ • JWT   │      │ 50+ APIs│      │  FILES  │
    │ • Keys  │      │         │      │         │
    └────┬────┘      └────┬────┘      └─────────┘
         │                │
         └────────┬───────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│              BUSINESS LOGIC LAYER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Payment  │  │  Fraud   │  │  Ledger  │              │
│  │ Service  │  │  Engine  │  │ Service  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│             DATA LAYER (SQLAlchemy ORM)                  │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│           DATABASE (PostgreSQL / SQLite)                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 How It Works: Deep Dive

### Payment Processing Flow

```
┌─────────────────────────────────────────────────────────┐
│  Payment Request Flow (Step-by-Step)                    │
└─────────────────────────────────────────────────────────┘

1. User submits payment from browser
       ↓
2. FastAPI receives POST /api/v1/payments
       ↓
3. Middleware validates:
   • Rate limit check (100/min)
   • JWT token validation
   • API key verification (merchant)
       ↓
4. Pydantic validates request schema
       ↓
5. Check idempotency (duplicate prevention)
   ├─ Duplicate → Return existing transaction
   └─ New → Continue ↓
       
6. Fraud Engine evaluates transaction:
   ┌──────────────────────────────────┐
   │ a) High-Value Check              │
   │    Amount > $5,000? → +0.45 pts  │
   │                                   │
   │ b) Velocity Check                │
   │    >5 txns in 60 sec? → +0.25 pts│
   │                                   │
   │ c) Geo-Mismatch                  │
   │    Location changed? → +0.10 pts │
   │                                   │
   │ d) ML Model (Isolation Forest)   │
   │    Anomaly detected → up to +0.30│
   │                                   │
   │ TOTAL SCORE → Decision:          │
   │ < 0.50 → APPROVE ✅              │
   │ 0.50-0.75 → FLAG ⚠️              │
   │ > 0.75 → REJECT ❌               │
   └──────────────────────────────────┘
       ↓
7. Credit Limit Check
   ├─ Insufficient → Reject transaction
   └─ OK → Continue ↓
       
8. Database Transaction (ACID):
   ├─ Update: available_credit -= amount
   ├─ Create: transaction record
   └─ Create: ledger block (hash-chained)
       ↓
9. Publish webhook event (async)
       ↓
10. Commit to database
       ↓
11. Return JSON response
       ↓
12. Browser updates dashboard
```

### Fraud Detection Algorithm

**Code Implementation** (`app/services/fraud.py`):

```python
def evaluate(self, db, user_id, amount, geo):
    score = 0.0
    
    # Factor 1: High-value check
    if amount >= 5000:
        score += 0.45
    
    # Factor 2: Velocity check
    recent_count = count_transactions_last_60_seconds(user_id)
    if recent_count >= 5:
        score += 0.25
    
    # Factor 3: Geo-mismatch
    last_geo = get_last_transaction_location(user_id)
    if last_geo and last_geo != geo:
        score += 0.10
    
    # Factor 4: ML model (Isolation Forest)
    features = [[amount, recent_count]]
    ml_score = isolation_forest.decision_function(features)
    score += max(0, min(0.30, -ml_score))
    
    # Decision
    if score >= 0.75:
        return "rejected"
    elif score >= 0.50:
        return "flagged"
    else:
        return "approved"
```

**Visual Breakdown**:

```
Example Transaction: $6,000 from US

┌─────────────────────────────┐
│ HIGH-VALUE CHECK            │
│ $6,000 > $5,000? YES        │
│ Score: +0.45                │
└──────────┬──────────────────┘
           │ Running Total: 0.45
           ▼
┌─────────────────────────────┐
│ VELOCITY CHECK              │
│ Transactions last 60s: 2    │
│ 2 < 5? OK                   │
│ Score: +0.0                 │
└──────────┬──────────────────┘
           │ Running Total: 0.45
           ▼
┌─────────────────────────────┐
│ GEO-MISMATCH CHECK          │
│ Last location: US           │
│ Current: US → Same          │
│ Score: +0.0                 │
└──────────┬──────────────────┘
           │ Running Total: 0.45
           ▼
┌─────────────────────────────┐
│ ML MODEL (Isolation Forest) │
│ Features: [6000, 2]         │
│ Anomaly score: 0.15         │
│ Score: +0.15                │
└──────────┬──────────────────┘
           │ FINAL: 0.60
           ▼
┌─────────────────────────────┐
│ DECISION                    │
│ 0.60 is between 0.50-0.75   │
│ Result: FLAGGED ⚠️          │
└─────────────────────────────┘
```

### Ledger Hash-Chaining Process

**Algorithm** (`app/services/ledger.py`):

```python
def append_block(db, tx_id, payload):
    # Step 1: Get previous block's hash
    prev_block = get_latest_block(db)
    prev_hash = prev_block.block_hash if prev_block else "GENESIS"
    
    # Step 2: Prepare data
    timestamp = datetime.utcnow()
    payload_json = json.dumps(payload, sort_keys=True)
    
    # Step 3: Create raw string
    raw_string = f"{tx_id}|{timestamp}|{prev_hash}|{payload_json}"
    
    # Step 4: Hash with SHA-256
    block_hash = hashlib.sha256(raw_string.encode()).hexdigest()
    
    # Step 5: Save to database
    new_block = LedgerBlock(
        transaction_id=tx_id,
        previous_hash=prev_hash,  # Links to prev block
        block_hash=block_hash,     # Current block hash
        payload=payload_json,
        created_at=timestamp
    )
    db.add(new_block)
    return new_block
```

**Visual Example**:

```
Creating Block #7 for Transaction $1,500

┌──────────────────────────────────────────┐
│ STEP 1: Fetch Previous Block            │
├──────────────────────────────────────────┤
│ Block #6 hash:                           │
│ 2fa955e1d12e9c0f94768cb921d50c49...     │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ STEP 2: Prepare Raw String               │
├──────────────────────────────────────────┤
│ 7|2026-04-05T10:30:00|2fa955e1...|      │
│ {"amount":1500,"status":"approved"}      │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ STEP 3: Apply SHA-256 Hash               │
├──────────────────────────────────────────┤
│ Input: "7|2026-04-05..."                 │
│ Output: 943ff19fa73834af2db56679...      │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ STEP 4: Create New Block                 │
├──────────────────────────────────────────┤
│ Block #7                                  │
│ ├─ transaction_id: 7                     │
│ ├─ previous_hash: 2fa955e1...            │
│ ├─ block_hash: 943ff19f...               │
│ └─ payload: {...}                        │
└──────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────┐
│ STEP 5: Save to Database                 │
├──────────────────────────────────────────┤
│ ✅ Block #7 added to chain               │
│ ⛓️ Links to Block #6                     │
│ 🔒 Immutable (tampering = broken chain) │
└──────────────────────────────────────────┘
```

**Chain Verification**:

```
Verify Integrity Algorithm:

FOR each block in database:
  ┌─────────────────────────────────┐
  │ 1. Check hash linkage           │
  │    block.previous_hash ==       │
  │    previous_block.block_hash?   │
  │    ├─ NO → Chain broken! ❌     │
  │    └─ YES → Continue ✓          │
  └─────────────────────────────────┘
           ↓
  ┌─────────────────────────────────┐
  │ 2. Recompute hash               │
  │    raw = reconstruct_string()   │
  │    computed = SHA256(raw)       │
  │    computed == block.block_hash?│
  │    ├─ NO → Data tampered! ❌    │
  │    └─ YES → Valid ✓             │
  └─────────────────────────────────┘

IF all blocks pass → Chain VALID ✅
ELSE → Chain CORRUPTED ❌ (report first invalid block)
```

---

## 📡 API Documentation

### Core Endpoints

**Authentication**
```http
POST /api/v1/auth/register  # Create account
POST /api/v1/auth/login     # Get JWT token
GET  /api/v1/auth/me        # Get profile + role
```

**Payments**
```http
POST /api/v1/payments       # Process payment
GET  /api/v1/payments       # List transactions
```

**Ledger**
```http
GET /api/v1/ledger          # List blocks
GET /api/v1/ledger/stats    # Chain statistics
GET /api/v1/ledger/verify   # Verify integrity
```

**Admin** (admin-only)
```http
GET   /api/v1/users         # List users
PATCH /api/v1/users/{id}/role    # Change role
POST  /api/v1/users/{id}/activate # Activate user
```

### Complete API List (50+)

<details>
<summary>📚 Click to view all endpoints</summary>

**Auth** (3)
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

**Payments** (2)
- `POST /payments`
- `GET /payments`

**Merchants** (5)
- `POST /merchants` - Create
- `GET /merchants` - List
- `GET /merchants/{id}` - Get one
- `POST /merchants/{id}/rotate-key` - Rotate API key
- `POST /merchants/{id}/deactivate` - Deactivate

**Ledger** (4)
- `GET /ledger` - List blocks
- `GET /ledger/stats` - Statistics
- `GET /ledger/verify` - Verify chain
- `GET /ledger/{id}` - Get block

**Users** (6) - Admin only
- `GET /users` - List
- `GET /users/stats` - Statistics
- `GET /users/{id}` - Get user
- `PATCH /users/{id}/role` - Change role
- `POST /users/{id}/activate`
- `POST /users/{id}/deactivate`

**MFA** (7)
- `GET /mfa/status`
- `POST /mfa/totp/setup`
- `POST /mfa/totp/verify`
- `POST /mfa/sms/setup`
- `POST /mfa/sms/verify`
- `POST /mfa/backup-codes/regenerate`
- `POST /mfa/disable`

**KYC** (6)
- `GET /kyc/status`
- `POST /kyc/submit`
- `POST /kyc/documents`
- `GET /kyc/documents`
- `GET /kyc/admin/pending` - Admin
- `POST /kyc/admin/{id}/review` - Admin

**Webhooks** (7)
- `GET /webhooks/events` - List event types
- `POST /webhooks` - Create endpoint
- `GET /webhooks` - List endpoints
- `GET /webhooks/{id}` - Get endpoint
- `POST /webhooks/{id}/rotate-secret`
- `GET /webhooks/{id}/deliveries`
- `POST /webhooks/{id}/test`

**Analytics** (4)
- `GET /analytics/spending-summary`
- `GET /dashboard/summary`
- `GET /dashboard/categories`
- `GET /dashboard/trends`

**Refunds** (5)
- `POST /refunds` - Request
- `GET /refunds` - List
- `GET /refunds/{id}` - Get one
- `GET /refunds/admin/pending` - Admin
- `POST /refunds/admin/{id}/process` - Admin

**Disputes** (7)
- `POST /disputes` - Create
- `GET /disputes` - List mine
- `GET /disputes/{id}` - Get details
- `POST /disputes/{id}/evidence` - Upload
- `POST /disputes/{id}/comments` - Add comment
- `POST /disputes/{id}/withdraw` - Withdraw
- `GET /disputes/admin/all` - Admin

**Currency** (6)
- `GET /fx/currencies`
- `GET /fx/currencies/{code}`
- `GET /fx/rates`
- `GET /fx/rate`
- `POST /fx/convert`
- `GET /fx/convert`

</details>

### Example API Calls

**Login and Get Profile**
```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.opencredit.com","password":"AdminPass123!"}'

# Response:
{"access_token":"eyJhbGc..."}

# 2. Get profile
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
  "id": 1,
  "email": "admin@demo.opencredit.com",
  "role": "admin",
  "is_admin": true,
  "credit_limit": 15000.0
}
```

**Process Payment**
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-API-Key: oc_live_merchant_key" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 150.00,
    "currency": "USD",
    "category": "food",
    "geo": "US",
    "idempotency_key": "unique-123"
  }'

# Response:
{
  "transaction_id": 42,
  "amount": 150.00,
  "status": "approved",
  "fraud_score": 0.12,
  "available_credit": 14850.00
}
```

---

## 🗄️ Database Schema

### Entity Relationship Diagram

```
┌────────────────┐           ┌───────────────────┐
│     Users      │           │  Credit Accounts  │
├────────────────┤           ├───────────────────┤
│ id (PK)        │◄─────────┤│ user_id (FK)      │
│ email          │   1:1     │ credit_limit      │
│ password_hash  │           │ available_credit  │
│ role           │           └───────────────────┘
│ is_active      │
└────────┬───────┘
         │ 1:N
         ▼
┌────────────────┐           ┌───────────────────┐
│  Transactions  │           │  Ledger Blocks    │
├────────────────┤           ├───────────────────┤
│ id (PK)        │◄─────────┤│ transaction_id(FK)│
│ user_id (FK)   │   1:1     │ block_hash        │
│ merchant_id(FK)│           │ previous_hash     │
│ amount         │           │ payload (JSON)    │
│ status         │           └───────────────────┘
│ fraud_score    │
└────────┬───────┘
         │ N:1
         ▼
┌────────────────┐
│   Merchants    │
├────────────────┤
│ id (PK)        │
│ user_id (FK)   │
│ name           │
│ api_key_hash   │
└────────────────┘
```

### Key Tables

**users**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    password_hash VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP
);
```

**transactions**
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    merchant_id INTEGER,
    amount DECIMAL(10,2),
    currency VARCHAR(3),
    status VARCHAR(20),
    fraud_score DECIMAL(5,4),
    category VARCHAR(50),
    geo VARCHAR(3),
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);
```

**ledger_blocks**
```sql
CREATE TABLE ledger_blocks (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER UNIQUE,
    block_hash VARCHAR(64) UNIQUE,
    previous_hash VARCHAR(64),
    payload TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- Index for chain traversal
CREATE INDEX idx_prev_hash ON ledger_blocks(previous_hash);
```

---

## 🔐 Security

### Authentication

**JWT Tokens**
```python
# Payload:
{
  "sub": "user@example.com",
  "exp": 1680000000,  # Expiration
  "iat": 1679990000   # Issued at
}
# Algorithm: HS256
# Secret: From environment variable
```

**API Keys** (for merchants)
```
Format: oc_live_{32_random_chars}
Storage: SHA-256 hashed in database
Rotation: Supported with 7-day grace period
```

**Passwords**
- Hashed with bcrypt (cost=12)
- Minimum 8 characters
- Never stored in plain text

### Rate Limiting

```
┌─────────────────────────────┐
│ Endpoint     Limit           │
├─────────────────────────────┤
│ /auth/*      5/minute        │
│ /payments    100/minute      │
│ Default      60/minute       │
└─────────────────────────────┘
```

### Input Validation

All requests validated with Pydantic:
```python
class PaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=10000)
    currency: str = Field(regex="^[A-Z]{3}$")
```

---

## 🧪 Testing

### Test Suite

```
┌────────────────────────────┐
│ Tests:     141             │
│ Passing:   141 ✅          │
│ Coverage:  ~85%            │
│ Duration:  ~12 seconds     │
└────────────────────────────┘
```

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_fraud.py -v

# Parallel
pytest -n auto
```

---

## 🚢 Deployment

### Quick Deploy

**Local**
```bash
uvicorn app.main:app --reload
```

**Docker**
```bash
docker build -t opencredit .
docker run -p 8000:8000 opencredit
```

**Heroku**
```bash
heroku create opencredit-app
git push heroku main
heroku run alembic upgrade head
```

### Environment Variables

```bash
JWT_SECRET=your-secret-key-here
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379/0
```

---

## 📁 Project Structure

```
opencredit/
├── app/
│   ├── api/routes/      # 50+ API endpoints
│   ├── core/            # Config, security
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic validation
│   ├── services/        # Business logic
│   └── static/          # Dashboard UI
├── tests/               # 141 tests
├── alembic/             # Migrations
└── requirements.txt     # Dependencies
```

---

## 🎓 What You'll Learn

- ✅ FastAPI best practices
- ✅ Machine learning integration
- ✅ Blockchain/hash-chain concepts
- ✅ Security (JWT, RBAC, MFA)
- ✅ Database design
- ✅ Testing strategies
- ✅ API documentation

---

## 📞 Support

- **Live Demo**: https://opencredit-api-ivon.onrender.com
- **HELP Docs**: https://opencredit-api-ivon.onrender.com/static/testing_guide.html
- **Issues**: GitHub Issues

---

<div align="center">

**⭐ Star this repo if you find it helpful! ⭐**

Made with ❤️ for learning and portfolio demonstration

[Documentation](http://localhost:8000/docs) • [Report Bug](https://github.com/issues) • [Request Feature](https://github.com/issues)

</div>
