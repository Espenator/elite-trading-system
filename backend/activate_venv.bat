@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated!
echo.
echo You can now run:
echo   python start_server.py
echo   or
echo   python tools/test_api.py
echo.
cmd /k

