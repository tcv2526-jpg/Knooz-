# Knooz ERP

Full ERP system — CRM, Accounting, HR & Payroll, Inventory.

**Tech stack:** Python (FastAPI) + Single-page HTML frontend + PostgreSQL + Redis

---

## 🚀 Deploy to Railway (Free — 15 minutes)

### Step 1 — Push to GitHub

1. Go to **https://github.com/new** and create a new repository named `knooz`
2. Make it **Public** (required for free Railway)
3. Run these commands in your project folder:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/knooz.git
git push -u origin main
```

### Step 2 — Create Railway account

1. Go to **https://railway.app**
2. Click **"Start a New Project"**
3. Sign up with GitHub (free, no credit card needed for $5 credit)

### Step 3 — Deploy Backend

1. In Railway dashboard → **"New Project"** → **"Deploy from GitHub repo"**
2. Select your `knooz` repository
3. Railway will detect the Dockerfile automatically
4. Set the **Root Directory** to: `backend`
5. Click **Deploy**

### Step 4 — Add PostgreSQL

1. In your Railway project → click **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Once created, click the PostgreSQL service → **"Variables"** tab
3. Copy the `DATABASE_URL` value

### Step 5 — Add Redis

1. Click **"+ New"** → **"Database"** → **"Redis"**
2. Copy the `REDIS_URL` value

### Step 6 — Configure Backend Environment Variables

Click your backend service → **"Variables"** tab → Add these:

```
DATABASE_URL        = (paste from PostgreSQL)
REDIS_URL           = (paste from Redis)
SECRET_KEY          = any-random-string-here-change-this
ENVIRONMENT         = production
CORS_ORIGINS        = ["*"]
```

### Step 7 — Get your Backend URL

1. Click your backend service → **"Settings"** → **"Domains"**
2. Click **"Generate Domain"**
3. Copy the URL (looks like: `https://knooz-backend-xxxx.up.railway.app`)

### Step 8 — Deploy Frontend

1. In Railway → **"+ New"** → **"Deploy from GitHub repo"** → select `knooz` again
2. Set **Root Directory** to: `frontend`
3. Railway uses the frontend Dockerfile (serves static files via nginx)
4. Generate a domain for frontend too

### Step 9 — Open the App

1. Open your **frontend URL** in browser
2. You'll see a setup screen — paste your **backend URL**
3. Click **"Connect & Continue"**
4. Login with: `admin@knooz.com` / `admin123`

---

## 💻 Run Locally (Docker)

```bash
docker compose up -d --build
docker compose exec backend python seed.py
```

Open: http://localhost:3000

---

## 📋 Modules

| Module | Features |
|--------|----------|
| CRM | Contacts, Leads, Deals |
| Inventory | Products, Sales Orders |
| Accounting | Invoices (with VAT), Transactions |
| HR & Payroll | Employees, Leave Requests, Payroll |

---

## 🔑 Default Login

- Email: `admin@knooz.com`
- Password: `admin123`

**Change the password after first login!**

---

## 📡 API Documentation

Available at: `https://your-backend-url.railway.app/api/docs`
