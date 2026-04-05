# 🚀 QUICK START - Deploy to Render.com

## ✅ Files Ready for Deployment

Your project is now configured for deployment! Here's what I've added:

1. ✅ `render.yaml` - Automatic deployment configuration
2. ✅ `Dockerfile.render` - Optimized Docker image for Render
3. ✅ `start.sh` - Startup script (migrations + server)
4. ✅ `DEPLOYMENT_GUIDE.md` - Detailed deployment instructions
5. ✅ `.env.render` - Environment variables template

All files pushed to: https://github.com/Jay121305/OpenCredit

---

## 🎯 Deploy NOW (3 Minutes!)

### Step 1: Sign Up on Render (Free)
1. Go to: https://render.com/
2. Click "Get Started" → Sign up with GitHub
3. Authorize Render to access your GitHub repositories

### Step 2: Deploy with Blueprint (One-Click)
1. Go to Render Dashboard: https://dashboard.render.com/
2. Click **"New"** → **"Blueprint"**
3. Select repository: **"Jay121305/OpenCredit"**
4. Render will detect `render.yaml` automatically
5. Click **"Apply"** 
6. Wait 5-10 minutes for deployment ☕

### Step 3: Set Required Secrets

After deployment starts, go to your service settings:

1. Find **"opencredit-api"** service
2. Click **"Environment"** tab
3. Add these variables:

```bash
# Generate JWT Secret (run this on your computer):
# Windows PowerShell:
(New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes(32) | ForEach-Object { $_.ToString("x2") } | Join-String

# Or use: python -c "import secrets; print(secrets.token_hex(32))"
```

Then add in Render:
```
JWT_SECRET = <paste the generated secret>
```

That's it! Your API will be live at: `https://opencredit-api.onrender.com`

---

## 📱 Access Your Deployed API

Once deployment completes:

- **🏠 Dashboard**: https://opencredit-api.onrender.com/
- **📚 API Docs**: https://opencredit-api.onrender.com/docs
- **💚 Health Check**: https://opencredit-api.onrender.com/health
- **📖 ReDoc**: https://opencredit-api.onrender.com/redoc

---

## 🗄️ Database Setup

Render's free PostgreSQL expires after 90 days. Better option:

### Option A: Neon.tech (FREE FOREVER ✅)

1. Sign up at: https://neon.tech (free)
2. Create a new project: "opencredit"
3. Copy the connection string (starts with `postgresql://`)
4. In Render dashboard → Environment → Add:
   ```
   DATABASE_URL = postgresql://user:pass@ep-xxx.neon.tech/opencredit?sslmode=require
   ```
5. Click "Save" → Service auto-redeploys

### Option B: Use SQLite (Simple, but data resets on redeploy)

In Render Environment variables:
```
DATABASE_URL = sqlite:///./opencredit.db
```

---

## 🎉 Create Your First User

After deployment, use the API docs:

1. Go to: `https://YOUR_APP.onrender.com/docs`
2. Find `POST /api/v1/auth/register`
3. Click "Try it out"
4. Register:
   ```json
   {
     "email": "admin@example.com",
     "password": "SecurePass123!",
     "full_name": "Admin User"
   }
   ```
5. Use the token to access protected endpoints!

---

## ⚡ Free Tier Notes

- **Sleep**: App sleeps after 15 min inactivity (wakes in ~30s on first request)
- **Hours**: 750 hours/month free
- **PostgreSQL**: Render's free DB expires in 90 days (use Neon instead)
- **Redis**: Not included in free tier (optional for this deployment)

---

## 🐛 Troubleshooting

### Build Failing?
- Check logs in Render dashboard → "Logs" tab
- Verify `requirements.txt` installs correctly
- Make sure `Dockerfile.render` is being used

### Can't Connect to Database?
1. Verify `DATABASE_URL` is set correctly
2. For Neon, ensure `?sslmode=require` is in the URL
3. Check Render logs for connection errors

### API Returns 404?
- Verify `API_PREFIX=/api/v1` is set in environment
- Check routes at `/docs` endpoint
- Ensure `ENV=production` is set

---

## 📋 Environment Variables Checklist

Required in Render dashboard:

- [x] `JWT_SECRET` - Generate with command above
- [x] `DATABASE_URL` - From Neon.tech or Render PostgreSQL
- [x] `ENV=production` - Set by render.yaml
- [x] `CORS_ORIGINS` - Update with your Render URL

Optional:
- [ ] `REDIS_URL` - For analytics (get free tier at upstash.com)

---

## 🔄 Update Your App

Every time you push to GitHub, Render auto-deploys:

```bash
# Make changes to your code
git add .
git commit -m "Add new feature"
git push origin main

# Render automatically rebuilds and deploys! 🚀
```

---

## 🎓 What's Next?

1. **Test all endpoints** using `/docs` interface
2. **Create demo accounts** using the registration API
3. **Monitor performance** in Render metrics
4. **Add custom domain** (optional) in Render settings
5. **Upgrade to paid tier** ($7/mo) for 24/7 uptime

---

## 📚 Full Documentation

See `DEPLOYMENT_GUIDE.md` for:
- Detailed setup instructions
- Redis configuration (optional)
- Custom domain setup
- Security best practices
- Monitoring and scaling tips

---

## 🆘 Need Help?

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com/
- **OpenCredit Repo**: https://github.com/Jay121305/OpenCredit

---

**You're all set! 🎊**

Deploy now at: https://dashboard.render.com/
