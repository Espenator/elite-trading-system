@echo off
title Embodier Trader v4.1.0
color 0A
cd /d "%~dp0"
echo.
echo   ============================================
echo    EMBODIER TRADER - Starting...
echo   ============================================
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File ".\start-embodier.ps1"
if errorlevel 1 (
    echo.
    echo   [ERROR] Start-up failed. Check the error above.
    echo.
)
pause
