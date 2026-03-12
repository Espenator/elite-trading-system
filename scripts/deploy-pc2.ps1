# deploy-pc2.ps1 — Automated deploy for ProfitTrader (PC2): pull, deps, restart brain_service, health check.
# Run from repo root: .\scripts\deploy-pc2.ps1
# Rollback: .\scripts\deploy-pc2.ps1 -Rollback

param(
    [switch]$Rollback,
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

Write-Host "`n  [PC2 Deploy] ProfitTrader — $RepoRoot" -ForegroundColor Cyan

if ($Rollback) {
    $prev = git rev-parse HEAD~1
    Write-Host "  Rolling back to $prev" -ForegroundColor Yellow
    git reset --hard $prev
} else {
    git fetch origin main
    git pull origin main
}

# Backend venv (optional on PC2 for discovery)
$backendVenv = Join-Path $RepoRoot "backend\venv\Scripts\pip.exe"
if (Test-Path $backendVenv) {
    Write-Host "  Installing backend deps..." -ForegroundColor Yellow
    & $backendVenv install -r (Join-Path $RepoRoot "backend\requirements.txt") -q
}

# Brain service
$brainDir = Join-Path $RepoRoot "brain_service"
$brainVenv = Join-Path $brainDir "venv\Scripts\pip.exe"
if (Test-Path (Join-Path $brainDir "requirements.txt")) {
    Write-Host "  Installing brain_service deps..." -ForegroundColor Yellow
    if (Test-Path $brainVenv) {
        & $brainVenv install -r (Join-Path $brainDir "requirements.txt") -q
    } else {
        python -m pip install -r (Join-Path $brainDir "requirements.txt") -q
    }
}

# Restart brain_service (port 50051)
Get-NetTCPConnection -LocalPort 50051 -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.OwningProcess) { taskkill /F /T /PID $_.OwningProcess 2>$null | Out-Null }
}
Start-Sleep -Seconds 2

Write-Host "  Starting brain_service (gRPC :50051)..." -ForegroundColor Yellow
$activate = Join-Path $brainDir "venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$brainDir'; & '$activate'; python server.py"
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$brainDir'; python server.py"
}

Start-Sleep -Seconds 4
Write-Host "  Health check (brain :50051)..." -ForegroundColor Yellow
try {
    $tcp = New-Object System.Net.Sockets.TcpClient("localhost", 50051)
    $tcp.Close()
    Write-Host "  OK brain_service listening on :50051" -ForegroundColor Green
} catch {
    Write-Host "  WARN brain_service not ready: $_" -ForegroundColor Yellow
}

Write-Host "`n  PC2 deploy done. Brain gRPC: :50051`n" -ForegroundColor Green
