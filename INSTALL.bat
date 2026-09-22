@echo off
title Viora – Installation
color 0A
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      Viora – AI Voice Receptionist       ║
echo  ║            INSTALLATION                  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check prerequisites
echo [1/5] Checking prerequisites...
where python >nul 2>&1 || (echo  ✗ Python 3.12+ not found. Install from python.org & pause & exit /b 1)
where node   >nul 2>&1 || (echo  ✗ Node.js 20+ not found. Install from nodejs.org & pause & exit /b 1)
where docker >nul 2>&1 || (echo  ✗ Docker not found. Install Docker Desktop & pause & exit /b 1)
where git    >nul 2>&1 || (echo  ✗ Git not found. Install from git-scm.com & pause & exit /b 1)
echo  ✓ All prerequisites found

:: Copy .env
echo [2/5] Setting up environment...
if not exist .env (
    copy .env.example .env >nul
    echo  ✓ Created .env from .env.example
    echo.
    echo  ⚠  IMPORTANT: Edit .env and add your API keys before running.
    echo     Required: GEMINI_API_KEY, SARVAM_API_KEY, LIVEKIT_*, EXOTEL_*
    echo     The system runs in DEMO MODE without them.
    echo.
) else (
    echo  ✓ .env already exists – skipping
)

:: Python venv
echo [3/5] Creating Python virtual environment...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo  ✓ Python dependencies installed

:: Frontend
echo [4/5] Installing frontend dependencies...
cd dashboard
call npm ci --silent
cd ..
echo  ✓ Frontend dependencies installed

:: Docker services
echo [5/5] Starting Docker services (PostgreSQL + Redis)...
docker compose up -d postgres redis
echo  ✓ Database services started

echo.
echo  ══════════════════════════════════════════════
echo   Installation complete!
echo   Run "Run_Project.bat" to start Viora.
echo  ══════════════════════════════════════════════
echo.
pause
