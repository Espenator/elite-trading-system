# Embodier Trader — PC2 (ProfitTrader) Launcher with Auto-Restart Supervisor
# ============================================================================
# This is the ONE script to run on PC2. It starts all PC2 services with
# auto-restart, health monitoring, and auto-debug logging.
#
# Usage:
#   .\start-pc2.ps1              # Normal start with supervisor
#   .\start-pc2.ps1 -DryRun      # Show what would start
#   .\start-pc2.ps1 -NoBrowser   # Skip opening browser
#
# PC2 Role: GPU training, ML inference, brain_service (gRPC), Ollama LLM
# Services managed: Backend (8001), Frontend (5173), Brain Service (50051), Ollama (11434)
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
Write-Host "  EMBODIER TRADER — PC2 (ProfitTrader) Supervisor" -ForegroundColor Cyan
Write-Host "  Role: GPU Training | ML Inference | Brain Service" -ForegroundColor DarkCyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- 0. Confirm identity ---
$hostname = [System.Net.Dns]::GetHostName()
Write-Host "[INFO] Hostname: $hostname" -ForegroundColor Gray
Write-Host "[INFO] Repo: $RepoRoot" -ForegroundColor Gray
Write-Host ""

# --- 1. Git pull ---
if (-not $SkipGitPull) {
    Write-Host "[1/6] Pulling latest code..." -ForegroundColor Yellow
    Set-Location $RepoRoot
    git pull origin main 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    Write-Host ""
}

# --- 2. Environment check ---
Write-Host "[2/6] Checking environment..." -ForegroundColor Yellow
$envFile = Join-Path $RepoRoot "backend\.env"
if (Test-Path $envFile) {
    $role = (Get-Content $envFile | Where-Object { $_ -match "^PC_ROLE=" }) -replace "PC_ROLE=", ""
    $port = (Get-Content $envFile | Where-Object { $_ -match "^PORT=" }) -replace "PORT=", ""
    Write-Host "  PC_ROLE=$role, PORT=$port" -ForegroundColor Green
} else {
    Write-Host "  WARNING: backend\.env not found!" -ForegroundColor Red
}

# Check Python venv
$venvPython = Join-Path $RepoRoot "backend\venv\Scripts\python.exe"
$venvUvicorn = Join-Path $RepoRoot "backend\venv\Scripts\uvicorn.exe"
if (Test-Path $venvPython) {
    Write-Host "  Python venv: OK" -ForegroundColor Green
} else {
    Write-Host "  Python venv: MISSING — run 'cd backend && python -m venv venv && venv\Scripts\pip install -r requirements.txt'" -ForegroundColor Red
    if (-not $DryRun) { exit 1 }
}

# Check Node
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
    Write-Host "  Node/npm: OK ($(node --version))" -ForegroundColor Green
} else {
    Write-Host "  Node/npm: MISSING" -ForegroundColor Red
}

# Check Ollama
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Write-Host "  Ollama: FOUND" -ForegroundColor Green
} else {
    Write-Host "  Ollama: NOT FOUND (brain_service will use fallback)" -ForegroundColor Yellow
}
Write-Host ""

# --- 3. Launch via Python supervisor ---
if ($DryRun) {
    Write-Host "[3/6] DRY RUN — supervisor would start these services:" -ForegroundColor Yellow
    & $venvPython (Join-Path $RepoRoot "scripts\service_supervisor.py") --role pc2 --dry-run
} else {
    Write-Host "[3/6] Starting Service Supervisor (auto-restart enabled)..." -ForegroundColor Yellow
    Write-Host "  Log: scripts\logs\supervisor.log" -ForegroundColor DarkGray
    Write-Host "  Press CTRL+C to stop all services" -ForegroundColor DarkGray
    Write-Host ""

    # Open browser after a delay (non-blocking)
    if (-not $NoBrowser) {
        Start-Job -ScriptBlock {
            Start-Sleep -Seconds 10
            Start-Process "http://localhost:5173/dashboard"
            Start-Process "http://localhost:$using:port/docs"
        } | Out-Null
        Write-Host "[4/6] Browser will open in ~10 seconds..." -ForegroundColor Yellow
    }

    Write-Host "[5/6] Starting all services with auto-restart..." -ForegroundColor Green
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Services: Backend(:$port) | Frontend(:5173) | Brain(:50051) | Ollama(:11434)" -ForegroundColor White
    Write-Host "  Auto-restart: ON | Health checks: every 30s | Crash budget: 10/15min" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Run supervisor (blocking — monitors and auto-restarts)
    & $venvPython (Join-Path $RepoRoot "scripts\service_supervisor.py") --role pc2

    Write-Host ""
    Write-Host "[6/6] Supervisor exited. All services stopped." -ForegroundColor Yellow
}
