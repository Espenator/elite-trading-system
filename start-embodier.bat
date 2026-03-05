@echo off
title Embodier Trader v3.2.0 - AI-Powered Elite Trading
color 0A
echo.
echo ============================================================
echo   EMBODIER TRADER v3.2.0 - AI-Powered Elite Trading
echo   13-Agent Council ^| Event-Driven Pipeline
echo ============================================================
echo.

REM Navigate to repo root (where this .bat lives)
cd /d "%~dp0"

REM Launch the PowerShell script
powershell -ExecutionPolicy Bypass -File ".\start-embodier.ps1"

pause
