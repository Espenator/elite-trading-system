# Embodier Trader — Start All Services
# Run this from PowerShell on ESPENMAIN
# Usage: Right-click → Run with PowerShell, or: .\start-all.ps1

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Embodier Trader — Starting All Services" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# --- 1. Pull latest from git ---
Write-Host "[1/5] Pulling latest code from git..." -ForegroundColor Yellow
Set-Location $RepoRoot
git pull origin main
Write-Host ""

# --- 2. Start Backend (FastAPI/Uvicorn) ---
Write-Host "[2/5] Starting Backend (FastAPI on port 8000)..." -ForegroundColor Yellow
$backendDir = Join-Path $RepoRoot "backend"
$venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"

$backendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$backendDir'; & '$venvActivate'; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
) -PassThru
Write-Host "  Backend PID: $($backendJob.Id)" -ForegroundColor Green

Start-Sleep -Seconds 3

# --- 3. Start Frontend (Vite on port 5173) ---
Write-Host "[3/5] Starting Frontend (Vite on port 5173)..." -ForegroundColor Yellow
$frontendDir = Join-Path $RepoRoot "frontend-v2"

$frontendJob = Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$frontendDir'; npm run dev"
) -PassThru
Write-Host "  Frontend PID: $($frontendJob.Id)" -ForegroundColor Green

Start-Sleep -Seconds 5

# --- 4. Open Browser ---
Write-Host "[4/5] Opening browser at http://localhost:5173/dashboard ..." -ForegroundColor Yellow
Start-Process "http://localhost:5173/dashboard"

# --- 5. Start Electron (optional) ---
Write-Host "[5/5] Starting Electron desktop app..." -ForegroundColor Yellow
$desktopDir = Join-Path $RepoRoot "desktop"
if (Test-Path (Join-Path $desktopDir "node_modules")) {
    $electronJob = Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$desktopDir'; npm start"
    ) -PassThru
    Write-Host "  Electron PID: $($electronJob.Id)" -ForegroundColor Green
} else {
    Write-Host "  Electron node_modules not found. Run 'cd desktop && npm install' first." -ForegroundColor Red
    Write-Host "  Installing now..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "Set-Location '$desktopDir'; npm install; npm start"
    ) -PassThru | Out-Null
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  All services launched!" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Electron: Desktop window" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Keep this window open. Close it to see service windows." -ForegroundColor DarkGray
Write-Host "Press any key to exit this launcher..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
