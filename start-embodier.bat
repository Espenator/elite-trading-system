@echo off
title Embodier Trader v4.1.0
color 0A
cd /d "%~dp0"
echo.
echo  ============================================
echo   EMBODIER TRADER  v4.1.0
echo   Starting services...
echo  ============================================
echo.

:: Start backend
start "Embodier Backend" cmd /k "cd backend && .\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend
timeout /t 5 /nobreak >nul

:: Start frontend
start "Embodier Frontend" cmd /k "cd frontend-v2 && npm run dev"

echo.
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:3000
echo.
pause
