# deploy-pc1.ps1 — Automated deploy for ESPENMAIN (PC1): pull, deps, restart backend + frontend, health check.
# Run from repo root: .\scripts\deploy-pc1.ps1
# Rollback: .\scripts\deploy-pc1.ps1 -Rollback

param(
    [switch]$Rollback,
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

Write-Host "`n  [PC1 Deploy] ESPENMAIN — $RepoRoot" -ForegroundColor Cyan

if ($Rollback) {
    $prev = git rev-parse HEAD~1
    Write-Host "  Rolling back to $prev" -ForegroundColor Yellow
    git reset --hard $prev
} else {
    git fetch origin main
    git pull origin main
}

Write-Host "  Installing backend deps..." -ForegroundColor Yellow
$venv = Join-Path $RepoRoot "backend\venv\Scripts\pip.exe"
if (Test-Path $venv) {
    & $venv install -r (Join-Path $RepoRoot "backend\requirements.txt") -q
} else {
    python -m pip install -r (Join-Path $RepoRoot "backend\requirements.txt") -q
}

# Restart: kill backend/frontend then start (call start-embodier so one place owns startup)
Write-Host "  Stopping backend (port 8000) and frontend (port 5173)..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.OwningProcess) { taskkill /F /T /PID $_.OwningProcess 2>$null | Out-Null }
}
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.OwningProcess) { taskkill /F /T /PID $_.OwningProcess 2>$null | Out-Null }
}
Start-Sleep -Seconds 2

Write-Host "  Starting backend and frontend (run start-embodier.ps1 in a separate window if you need full launcher)." -ForegroundColor Yellow
$backendDir = Join-Path $RepoRoot "backend"
$frontendDir = Join-Path $RepoRoot "frontend-v2"
$activate = Join-Path $backendDir "venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RepoRoot'; & '$activate'; cd backend; uvicorn app.main:app --host 0.0.0.0 --port 8000"
    Start-Sleep -Seconds 3
}
if (Test-Path (Join-Path $frontendDir "package.json")) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"
}

Start-Sleep -Seconds 5
Write-Host "  Health check..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "  OK /health: $($r.status)" -ForegroundColor Green
} catch {
    Write-Host "  WARN Backend not ready yet: $_" -ForegroundColor Yellow
}

Write-Host "`n  PC1 deploy done. Backend: :8000  Frontend: :5173`n" -ForegroundColor Green
