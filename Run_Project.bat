@echo off
title Viora – AI Voice Receptionist
color 0B
setlocal enabledelayedexpansion

:: ── Ensure script runs from its own directory ──────────────────────────────
cd /d "%~dp0"

echo.
echo  ======================================================
echo         Viora - Healthcare Voice Receptionist
echo  ======================================================
echo.

:: ── Check Prerequisites ──────────────────────────────────────────────────
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11+ and try again.
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js 18+ and try again.
    pause
    exit /b 1
)

:: ── Environment & Virtualenv ──────────────────────────────────────────────
if not exist .env (
    echo [INFO] No .env file found. Creating .env from .env.example...
    copy .env.example .env >nul
    echo [INFO] Created .env file.
)

:: ── Clean up stale ports (8000 for backend, 5173 for Vite) ─────────────────
echo [1/3] Checking and freeing ports...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)

:: ── 1. Start FastAPI Backend ───────────────────────────────────────────────
echo [2/3] Starting Viora FastAPI Backend (Port 8000)...
start "Viora API Backend" cmd /k "cd /d ""%~dp0"" && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && python run_backend.py"

:: ── 2. Start LiveKit Voice Agent Worker ───────────────────────────────────
echo [2/3] Starting Viora LiveKit Voice Agent Worker...
start "Viora Agent Worker" cmd /k "cd /d ""%~dp0"" && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) && python -m agent.worker dev"

:: ── 3. Start React Dashboard ──────────────────────────────────────────────
echo [3/3] Starting Viora React Dashboard (Port 5173)...
start "Viora Dashboard" cmd /k "cd /d ""%~dp0\dashboard"" && npm run dev"

echo.
echo  ======================================================
echo   Viora services are launching in separate windows:
echo.
echo   - Admin Dashboard:  http://localhost:5173
echo   - Voice Simulator:  http://localhost:5173/simulator
echo   - API Backend:      http://localhost:8000/docs
echo   - API Health:       http://localhost:8000/health
echo.
echo   Press any key to open the Voice Simulator in browser...
echo   (or close this window to keep services running)
echo  ======================================================
echo.
pause >nul
start "" http://localhost:5173/simulator
