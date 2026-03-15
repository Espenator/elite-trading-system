# Embodier Trader — PC1 (ESPENMAIN) Launcher with Auto-Restart Supervisor
# ============================================================================
# This is the ONE script to run on PC1. It starts all PC1 services with
# auto-restart, health monitoring, and auto-debug logging.
#
# Usage:
#   .\start-pc1.ps1              # Normal start with supervisor
#   .\start-pc1.ps1 -DryRun      # Show what would start
#   .\start-pc1.ps1 -NoBrowser   # Skip opening browser
#
# PC1 Role: Backend API, Frontend, DuckDB, Trading Execution, Electron Desktop
# Services managed: Backend (8000), Frontend (3000), Electron Desktop
# ============================================================================

param(
    [switch]$DryRun,
    [switch]$NoBrowser,
    [switch]$SkipGitPull
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  EMBODIER TRADER — PC1 (ESPENMAIN) Supervisor" -ForegroundColor Cyan
Write-Host "  Role: Backend API | Frontend | Trading Execution" -ForegroundColor DarkCyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$hostname = [System.Net.Dns]::GetHostName()
Write-Host "[INFO] Hostname: $hostname" -ForegroundColor Gray
Write-Host "[INFO] Repo: $RepoRoot" -ForegroundColor Gray
Write-Host ""

# --- Git pull ---
if (-not $SkipGitPull) {
    Write-Host "[1/5] Pulling latest code..." -ForegroundColor Yellow
    Set-Location $RepoRoot
    git pull origin main 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    Write-Host ""
}

# --- Environment check ---
Write-Host "[2/5] Checking environment..." -ForegroundColor Yellow
$venvPython = Join-Path $RepoRoot "backend\venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Host "  Python venv: OK" -ForegroundColor Green
} else {
    Write-Host "  Python venv: MISSING" -ForegroundColor Red
    if (-not $DryRun) { exit 1 }
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
    Write-Host "  Node/npm: OK ($(node --version))" -ForegroundColor Green
} else {
    Write-Host "  Node/npm: MISSING" -ForegroundColor Red
}
Write-Host ""

# --- Launch supervisor ---
if ($DryRun) {
    & $venvPython (Join-Path $RepoRoot "scripts\service_supervisor.py") --role pc1 --dry-run
} else {
    if (-not $NoBrowser) {
        Start-Job -ScriptBlock {
            Start-Sleep -Seconds 12
            Start-Process "http://localhost:3000/dashboard"
        } | Out-Null
        Write-Host "[3/5] Browser will open in ~12 seconds..." -ForegroundColor Yellow
    }

    Write-Host "[4/5] Starting all services with auto-restart..." -ForegroundColor Green
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Services: Backend(:8000) | Frontend(:5173) | Electron" -ForegroundColor White
    Write-Host "  Auto-restart: ON | Health checks: every 30s" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    & $venvPython (Join-Path $RepoRoot "scripts\service_supervisor.py") --role pc1

    Write-Host ""
    Write-Host "[5/5] Supervisor exited." -ForegroundColor Yellow
}
