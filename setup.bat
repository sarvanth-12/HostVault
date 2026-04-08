@echo off
title PrivCloud Setup
cd /d "%~dp0"

echo.
echo  ==========================================
echo    PrivCloud — First Time Setup
echo  ==========================================
echo.

:: Step 1 - Install dependencies
echo [1/3] Installing Python packages...
pip install -r requirements.txt
if errorlevel 1 ( echo ERROR: pip install failed & pause & exit /b 1 )

:: Step 2 - Check .env
if not exist ".env" (
  echo.
  echo [!] .env file not found!
  echo     Please:
  echo     1. Copy .env.example to .env
  echo     2. Fill in your PostgreSQL password and MinIO credentials
  echo     3. Run this script again
  echo.
  pause
  exit /b 1
)

:: Step 3 - Init database
echo [2/3] Creating database tables...
python scripts\init_db.py
if errorlevel 1 ( echo ERROR: Database init failed & pause & exit /b 1 )

echo.
echo [3/3] Starting server...
echo.
echo  Open your browser at: http://localhost:5000
echo  Press Ctrl+C to stop.
echo.
python run.py
pause
