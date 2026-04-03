# 🚀 OpenCredit QuickStart Guide

## Prerequisites
- **Python 3.11+** (Check: `python --version`)
- **pip** (Check: `pip --version`)
- **Git** (Check: `git --version`)

## 📦 Option 1: Simple Setup (SQLite - No Docker)

### Step 1: Install Dependencies
```bash
cd "C:\Users\jayga\OneDrive\Desktop\fintech prject\opencredit"
pip install -r requirements.txt
```

### Step 2: Verify Environment Configuration
Your `.env` file is already configured for local SQLite development!

**Current configuration:**
- ✅ Database: SQLite (`opencredit.db`)
- ✅ JWT Secret: Configured
- ✅ Redis: Optional (runs without it)
- ✅ Email/SMS: Test APIs configured

### Step 3: Run Database Migration
```bash
alembic upgrade head
```

### Step 4: Start the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Server will be running at:**
- 🌐 API: http://localhost:8000
- 📖 Docs: http://localhost:8000/docs
- 🔍 ReDoc: http://localhost:8000/redoc

### Step 5: Test the API

**Health check:**
```bash
curl http://localhost:8000/health
```

**Register a user:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@test.com\",\"password\":\"StrongPass123!\",\"role\":\"admin\"}"
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@test.com\",\"password\":\"StrongPass123!\"}"
```

Save the token from the response!

---

## 🐳 Option 2: Full Setup (Docker with PostgreSQL + Redis)

### Step 1: Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop

### Step 2: Start All Services
```bash
cd "C:\Users\jayga\OneDrive\Desktop\fintech prject\opencredit"
docker-compose up -d
```

This starts:
- ✅ PostgreSQL database (port 5432)
- ✅ Redis cache (port 6379)
- ✅ FastAPI app (port 8000)
- ✅ Nginx reverse proxy (port 80)

### Step 3: Check Logs
```bash
# All services
docker-compose logs -f

# Just the app
docker-compose logs -f app
```

### Step 4: Run Migrations (in container)
```bash
docker-compose exec app alembic upgrade head
```

### Step 5: Access the API
- 🌐 API: http://localhost
- 📖 Docs: http://localhost/docs

---

## 🧪 Run Tests

### All Tests
```bash
pytest
```

### Verbose Output
```bash
pytest -v
```

### Specific Test File
```bash
pytest tests/test_records.py -v
pytest tests/test_dashboard.py -v
pytest tests/test_user_management.py -v
```

### With Coverage
```bash
pytest --cov=app --cov-report=term-missing
```

**Expected result:** 141 tests passing ✅

---

## 🎯 Quick API Examples

### 1. Create Financial Record
```bash
# First, get token from login above, then:
curl -X POST http://localhost:8000/api/v1/records ^
  -H "Authorization: Bearer YOUR_TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"amount\":150.50,\"type\":\"expense\",\"category\":\"food\",\"description\":\"Lunch\"}"
```

### 2. Get Dashboard Summary
```bash
curl http://localhost:8000/api/v1/dashboard/summary ^
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. List Users (Admin only)
```bash
curl http://localhost:8000/api/v1/users ^
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📂 Database Files

- **Development DB:** `opencredit.db` (SQLite)
- **Test DB:** `test_opencredit.db` (auto-created during tests)

To reset the database:
```bash
rm opencredit.db
alembic upgrade head
```

---

## 🔧 Common Commands

### Development Server with Hot Reload
```bash
uvicorn app.main:app --reload
```

### Create Database Backup
```bash
# SQLite backup
copy opencredit.db opencredit.backup.db

# PostgreSQL backup (Docker)
docker-compose exec postgres pg_dump -U opencredit opencredit > backup.sql
```

### View Database
```bash
# Install sqlite-web
pip install sqlite-web

# Open database browser
sqlite_web opencredit.db
```

### Check Environment Variables
```bash
python -c "from app.core.config import settings; print(settings.model_dump())"
```

---

## 🛑 Stop Services

### Local Development
Press `Ctrl+C` in the terminal running uvicorn

### Docker
```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (DELETES DATA!)
docker-compose down -v
```

---

## 📊 API Endpoints Overview

| Category | Endpoints | Auth Level |
|----------|-----------|------------|
| **Auth** | Register, Login | None |
| **Records** | CRUD operations | Analyst+ |
| **Dashboard** | Summary, Categories, Trends | Viewer+ |
| **Users** | Management, Roles | Admin |
| **Payments** | Process, Refund | User+ |
| **Health** | Health checks | None |

Full documentation: http://localhost:8000/docs

---

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Windows - Find process on port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Database Locked (SQLite)
```bash
# Close all connections and restart
rm opencredit.db
alembic upgrade head
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Redis Connection Error
If you see Redis errors but don't have Redis installed:
- It's **optional** for development
- App will run without it (some features like rate limiting will be disabled)
- To install: https://redis.io/docs/install/

---

## 🎓 Next Steps

1. **Explore the API:** Visit http://localhost:8000/docs
2. **Read the README:** See `README.md` for architecture details
3. **Check the tests:** Review `tests/` for usage examples
4. **Customize:** Edit `.env` for your configuration

**Happy coding! 🚀**
