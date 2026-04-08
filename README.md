# ☁️ HostVault — Private Cloud Storage

HostVault is a self-hosted private cloud storage platform — think Google Drive, but running entirely on your own machine. Built with Flask, MinIO, and PostgreSQL, it gives you full control over your files with no third-party cloud involved.

Designed for small teams and personal use with a clean modern dashboard, secure file management, and a powerful admin panel.

---

## ✨ Features
- 📤 Upload, download, and manage files
- 🗑️ Trash with 30-day recovery
- 📊 Storage quota tracking per user
- 🔐 Login with email or Google OAuth
- 🛡️ Admin panel — manage users, files, storage and activity logs
- 🌙 Dark / Light theme
- 🔒 Brute force protection, rate limiting, security headers

---

## 🛠️ Tech Stack
| Layer | Tech |
|---|---|
| Backend | Python, Flask, Waitress |
| Database | PostgreSQL + SQLAlchemy |
| Storage | MinIO |
| Proxy | Nginx |
| Frontend | HTML / CSS / JS |

---

## ⚙️ Setup Guide

### Requirements
- Python 3.10+
- PostgreSQL 16+
- MinIO
- Nginx

---

### Step 1 — Clone the project
```powershell
git clone https://github.com/vijay-1806/hostvault.git
cd hostvault
```

---

### Step 2 — Create your .env file
Copy `.env.example` → rename to `.env`
Fill in your values:
```env
SECRET_KEY=privcloud-secret-key-2024
FLASK_DEBUG=0
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/privcloud_db
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-minio-password
MINIO_BUCKET=hostvault-files
MINIO_SECURE=False
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
DEFAULT_STORAGE_QUOTA=10737418240
TRASH_RETENTION_DAYS=30
FRONTEND_URL=http://localhost
HOST=0.0.0.0
PORT=8000
```

---

### Step 3 — Create the database
Open pgAdmin → Query Tool → run:
```sql
CREATE DATABASE privcloud_db;
```

---

### Step 4 — Install & initialize
```powershell
pip install -r requirements.txt
python scripts/init_db.py
```

---

### Step 5 — Install & configure Nginx
1. Download Nginx from https://nginx.org/en/download.html
2. Extract to `C:\nginx`
3. Replace `C:\nginx\conf\nginx.conf` with the `nginx.conf` file from this repo

---

### Step 6 — Install & configure MinIO
1. Download MinIO from https://min.io/download
2. Place `minio.exe` in `C:\minio\`
3. Create folder `C:\minio\data`

---

### Step 7 — Start the project (3 terminals)
```powershell
# Terminal 1 - MinIO
cd C:\minio
.\minio.exe server C:\minio\data --console-address ":9001"

# Terminal 2 - Flask
cd path\to\hostvault
python run.py

# Terminal 3 - Nginx
cd C:\nginx
.\nginx.exe
```

Open browser: **http://localhost**

---

## 🔑 Default Admin Login
| Field    | Value                  |
|----------|------------------------|
| Email    | admin@hostvault.local  |
| Password | Admin@1234             |

Admin portal: **http://localhost/admin-login.html**

---

## 🌐 Google OAuth Setup
1. Go to https://console.cloud.google.com
2. Create project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Add redirect URI: `http://localhost/api/auth/google/callback`
5. Copy Client ID and Secret into `.env`
6. Restart Flask

---

## 🗄️ MinIO Console
URL: **http://localhost:9001**
Default login: `minioadmin` / `minioadmin`
Create bucket named: `hostvault-files`

---

## 🔧 Useful Nginx Commands
```powershell
cd C:\nginx
.\nginx.exe -t        # test config
.\nginx.exe -s reload # reload
.\nginx.exe -s stop   # stop
```

---