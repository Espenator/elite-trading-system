@echo off
REM ═══════════════════════════════════════════════════════════════
REM  Register Embodier Trader to auto-start on Windows login
REM  Uses Task Scheduler (more reliable than Startup folder)
REM  Run this script AS ADMINISTRATOR once.
REM ═══════════════════════════════════════════════════════════════

set TASK_NAME=EmbodierTrader-AutoStart
set REPO=C:\Users\Espen\elite-trading-system
set SCRIPT=%REPO%\scripts\start-all.ps1

echo.
echo  Embodier Trader — Auto-Start Registration
echo  ==========================================
echo.
echo  This will create a Task Scheduler task that:
echo    - Starts backend + frontend on Windows login
echo    - Auto-restarts crashed services
echo    - Runs with health monitoring
echo.

REM Delete existing task if it exists
schtasks /Delete /TN "%TASK_NAME%" /F 2>nul

REM Create new task that runs at user logon
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT%\"" ^
    /SC ONLOGON ^
    /RL HIGHEST ^
    /DELAY 0000:30 ^
    /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  [OK] Task "%TASK_NAME%" registered successfully!
    echo  Services will auto-start 30 seconds after login.
    echo.
    echo  To remove: schtasks /Delete /TN "%TASK_NAME%" /F
    echo  To run now: schtasks /Run /TN "%TASK_NAME%"
    echo.
) else (
    echo.
    echo  [ERROR] Failed to register task. Try running as Administrator.
    echo.
)

pause
