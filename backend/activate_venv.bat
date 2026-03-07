@echo off
echo Activating Embodier Trader virtual environment...
call venv\Scripts\activate.bat
echo.
echo Ready. You can now run:
echo   python start_server.py
echo   pytest tests/ -v
echo.
cmd /k
