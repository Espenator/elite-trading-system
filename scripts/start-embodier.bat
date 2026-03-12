@echo off
REM ============================================================
REM  Embodier Trader — Quick Start (Dev Mode)
REM  PC: ProfitTrader (secondary role)
REM ============================================================

title Embodier Trader - Starting...

set ROOT=%~dp0..
set BACKEND_DIR=%ROOT%\backend
set FRONTEND_DIR=%ROOT%\frontend-v2
set DESKTOP_DIR=%ROOT%\desktop

echo.
echo  ============================================
echo   Embodier Trader - Dev Mode Launch
echo   PC: ProfitTrader (secondary)
echo  ============================================
echo.

REM --- Start Backend ---
echo [1/3] Starting backend on port 8001...
cd /d "%BACKEND_DIR%"
if exist "venv\Scripts\python.exe" (
    start "Embodier-Backend" cmd /k "call venv\Scripts\activate.bat && python run_server.py"
) else (
    start "Embodier-Backend" cmd /k "python run_server.py"
)

echo  Waiting for backend to be ready...
timeout /t 10 /nobreak >nul

REM --- Start Frontend ---
echo [2/3] Starting frontend on port 3000...
cd /d "%FRONTEND_DIR%"
start "Embodier-Frontend" cmd /k "npm run dev"

echo  Waiting for Vite...
timeout /t 5 /nobreak >nul

REM --- Start Electron ---
echo [3/3] Starting Electron desktop app...
cd /d "%DESKTOP_DIR%"
set NODE_ENV=development
start "Embodier-Electron" cmd /k "npx electron ."

echo.
echo  ============================================
echo   All services launched!
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:3000
echo  ============================================
echo.
echo  Close this window - services run independently.
timeout /t 5 /nobreak >nul
