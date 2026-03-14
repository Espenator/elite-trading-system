@echo off
title Embodier Trader - Starting...
setlocal

REM Use script directory for all paths
set "ROOT=%~dp0"

REM Check prerequisites
where python >nul 2>nul || (echo [ERROR] Python not found in PATH! & pause & exit /b 1)
where node >nul 2>nul || (echo [ERROR] Node.js not found in PATH! & pause & exit /b 1)

echo.
echo  ====================================
echo   Embodier Trader - Unified Launcher
echo  ====================================
echo.

REM Start backend
echo [1/4] Starting backend on port 8001...
start "EmbodierBackend" /min cmd /c "cd /d "%ROOT%backend" && python run_server.py"

REM Wait for backend to be ready
echo [2/4] Waiting for backend...
set /a TRIES=0
:wait_backend
timeout /t 2 /nobreak >nul
set /a TRIES+=1
curl -s http://localhost:8001/api/v1/system/health-check >nul 2>nul
if errorlevel 1 (
    if %TRIES% GEQ 30 (
        echo [WARN] Backend not responding after 60s. Continuing anyway...
        goto start_frontend
    )
    echo        Attempt %TRIES%/30...
    goto wait_backend
)
echo        Backend ready!

:start_frontend
REM Start frontend
echo [3/4] Starting frontend on port 5173...
start "EmbodierFrontend" /min cmd /c "cd /d "%ROOT%frontend-v2" && npm run dev"

REM Wait for frontend
echo [4/4] Waiting for frontend...
timeout /t 5 /nobreak >nul

REM Open browser
start http://localhost:5173/dashboard

echo.
echo  ====================================
echo   Embodier Trader is running!
echo  ------------------------------------
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8001
echo   API Docs:  http://localhost:8001/docs
echo  ====================================
echo.
echo  Press any key to STOP all services...
pause >nul

REM Cleanup
echo Stopping services...
taskkill /f /fi "WINDOWTITLE eq EmbodierBackend" >nul 2>nul
taskkill /f /fi "WINDOWTITLE eq EmbodierFrontend" >nul 2>nul
echo Done.
endlocal
