@echo off
REM ============================================================
REM  Embodier Trader - One-Click Launcher
REM  Double-click this or use the desktop shortcut.
REM  Calls start-embodier.ps1 which handles everything:
REM    - Kills stale processes on ports 8001/5173
REM    - Verifies Python venv, Node.js, node_modules
REM    - Starts backend with health check polling
REM    - Starts frontend (Vite on port 5173)
REM    - Starts Electron desktop app (if desktop/ exists)
REM  Options: pass -NoElectron or -SkipFrontend
REM ============================================================
title Embodier Trader - Launching...
powershell -ExecutionPolicy Bypass -File "%~dp0start-embodier.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] Launcher failed. See errors above.
    pause
)
