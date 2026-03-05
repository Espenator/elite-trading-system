# ============================================================================
# Embodier Trader - One-Click Launcher (Windows PowerShell)
#
# Usage: Right-click > "Run with PowerShell"
#   or:  .\start-embodier.ps1
#   or:  .\start-embodier.ps1 -SkipFrontend   (backend only)
#   or:  .\start-embodier.ps1 -Desktop         (launch Electron app)
# ============================================================================
param(
    [switch]$SkipFrontend,
    [switch]$Desktop,
    [int]$BackendPort = 8002
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend-v2"
$DesktopDir = Join-Path $RootDir "desktop"

function Log($msg) { Write-Host "[EMBODIER] $msg" -ForegroundColor Cyan }
function Ok($msg)  { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  EMBODIER TRADER v3.2.0 - AI-Powered Elite Trading" -ForegroundColor Magenta
Write-Host "  13-Agent Council | Event-Driven Pipeline" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""

# -- Prerequisite checks --
Log "Checking prerequisites..."

$pyVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) { Err "Python not found. Install from python.org"; exit 1 }
Ok "Python: $pyVersion"

$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) { Err "Node.js not found. Install from nodejs.org"; exit 1 }
Ok "Node.js: $nodeVersion"

# -- Step 1: Backend setup --
Log "Step 1/3: Setting up backend..."
Set-Location $BackendDir

if (-not (Test-Path "venv")) {
    Log "Creating Python virtual environment..."
    python -m venv venv
}

& .\venv\Scripts\Activate.ps1

try { $fastapiCheck = pip show fastapi 2>&1 } catch {}
if ($LASTEXITCODE -ne 0) {
    Log "Installing Python dependencies (first run)..."
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Err "pip install failed"; exit 1 }
}

if (-not (Test-Path ".env")) {
    Log "Creating .env from template..."
    Copy-Item "..\.env.example" ".env"
    (Get-Content .env) -replace "PORT=\d+", "PORT=$BackendPort" | Set-Content .env
    Ok "Created .env with port $BackendPort (edit to add API keys)"
} else {
    (Get-Content .env) -replace "PORT=\d+", "PORT=$BackendPort" | Set-Content .env
}

$existing = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue
if ($existing) {
    Warn "Port $BackendPort in use - attempting to free it..."
    $existing | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Log "Starting FastAPI backend on port $BackendPort..."
$backendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    & .\venv\Scripts\Activate.ps1
    python start_server.py
} -ArgumentList $BackendDir

Log "Waiting for backend to be ready..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/healthz" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch { }
    Write-Host "." -NoNewline
}
Write-Host ""

if ($ready) {
    Ok "Backend is ONLINE at http://localhost:$BackendPort"
    Ok "  API Docs: http://localhost:$BackendPort/docs"
    Ok "  Health:   http://localhost:$BackendPort/health"
} else {
    Warn "Backend may still be starting... check http://localhost:$BackendPort/healthz"
}

# -- Step 2: Frontend --
if (-not $SkipFrontend -and -not $Desktop) {
    Log "Step 2/3: Starting React frontend..."
    Set-Location $FrontendDir

    if (-not (Test-Path "node_modules")) {
        Log "Installing frontend dependencies (first run)..."
        npm install
    }

    $env:VITE_BACKEND_URL = "http://localhost:$BackendPort"

    $frontendJob = Start-Job -ScriptBlock {
        param($dir, $port)
        Set-Location $dir
        $env:VITE_BACKEND_URL = "http://localhost:$port"
        npm run dev
    } -ArgumentList $FrontendDir, $BackendPort

    Start-Sleep -Seconds 3
    Ok "Frontend starting at http://localhost:3000"
}

# -- Step 3: Desktop (optional) --
if ($Desktop) {
    Log "Step 3/3: Starting Electron desktop app..."
    Set-Location $DesktopDir

    if (-not (Test-Path "node_modules")) {
        Log "Installing desktop dependencies (first run)..."
        npm install
    }

    npm run dev
} else {
    Log "Step 3/3: Skipping desktop (use -Desktop flag to launch)"
}

# -- Summary --
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Embodier Trader is RUNNING!" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "  Backend API:  http://localhost:$BackendPort" -ForegroundColor Green
Write-Host "  Swagger Docs: http://localhost:$BackendPort/docs" -ForegroundColor Green
if (-not $SkipFrontend -and -not $Desktop) {
    Write-Host "  Dashboard:    http://localhost:3000" -ForegroundColor Green
}
Write-Host "" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

if (-not $SkipFrontend -and -not $Desktop) {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:3000"
}

try {
    while ($true) {
        Start-Sleep -Seconds 5
        if ($backendJob.State -eq "Failed") {
            Err "Backend crashed! Check logs above."
            Receive-Job $backendJob
            break
        }
    }
} finally {
    Log "Shutting down..."
    if ($backendJob) { Stop-Job $backendJob -ErrorAction SilentlyContinue; Remove-Job $backendJob -ErrorAction SilentlyContinue }
    if ($frontendJob) { Stop-Job $frontendJob -ErrorAction SilentlyContinue; Remove-Job $frontendJob -ErrorAction SilentlyContinue }
    Ok "All services stopped."
}
