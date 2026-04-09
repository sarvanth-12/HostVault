# PrivCloud — Setup Guide

## Quick Start (3 steps)

### Step 1 — Create your .env file
Copy `.env.example` → rename to `.env`
Open `.env` and fill in:

```
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/privcloud_db
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
```

Replace YOUR_POSTGRES_PASSWORD with the password you set during PostgreSQL install.

---

### Step 2 — Create the database in pgAdmin
Open pgAdmin → connect to your server → Query Tool → run each line one at a time (F5):

```sql
CREATE DATABASE privcloud_db;
```

That's it. We use the postgres superuser directly.

---

### Step 3 — Run setup
Double-click `setup.bat`

OR in VS Code terminal:
```
pip install -r requirements.txt
python scripts/init_db.py
python run.py
```

Open browser: http://localhost:5000

Default admin login:
- Email: admin@privcloud.local
- Password: Admin@1234

---

## Google OAuth Setup
1. Go to https://console.cloud.google.com
2. Create project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Add redirect URI: http://localhost:5000/api/auth/google/callback
5. Copy Client ID and Secret into .env:
   GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxx
6. Restart the server

---

## MinIO
Make sure MinIO is running on port 9000.
Default credentials in .env are minioadmin/minioadmin — update if yours are different.
The app will auto-create the bucket on first upload.
