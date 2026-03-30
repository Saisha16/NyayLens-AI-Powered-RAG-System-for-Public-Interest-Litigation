# 🚀 NyayLens Deployment Guide

This guide covers deploying NyayLens on various free hosting platforms.

---

## 📋 Prerequisites

- GitHub account with your repository
- Account on chosen platform (Render/Railway/Fly.io)
- Basic understanding of environment variables

---

## 🎯 Option 1: Render (Recommended for Beginners)

### Backend Deployment

1. **Sign up at [render.com](https://render.com)**

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select branch: `main`

3. **Configure Build Settings**
   ```
   Name: nyaylens-backend
   Region: Oregon (US West)
   Branch: main
   Root Directory: (leave empty)
   Runtime: Python 3
   Build Command: pip install -r requirements.txt && python -m spacy download en_core_web_sm
   Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Set Environment Variables**
   - Go to "Environment" tab
   - Add variables from `.env.example`
   - Generate secure values for `SECRET_KEY` and `JWT_SECRET`

5. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment

### Frontend Deployment

**Option A: Use Render Static Site**
1. Create "Static Site"
2. Point to `frontend` directory
3. No build command needed

**Option B: Use GitHub Pages**
1. Go to repository Settings → Pages
2. Source: Deploy from branch `main`
3. Folder: `/frontend`
4. Update `API_URL` in `frontend/script.js` to your backend URL

### Important Notes
- ⚠️ Free tier spins down after 15 min inactivity
- First request after sleep: 30-60 seconds
- 750 hours/month free

---

## 🚂 Option 2: Railway

1. **Sign up at [railway.app](https://railway.app)**

2. **Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure**
   - Railway auto-detects Python
   - Add environment variables in "Variables" tab
   - Deploy automatically starts

4. **Get URL**
   - Find your app URL in deployment dashboard
   - Update frontend `API_URL`

### Advantages
- No cold starts (stays warm)
- $5 free credit/month
- Easy one-click deployment

---

## ✈️ Option 3: Fly.io (For Advanced Users)

1. **Install Fly CLI**
   ```bash
   # Windows
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   
   # Mac/Linux
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and Initialize**
   ```bash
   fly auth login
   cd your-project-directory
   fly launch
   ```

3. **Configure fly.toml**
   - File is already created in repository
   - Update `app` name if needed

4. **Deploy**
   ```bash
   fly deploy
   ```

5. **Set Secrets**
   ```bash
   fly secrets set SECRET_KEY=your-secret-key
   fly secrets set JWT_SECRET=your-jwt-secret
   ```

### Advantages
- Always-on (no cold starts)
- 3 shared VMs free
- Better performance

---

## 🔧 Post-Deployment Configuration

### Update Frontend API URL

Edit `frontend/script.js`:
```javascript
const DEFAULT_API_URL = "https://your-backend-url.com";
```

### Enable CORS

Update `.env` or environment variables:
```
ALLOWED_ORIGINS=https://your-frontend-url.com,https://your-backend-url.com
```

### Test Deployment

1. Visit backend URL + `/health` → Should return `{"status": "healthy"}`
2. Visit backend URL + `/docs` → Should show Swagger API docs
3. Test frontend → Should load and fetch news

---

## 📊 Monitoring & Maintenance

### Check Logs
- **Render**: Dashboard → Logs tab
- **Railway**: Project → Logs
- **Fly.io**: `fly logs`

### Scheduled News Fetch

The app has built-in scheduler (runs at 08:00 daily). For platforms without persistent workers:

**Option A: External Cron Service**
1. Sign up at [cron-job.org](https://cron-job.org)
2. Create job: `GET https://your-backend/refresh-news?days_back=1`
3. Schedule: Daily at 08:00

**Option B: GitHub Actions**
Create `.github/workflows/fetch-news.yml`:
```yaml
name: Fetch Daily News
on:
  schedule:
    - cron: '0 8 * * *'  # 08:00 UTC daily
jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger news fetch
        run: |
          curl -X POST https://your-backend/refresh-news?days_back=1
```

---

## ⚠️ Common Issues

### Issue: Out of Memory
**Solution**: Reduce model size or upgrade to paid tier
```python
# Use lightweight spaCy model
python -m spacy download en_core_web_sm
```

### Issue: Slow Cold Starts
**Solution**: Use Railway (no cold starts) or Fly.io (always-on)

### Issue: CORS Errors
**Solution**: Update `ALLOWED_ORIGINS` environment variable

### Issue: Import Errors
**Solution**: Ensure all dependencies in `requirements.txt`

---

## 💰 Cost Comparison

| Platform | Free Tier | Cold Starts | Best For |
|----------|-----------|-------------|----------|
| **Render** | 750 hrs/month | Yes (15 min) | Beginners |
| **Railway** | $5 credit/month | No | Best balance |
| **Fly.io** | 3 shared VMs | No | Performance |
| **Vercel** (Frontend) | Unlimited | N/A | Static sites |

---

## 🎓 Recommended Setup

**For Best Free Experience:**
1. **Backend**: Railway (no cold starts)
2. **Frontend**: Vercel or GitHub Pages
3. **Cron Jobs**: cron-job.org (for news fetch)

**Total Cost**: $0/month 🎉

---

## 📚 Additional Resources

- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
- [Fly.io Docs](https://fly.io/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

---

## 🆘 Need Help?

If deployment fails:
1. Check platform logs
2. Verify environment variables
3. Test locally first with Docker: `docker build -t nyaylens . && docker run -p 8001:8001 nyaylens`
4. Open an issue on GitHub

---

**Happy Deploying! 🚀**
