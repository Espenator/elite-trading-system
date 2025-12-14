@echo off
title Elite Trading System Launcher
color 0A
echo ========================================
echo  ELITE TRADING SYSTEM v2.0
echo ========================================

REM Kill existing processes
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1

echo [1/3] Starting Backend Server...
cd /d C:\Users\espen\elite-trading-system\backend
start "Backend API" cmd /k "python -m uvicorn app.main:app --reload --port 8000"

echo [2/3] Waiting for backend...
timeout /t 8 /nobreak >nul

echo [3/3] Starting Frontend...
cd /d C:\Users\espen\elite-trading-system\frontend
start "Frontend Dev" cmd /k "npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ? SYSTEM ONLINE!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.

start http://localhost:3000
pause
