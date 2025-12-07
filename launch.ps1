Write-Host "🎯 ELITE TRADING SYSTEM - LAUNCHER" -ForegroundColor Cyan
Write-Host ""

$choice = Read-Host "Select: [1] Frontend [2] Backend [3] Both [4] Exit"

switch ($choice) {
    "1" {
        Write-Host "🌐 Starting Frontend..." -ForegroundColor Green
        cd frontend
        npm run dev
    }
    "2" {
        Write-Host "⚙️ Starting Backend..." -ForegroundColor Green
        cd backend
        .\venv\Scripts\Activate.ps1
        uvicorn main:app --reload --port 8000
    }
    "3" {
        Write-Host "🚀 Starting Both..." -ForegroundColor Green
        Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; .\venv\Scripts\Activate.ps1; uvicorn main:app --reload --port 8000"
        Start-Sleep -Seconds 3
        cd frontend
        npm run dev
    }
    "4" { exit }
    default { Write-Host "Invalid option" -ForegroundColor Red }
}
