@echo off
title Embodier Trader
echo.
echo  ==============================
echo   Embodier Trader - Launching
echo  ==============================
echo.

:: Navigate to desktop directory
cd /d "%~dp0desktop"

:: Check if node_modules exists
if not exist "node_modules" goto :install
goto :start

:install
echo Installing Electron dependencies (first run)...
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed. Make sure Node.js 18+ is installed.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

:start
echo Starting Embodier Trader...
call npm start

if errorlevel 1 (
    echo.
    echo Embodier Trader exited with an error.
    pause
)
