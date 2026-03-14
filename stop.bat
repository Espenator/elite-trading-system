@echo off
echo Stopping Embodier Trader services...
taskkill /f /fi "WINDOWTITLE eq EmbodierBackend" >nul 2>nul
taskkill /f /fi "WINDOWTITLE eq EmbodierFrontend" >nul 2>nul
REM Also kill by port as fallback
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>nul
echo All services stopped.
timeout /t 2 >nul
