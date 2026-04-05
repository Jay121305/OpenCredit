# 🔧 RENDER DEPLOYMENT TROUBLESHOOTING

## ❌ Error: Health Check Timeout

**Symptom**: "Timed out after waiting for internal health check to return a successful response code"

This means your app isn't starting properly. Follow these steps:

---

## 🔍 Step 1: Check Render Logs (MOST IMPORTANT!)

1. Go to your Render dashboard: https://dashboard.render.com/
2. Click on **"opencredit-api"** service
3. Click **"Logs"** tab
4. Look for error messages (usually in RED)

**Common errors you might see:**
- `connection refused` → Database URL is wrong
- `SSL required` → Missing `?sslmode=require` in DATABASE_URL
- `JWT_SECRET` → Missing JWT_SECRET environment variable
- `ImportError` → Missing package in requirements.txt

---

## ✅ Step 2: Fix Database Connection (Neon.tech)

### Get Your Neon Connection String:

1. Log in to: https://console.neon.tech/
2. Select your project
3. Click **"Dashboard"** → **"Connection Details"**
4. Copy the **connection string** - should look like:
   ```
   postgresql://username:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Set in Render:

1. Go to Render Dashboard → **opencredit-api** → **"Environment"**
2. Find `DATABASE_URL` or click **"Add Environment Variable"**
3. Set:
   ```
   Key: DATABASE_URL
   Value: postgresql://username:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   
   **⚠️ CRITICAL: Make sure it ends with `?sslmode=require`**

4. Click **"Save Changes"** (Render will auto-redeploy)

---

## ✅ Step 3: Set Required Environment Variables

Make sure these are set in Render → Environment:

### Required (MUST SET):

```bash
DATABASE_URL = postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
JWT_SECRET = <generate with command below>
```

### Generate JWT Secret:

**Windows PowerShell:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Or online:** https://generate-secret.vercel.app/32

### Optional (Already set in render.yaml):

These should already be set from render.yaml, but verify:
```bash
ENV = production
APP_NAME = OpenCredit
API_PREFIX = /api/v1
```

---

## ✅ Step 4: Verify Neon Database Settings

1. In Neon.tech console, make sure:
   - ✅ Database is **"Active"** (not suspended)
   - ✅ Connection string shows correct **region** (e.g., us-east-2)
   - ✅ **Pooled connection** is enabled (recommended)

2. Test connection from your local machine:
   ```bash
   # Install psql or use python
   python -c "from sqlalchemy import create_engine; engine = create_engine('YOUR_DATABASE_URL'); print(engine.connect())"
   ```

---

## ✅ Step 5: Remove Database Block from render.yaml

Since you're using Neon (not Render PostgreSQL), remove the database section:

**Option A: Let me update render.yaml for you**

Or

**Option B: Manual fix** - Delete lines 100-112 in `render.yaml`:
```yaml
# DELETE THIS SECTION:
databases:
  - name: opencredit-db
    plan: free
    databaseName: opencredit
    user: opencredit
```

Then commit and push.

---

## ✅ Step 6: Increase Health Check Timeout

The health check might be timing out during migrations. I've already updated this, but verify:

In **Render Dashboard** → **opencredit-api** → **Settings**:
- Health Check Path: `/health`
- Health Check Start Period: `60` seconds (or leave blank)

---

## 🔄 Step 7: Manual Redeploy

After setting environment variables:

1. Go to Render Dashboard → **opencredit-api**
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Watch the **Logs** tab for errors

---

## 📊 Step 8: Check Build Logs

In Render **Logs** tab, look for these stages:

### ✅ Good Build Output:
```
==> Building...
Successfully built xxxxx
==> Deploying...
==> Running: alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade -> abc123
==> Starting server...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### ❌ Bad Build Output (errors to look for):
```
ERROR: Could not connect to database
ERROR: relation "users" does not exist
ERROR: Missing environment variable: JWT_SECRET
ModuleNotFoundError: No module named 'xxx'
```

---

## 🔧 Quick Fixes by Error Type

### Error: "Could not connect to database"
**Fix:** Check DATABASE_URL format
```bash
# WRONG:
postgresql://user:pass@host/db

# CORRECT (for Neon):
postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require
```

### Error: "JWT_SECRET must be set"
**Fix:** Add JWT_SECRET in Environment variables
```bash
JWT_SECRET = <generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

### Error: "relation 'users' does not exist"
**Fix:** Migrations failed. Check:
1. DATABASE_URL is correct
2. Alembic can connect to database
3. Look for migration errors in logs

### Error: "Port 10000 is already in use"
**Fix:** This is normal on Render - ignore it

### Error: "Health check failed"
**Fix:** 
1. Check if `/health` endpoint works locally
2. Verify PORT environment variable is used
3. Increase health check timeout in Dockerfile

---

## 🎯 Common Neon.tech Issues

### Issue 1: SSL Mode Required
Neon REQUIRES SSL. Your DATABASE_URL MUST end with:
```
?sslmode=require
```

### Issue 2: Connection Pooling
If you see "too many connections":
1. Go to Neon dashboard
2. Enable **"Pooled Connection"**
3. Use the **pooled connection string** instead

### Issue 3: Database Suspended
Free tier Neon databases suspend after inactivity:
- Solution: Access Neon dashboard to wake it up
- Or: Upgrade to paid tier for always-on

---

## 🚀 Still Not Working?

### Try This Minimal Configuration:

1. **Temporarily use SQLite** to test if it's a DB issue:
   ```bash
   # In Render Environment:
   DATABASE_URL = sqlite:////app/data/opencredit.db
   ```

2. **If SQLite works**, problem is Neon connection
3. **If SQLite fails**, problem is app configuration

---

## 📝 Checklist Before Asking for Help

- [ ] DATABASE_URL is set with `?sslmode=require`
- [ ] JWT_SECRET is set (32+ characters)
- [ ] Checked Render **Logs** tab for actual error
- [ ] Verified Neon database is "Active" (not suspended)
- [ ] Tested DATABASE_URL connection locally
- [ ] All environment variables from render.yaml are set
- [ ] Removed the `databases:` block from render.yaml (if using Neon)

---

## 🆘 Get Your Exact Error

**Copy this and run in your Render shell:**

1. Dashboard → **opencredit-api** → **Shell** tab
2. Run:
   ```bash
   echo "DATABASE_URL: $DATABASE_URL"
   echo "JWT_SECRET: ${JWT_SECRET:0:10}..."
   python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); print(engine.connect())"
   ```

This will show:
- If DATABASE_URL is set
- If connection works
- Exact error message

---

## 📞 Next Steps

1. Check Render **Logs** tab - screenshot the error
2. Verify DATABASE_URL in Render Environment
3. Make sure it ends with `?sslmode=require`
4. Click "Manual Deploy" after setting variables

Need more help? Share:
- Screenshot of Render logs (with error in red)
- Your DATABASE_URL format (hide password)
- List of environment variables set in Render
