@echo off
echo ========================================
echo ELITE TRADER TERMINAL - UNIFIED LAUNCH
echo ========================================
echo.

echo Starting Backend API Server...
start "Elite Trader Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8000"

timeout /t 3 /nobreak > nul

echo Starting Frontend UI...
start "Elite Trader Frontend" cmd /k "cd /d %~dp0glass-house-ui && npm run dev"

timeout /t 2 /nobreak > nul

echo.
echo ========================================
echo ELITE TRADER TERMINAL LAUNCHED
echo ========================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo WebSocket: ws://localhost:8000/ws
echo.
echo Press any key to open in browser...
pause > nul

start http://localhost:3000

echo.
echo System is running. Close both windows to stop.
