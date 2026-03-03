# 🚀 Deployment Guide

## Option 1 — Railway (Recommended, Free Tier)

Railway supports multi-service deployments from a single repo.

### Steps

1. Create a free account at https://railway.app
2. New Project → Deploy from GitHub repo → select `pharma-kpi-platform`
3. Add two services:
   - **API service**: set start command `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Dashboard service**: set start command `streamlit run dashboard/app.py --server.port $PORT --server.address 0.0.0.0`
4. Set environment variables (copy from `.env.example`):
   - `DUCKDB_PATH=/data/kpis.db`
   - `SLACK_WEBHOOK_URL=https://hooks.slack.com/...` (optional)
   - `API_BASE_URL=https://your-api-service.railway.app`
5. Add a Volume on `/data` for DuckDB persistence
6. Deploy — Railway auto-deploys on every push to `main`

---

## Option 2 — Render

1. Create account at https://render.com
2. New Web Service → connect GitHub repo
3. Create two services (API + Dashboard) with the same commands as above
4. Free tier spins down after inactivity — use paid tier for always-on
5. Set env vars in the Render dashboard

---

## Option 3 — VPS (Ubuntu 22.04)

```bash
# 1. SSH into your server
ssh user@your-vps-ip

# 2. Install Docker
curl -fsSL https://get.docker.com | sh

# 3. Clone the repo
git clone https://github.com/BadreddineEK/pharma-kpi-platform
cd pharma-kpi-platform

# 4. Configure
cp .env.example .env
nano .env  # fill in your values

# 5. Run
docker-compose up -d

# 6. (Optional) Set up Nginx reverse proxy
# Dashboard on port 80 → proxy to localhost:8501
# API on /api/ → proxy to localhost:8000
```

### Nginx config example

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
    }
}
```

---

## CI/CD — GitHub Actions

The workflow in `.github/workflows/ci.yml` automatically:
- Runs `pytest` on every push
- Runs `ruff` linting
- Deploys to Railway on push to `main` (requires `RAILWAY_TOKEN` secret)

To set up auto-deploy:
1. Get your Railway token: Railway dashboard → Account → Tokens
2. Add it as a GitHub secret: repo Settings → Secrets → `RAILWAY_TOKEN`
