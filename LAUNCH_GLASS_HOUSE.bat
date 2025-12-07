@echo off
color 0A
title ELITE GLASS HOUSE TRADING SYSTEM

echo.
echo ========================================
echo  ELITE GLASS HOUSE TRADING SYSTEM
echo  Version 7.0 - Aurora Edition
echo ========================================
echo.

cd /d C:\Users\Espen\elite-trading-system

echo [1/3] Starting FastAPI Backend (Port 8000)...
start "BACKEND API" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak > nul

echo [2/3] Starting Glass House UI (Port 3000)...
cd glass-house-ui
start "GLASS HOUSE UI" cmd /k "npm run dev"
timeout /t 10 /nobreak > nul

echo [3/3] Opening browsers...
start http://localhost:8000/docs
timeout /t 2 /nobreak > nul
start http://localhost:3000

echo.
echo ========================================
echo  SYSTEM READY!
echo ========================================
echo  Backend API: http://localhost:8000/docs
echo  Glass House: http://localhost:3000
echo ========================================
echo.

pause
