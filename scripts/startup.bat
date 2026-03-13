@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Embodier Trader — Windows Startup Launcher
REM  Runs start-all.ps1 in a hidden PowerShell window.
REM  Place shortcut to this in shell:startup or register via
REM  register-startup.bat for Task Scheduler auto-start.
REM ═══════════════════════════════════════════════════════════════

set REPO=C:\Users\Espen\elite-trading-system

REM Start PowerShell minimized with the master startup script
start /MIN "" powershell.exe -ExecutionPolicy Bypass -WindowStyle Minimized -File "%REPO%\scripts\start-all.ps1"

REM Optional: Also launch Electron desktop app after a delay
REM (uncomment the next 2 lines to auto-launch the desktop UI)
REM timeout /t 10 /nobreak >nul
REM start "" "%REPO%\desktop\node_modules\.bin\electron.cmd" "%REPO%\desktop"
