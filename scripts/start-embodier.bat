@echo off
REM ============================================================
REM  Embodier Trader — One-Click Launcher
REM  Double-click this or use the desktop shortcut.
REM  Calls start-embodier.ps1 which handles everything:
REM    - Kills stale processes on ports 8001/3000
REM    - Verifies Python venv, Node.js, node_modules
REM    - Starts backend with health check polling
REM    - Starts frontend (Vite)
REM    - Starts Electron desktop app
REM ============================================================
title Embodier Trader - Launching...
powershell -ExecutionPolicy Bypass -File "%~dp0start-embodier.ps1"
