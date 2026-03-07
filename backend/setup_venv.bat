@echo off
echo Setting up Embodier Trader Backend...
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created!
) else (
    echo Virtual environment already exists.
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete!
echo.
echo To start the server, run: start.bat
echo Or from the repo root: start-embodier.bat
pause
