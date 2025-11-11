# Deployment Guide - Dutch School Finder

Complete guide for deploying Dutch School Finder to production.

## Table of Contents

1. [Overview](#overview)
2. [Backend Deployment](#backend-deployment)
3. [Frontend Deployment](#frontend-deployment)
4. [Database Setup](#database-setup)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Overview

Dutch School Finder consists of two main components:

- **Backend API** (FastAPI + Python) - Serves school data
- **Frontend** (React + TypeScript) - User interface

### Deployment Options

| Component | Recommended Platforms |
|-----------|----------------------|
| Backend   | Heroku, Railway, Render, AWS Elastic Beanstalk, Google Cloud Run |
| Frontend  | Vercel, Netlify, AWS S3+CloudFront, GitHub Pages |
| Database  | PostgreSQL on Heroku, Railway, AWS RDS, or Google Cloud SQL |

---

## Backend Deployment

### Option 1: Heroku

1. **Install Heroku CLI**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
heroku login
```

2. **Create Heroku app**
```bash
cd backend
heroku create dutch-school-finder-api
```

3. **Add PostgreSQL**
```bash
heroku addons:create heroku-postgresql:mini
```

4. **Create Procfile**
```bash
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile
```

5. **Deploy**
```bash
git init
git add .
git commit -m "Deploy backend"
heroku git:remote -a dutch-school-finder-api
git push heroku main
```

6. **Set environment variables**
```bash
heroku config:set CORS_ORIGINS=https://your-frontend-domain.com
```

### Option 2: Docker + Railway/Render

1. **Create Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Deploy to Railway**
- Connect GitHub repository
- Railway auto-detects Dockerfile
- Add PostgreSQL database
- Set environment variables

3. **Deploy to Render**
- Connect GitHub repository
- Select "Docker" as environment
- Add PostgreSQL database
- Configure environment variables

### Option 3: AWS Elastic Beanstalk

1. **Install EB CLI**
```bash
pip install awsebcli
```

2. **Initialize EB**
```bash
cd backend
eb init -p python-3.11 dutch-school-finder
```

3. **Create environment**
```bash
eb create production
```

4. **Configure RDS**
- Add RDS PostgreSQL through AWS Console
- Update DATABASE_URL in environment variables

5. **Deploy**
```bash
eb deploy
```

---

## Frontend Deployment

### Option 1: Vercel (Recommended)

1. **Install Vercel CLI**
```bash
npm i -g vercel
```

2. **Configure**
```bash
cd frontend
vercel
```

3. **Set environment variables**
- Go to Vercel Dashboard → Project Settings → Environment Variables
- Add `VITE_API_URL` = your backend URL

4. **Deploy**
```bash
vercel --prod
```

### Option 2: Netlify

1. **Build the app**
```bash
cd frontend
npm run build
```

2. **Install Netlify CLI**
```bash
npm install -g netlify-cli
```

3. **Deploy**
```bash
netlify deploy --prod --dir=dist
```

4. **Configure environment**
- Netlify Dashboard → Site Settings → Environment Variables
- Add `VITE_API_URL`

### Option 3: AWS S3 + CloudFront

1. **Build the app**
```bash
cd frontend
npm run build
```

2. **Create S3 bucket**
```bash
aws s3 mb s3://dutch-school-finder
```

3. **Upload files**
```bash
aws s3 sync dist/ s3://dutch-school-finder --acl public-read
```

4. **Enable static website hosting**
```bash
aws s3 website s3://dutch-school-finder --index-document index.html --error-document index.html
```

5. **Create CloudFront distribution**
- Point to S3 bucket
- Configure custom domain (optional)
- Enable HTTPS

---

## Database Setup

### PostgreSQL on Heroku

Automatically provisioned with Heroku Postgres addon:
```bash
heroku addons:create heroku-postgresql:mini
```

Database URL is automatically set as `DATABASE_URL`.

### PostgreSQL on Railway

1. Create new PostgreSQL database in Railway dashboard
2. Copy connection string
3. Set as `DATABASE_URL` environment variable

### Self-hosted PostgreSQL

1. **Install PostgreSQL**
```bash
sudo apt-get install postgresql postgresql-contrib
```

2. **Create database**
```bash
sudo -u postgres psql
CREATE DATABASE dutch_schools;
CREATE USER schoolfinder WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE dutch_schools TO schoolfinder;
```

3. **Configure DATABASE_URL**
```
postgresql://schoolfinder:your_password@localhost/dutch_schools
```

### Database Initialization

The backend automatically creates tables on startup. To manually initialize:

```bash
python -c "from app.database import init_db; init_db()"
```

---

## Environment Configuration

### Backend Environment Variables

Create `.env` file or set in hosting platform:

```bash
# Required
DATABASE_URL=postgresql://user:pass@host/dbname
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com

# Optional
API_HOST=0.0.0.0
API_PORT=8000
DUO_API_URL=https://opendata.duo.nl/
```

### Frontend Environment Variables

Set in `.env` or hosting platform:

```bash
VITE_API_URL=https://your-backend-api.com
```

---

## SSL/HTTPS

### Backend

Most platforms (Heroku, Render, Railway) provide free SSL certificates automatically.

For custom domains:
- Heroku: `heroku certs:auto:enable`
- AWS: Use ACM (AWS Certificate Manager) with CloudFront

### Frontend

- Vercel/Netlify: Automatic HTTPS with free SSL
- CloudFront: Use ACM certificate
- Custom: Use Let's Encrypt with certbot

---

## Custom Domain Setup

### Backend API

**Heroku:**
```bash
heroku domains:add api.yourschools.com
# Configure DNS to point to Heroku DNS target
```

**Vercel/Netlify:**
- Add custom domain in dashboard
- Update DNS records as instructed

### Frontend

**Vercel:**
- Project Settings → Domains → Add yourschools.com
- Update DNS records

**CloudFront:**
- Add CNAME record pointing to CloudFront distribution
- Add alternate domain name in CloudFront settings

---

## Monitoring & Maintenance

### Application Monitoring

**Backend Logging:**
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**Error Tracking:**
- Sentry: `pip install sentry-sdk`
- Rollbar: `pip install rollbar`

**Uptime Monitoring:**
- UptimeRobot (free)
- Pingdom
- StatusCake

### Performance Monitoring

**Backend:**
- Use APM tools (New Relic, Datadog)
- Monitor API response times
- Track database query performance

**Frontend:**
- Google Analytics
- Web Vitals tracking
- Error boundary logging

### Database Maintenance

**Backups:**
```bash
# Heroku
heroku pg:backups:schedule --at '02:00 America/Los_Angeles'

# Manual backup
pg_dump -h host -U user dbname > backup.sql
```

**Restore:**
```bash
psql -h host -U user dbname < backup.sql
```

### Scaling

**Backend:**
- Heroku: Increase dyno size or add more dynos
- AWS: Auto-scaling groups
- Docker: Kubernetes or Docker Swarm

**Database:**
- Upgrade to larger instance
- Add read replicas for read-heavy workloads
- Implement caching (Redis)

---

## Continuous Deployment

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Heroku
        uses: akhileshns/heroku-deploy@v3.12.12
        with:
          heroku_api_key: ${{secrets.HEROKU_API_KEY}}
          heroku_app_name: "dutch-school-finder-api"
          heroku_email: ${{secrets.HEROKU_EMAIL}}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{secrets.VERCEL_TOKEN}}
          vercel-org-id: ${{secrets.ORG_ID}}
          vercel-project-id: ${{secrets.PROJECT_ID}}
```

---

## Checklist Before Going Live

- [ ] Backend API deployed and accessible
- [ ] Database provisioned and initialized
- [ ] Frontend deployed and pointing to correct API
- [ ] Environment variables configured
- [ ] HTTPS enabled for both frontend and backend
- [ ] Custom domains configured (if applicable)
- [ ] CORS configured correctly
- [ ] Error monitoring set up
- [ ] Backups scheduled
- [ ] Performance tested under load
- [ ] Security headers configured
- [ ] Rate limiting implemented (if needed)
- [ ] Documentation updated with production URLs

---

## Troubleshooting

### Backend not starting
- Check logs: `heroku logs --tail`
- Verify DATABASE_URL format
- Ensure all dependencies in requirements.txt

### Frontend can't reach API
- Verify CORS_ORIGINS includes frontend domain
- Check VITE_API_URL is correct
- Test API endpoint directly with curl

### Database connection failed
- Verify DATABASE_URL format
- Check database credentials
- Ensure database accepts connections from app IP

### High latency
- Enable database connection pooling
- Add CDN for frontend static assets
- Optimize API queries with indexes
- Consider caching frequently accessed data

---

## Cost Estimates

### Small Scale (MVP)

- Backend: $0-7/month (Heroku Hobby, Railway Hobby)
- Database: $0-5/month (included with backend)
- Frontend: $0 (Vercel/Netlify free tier)
- **Total: $0-12/month**

### Medium Scale (Production)

- Backend: $25-50/month (Heroku Standard, Railway Pro)
- Database: $9-50/month (dedicated PostgreSQL)
- Frontend: $0-20/month (Vercel Pro if needed)
- CDN: $0-10/month (CloudFlare free tier)
- **Total: $34-130/month**

### Large Scale (High Traffic)

- Backend: $200+/month (multiple instances, load balancer)
- Database: $100+/month (larger instance, replicas)
- Frontend: $20-100/month (Vercel Pro/Enterprise)
- CDN: $50+/month
- Monitoring: $30+/month
- **Total: $400+/month**

---

## Support & Resources

- **Documentation:** See README files in backend/ and frontend/
- **API Docs:** https://your-api.com/docs (Swagger UI)
- **Issues:** Create GitHub issue for bugs/features

---

**Last Updated:** 2025-11-11
