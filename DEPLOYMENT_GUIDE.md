# 🚀 OpenCredit Deployment Guide - Render.com

## ✨ One-Click Deployment to Render (FREE)

### 📋 Prerequisites

1. **GitHub Account** (to host your code)
2. **Render Account** (free at [render.com](https://render.com))
3. Your OpenCredit project pushed to GitHub

---

## 🎯 Quick Deployment Steps

### Step 1: Push Code to GitHub

```bash
# Initialize git (if not already done)
cd "c:\Users\jayga\OneDrive\Desktop\fintech prject\opencredit"
git init
git add .
git commit -m "Initial commit - Ready for deployment"

# Create repository on GitHub (https://github.com/new)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/opencredit.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Render

#### Option A: Automatic Blueprint Deployment (Easiest) ✅

1. **Go to Render Dashboard**: https://dashboard.render.com/
2. **Click "New" → "Blueprint"**
3. **Connect your GitHub repository** (opencredit)
4. Render will detect `render.yaml` and show all services
5. **Click "Apply"** - Done! 🎉

#### Option B: Manual Deployment

1. **Create Web Service**:
   - Dashboard → "New" → "Web Service"
   - Connect GitHub repo
   - **Settings**:
     - Name: `opencredit-api`
     - Runtime: `Docker`
     - Instance Type: `Free`
     - Build Command: (leave empty - uses Dockerfile)
     - Start Command: (leave empty - uses Dockerfile CMD)

2. **Create PostgreSQL Database** (Optional - see Alternative below):
   - Dashboard → "New" → "PostgreSQL"
   - Name: `opencredit-db`
   - Plan: `Free` (expires in 90 days)
   - Click "Create Database"

3. **Set Environment Variables**:
   - Go to your web service → "Environment"
   - Add these secrets:

   ```bash
   # Generate JWT secret (run on your machine):
   openssl rand -hex 32
   ```

   Then add in Render:
   ```
   JWT_SECRET=<paste generated secret>
   DATABASE_URL=<copy from PostgreSQL instance>
   ENV=production
   ```

### Step 3: Access Your API 🌐

After deployment (takes 5-10 minutes):

- **API URL**: `https://opencredit-api.onrender.com`
- **Health Check**: `https://opencredit-api.onrender.com/health`
- **API Docs**: `https://opencredit-api.onrender.com/docs`
- **Dashboard**: `https://opencredit-api.onrender.com/` (static frontend)

---

## 🔧 Configuration

### Environment Variables to Set in Render

| Variable | Value | Required |
|----------|-------|----------|
| `JWT_SECRET` | Generate with `openssl rand -hex 32` | ✅ Yes |
| `DATABASE_URL` | Auto-set by Render PostgreSQL | ✅ Yes |
| `ENV` | `production` | ✅ Yes |
| `CORS_ORIGINS` | `https://opencredit-api.onrender.com` | ✅ Yes |
| `REDIS_URL` | Leave empty for now (optional) | ❌ No |

### Update CORS After Deployment

After your site is live, update CORS:
1. Get your Render URL: `https://YOUR_APP_NAME.onrender.com`
2. Update `CORS_ORIGINS` environment variable in Render dashboard
3. Redeploy

---

## 💾 Database Options

### Option 1: Render PostgreSQL (Free, 90 days) ⚠️

**Pros**: Easy integration, managed
**Cons**: Expires after 90 days

Set in Render:
```
DATABASE_URL=postgresql://user:pass@host/opencredit
```

### Option 2: Neon.tech PostgreSQL (Free, Permanent) ✅ RECOMMENDED

**Pros**: Free forever (500MB storage), doesn't expire
**Cons**: Need external signup

1. Sign up at [neon.tech](https://neon.tech) (free)
2. Create new project
3. Copy connection string
4. Set in Render environment:
   ```
   DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/opencredit?sslmode=require
   ```

### Option 3: SQLite (Simplest for testing) 🧪

For demo/testing only (data lost on redeploy):

1. Update `DATABASE_URL` in Render:
   ```
   DATABASE_URL=sqlite:///./opencredit.db
   ```

2. Modify Dockerfile.render (line 45):
   ```dockerfile
   # Create data directory for SQLite
   RUN mkdir -p /app/data && chmod 755 /app/data
   ```

3. Update alembic.ini to use: `sqlite:///./data/opencredit.db`

---

## 🔴 Redis Configuration (Optional)

Render doesn't offer free Redis. Options:

### Option A: Upstash Redis (Free Tier) ✅

1. Sign up at [upstash.com](https://upstash.com) (free)
2. Create Redis database (serverless)
3. Copy `REDIS_URL` (rediss://...)
4. Set in Render environment variables

### Option B: Skip Redis (Disable Features)

Update your code to make Redis optional:
- Comment out analytics worker in `docker-compose.yml`
- Disable Redis-dependent features temporarily

---

## 🎉 Post-Deployment

### 1. Create Admin User

After deployment, create your first user:

**Option A: Use API Docs**
1. Go to: `https://YOUR_APP.onrender.com/docs`
2. Find `POST /api/v1/auth/register`
3. Register with:
   ```json
   {
     "email": "admin@example.com",
     "password": "SecurePass123!",
     "full_name": "Admin User"
   }
   ```

**Option B: Use Render Shell**
1. Dashboard → Your Service → "Shell"
2. Run:
   ```bash
   python create_demo_accounts.py
   ```

### 2. Test Your API

```bash
# Health check
curl https://YOUR_APP.onrender.com/health

# Login
curl -X POST https://YOUR_APP.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"SecurePass123!"}'

# Get dashboard (use token from login)
curl https://YOUR_APP.onrender.com/api/v1/dashboard/summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## ⚡ Render Free Tier Limitations

| Feature | Free Tier |
|---------|-----------|
| **Services** | Unlimited |
| **Compute** | 750 hours/month per service |
| **Sleep** | After 15 min inactivity (30s wake-up) |
| **PostgreSQL** | 1GB storage, expires in 90 days |
| **Build Time** | ~5-10 minutes |
| **Bandwidth** | 100GB/month |

**Tip**: Free services sleep after 15 minutes. First request after sleep takes ~30 seconds.

---

## 🔄 Update/Redeploy

Render auto-deploys on every `git push`:

```bash
# Make changes
git add .
git commit -m "Update feature X"
git push origin main

# Render automatically rebuilds and deploys!
```

---

## 🐛 Troubleshooting

### Build Fails

**Check Render Logs**:
- Dashboard → Your Service → "Logs"
- Look for Python/Docker errors

**Common fixes**:
- Ensure `requirements.txt` is up to date
- Check `Dockerfile.render` syntax
- Verify all dependencies install correctly

### Database Connection Issues

```bash
# Test DATABASE_URL format in Render shell:
echo $DATABASE_URL

# Should be:
postgresql://user:password@host:5432/dbname
```

### 404 on API Endpoints

- Verify `API_PREFIX=/api/v1` is set
- Check CORS settings match your domain
- Confirm routes in `/docs` page

### App Won't Start

Check startup command in logs:
```bash
# Should run:
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 🎓 Next Steps

1. ✅ **Custom Domain** (optional): Add your own domain in Render settings
2. ✅ **Monitoring**: Use Render's built-in metrics
3. ✅ **CI/CD**: Automatic deploys on git push (already working!)
4. ✅ **Upgrade**: Scale to paid tier ($7/mo) for 24/7 uptime
5. ✅ **Backups**: Enable in PostgreSQL settings

---

## 📚 Resources

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com/
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Neon DB**: https://neon.tech/docs
- **Upstash Redis**: https://upstash.com/docs/redis

---

## 🚨 Security Checklist

Before going live:

- [ ] Change all default passwords
- [ ] Set strong `JWT_SECRET` (32+ chars)
- [ ] Enable HTTPS (automatic on Render)
- [ ] Set correct `CORS_ORIGINS`
- [ ] Review rate limiting settings
- [ ] Set `ENV=production`
- [ ] Never commit `.env` to Git
- [ ] Enable Render's DDoS protection

---

**Need Help?** 
- Render Community: https://community.render.com/
- OpenCredit Issues: GitHub repository issues tab
