@echo off
title Viora – Uninstall
color 0C
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      Viora – AI Voice Receptionist       ║
echo  ║           UNINSTALLATION                 ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  This will stop and remove all Viora Docker containers and volumes.
echo  Your .env file and source code will NOT be deleted.
echo.
set /p confirm=Type YES to confirm: 
if /i not "%confirm%"=="YES" (echo Cancelled. & pause & exit /b 0)

echo.
echo [1/3] Stopping and removing Docker services...
docker compose down -v
echo  ✓ Done

echo [2/3] Removing Python virtual environment...
if exist .venv (
    rmdir /s /q .venv
    echo  ✓ .venv removed
) else (
    echo  – No .venv found
)

echo [3/3] Removing frontend build...
if exist dashboard\dist (
    rmdir /s /q dashboard\dist
    echo  ✓ dashboard\dist removed
)
if exist dashboard\node_modules (
    rmdir /s /q dashboard\node_modules
    echo  ✓ node_modules removed
)

echo.
echo  ✓ Uninstall complete. Source code and .env are preserved.
echo.
pause
