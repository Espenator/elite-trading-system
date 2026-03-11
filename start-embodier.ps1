# start-embodier.ps1 - Bulletproof Embodier Trader Launcher
# Usage: powershell -ExecutionPolicy Bypass -File start-embodier.ps1
# Or double-click start-embodier.bat
#
# WHAT THIS DOES:
#   1. Kills ALL zombie Python/Node processes from previous runs
#   2. Frees ports 8000 and 5173 if anything holds them
#   3. Clears DuckDB lock files that cause "file in use" errors
#   4. Creates .env files if missing
#   5. Verifies port is free before starting
#   6. Starts frontend + backend, auto-opens browser
#   7. Ctrl+C cleanly stops everything

param(
    [int]$BackendPort  = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = Get-Location }
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$PythonExe   = Join-Path $BackendDir "venv\Scripts\python.exe"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "    EMBODIER TRADER v4.1.0  Smart Launcher" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# ----------------------------------------------------------------
# PHASE 1: Kill zombie processes from previous runs
# ----------------------------------------------------------------
Write-Host "  [1/6] Cleaning up stale processes..." -ForegroundColor Yellow

$killedCount = 0

# Kill stale Python processes (uvicorn, start_server, etc)
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -and ($cmd -match "elite-trading-system" -or $cmd -match "uvicorn" -or $cmd -match "start_server")) {
            Stop-Process -Id $_.Id -Force
            $script:killedCount++
        }
    } catch {}
}

# Kill stale Node/Vite processes
Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -and ($cmd -match "elite-trading-system" -or $cmd -match "vite")) {
            Stop-Process -Id $_.Id -Force
            $script:killedCount++
        }
    } catch {}
}

# Force-free the backend and frontend ports
foreach ($p in @($BackendPort, $FrontendPort)) {
    Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -ne 0 } |
        ForEach-Object {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            $script:killedCount++
            Write-Host "    Freed port $p (PID $_)" -ForegroundColor Gray
        }
}

if ($killedCount -gt 0) {
    Write-Host "    Killed $killedCount stale process(es)" -ForegroundColor Gray
} else {
    Write-Host "    No stale processes found" -ForegroundColor Gray
}

# Let OS release sockets and file handles
Start-Sleep -Seconds 2

# ----------------------------------------------------------------
# PHASE 2: Clear DuckDB lock files
# ----------------------------------------------------------------
Write-Host "  [2/6] Clearing DuckDB locks..." -ForegroundColor Yellow

$lockCount = 0
Get-ChildItem -Path $BackendDir -Include "*.duckdb.wal","*.duckdb.tmp" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    Write-Host "    Removed $($_.Name)" -ForegroundColor Gray
    $lockCount++
}
if ($lockCount -eq 0) { Write-Host "    No stale locks found" -ForegroundColor Gray }

# ----------------------------------------------------------------
# PHASE 3: Ensure .env files exist
# ----------------------------------------------------------------
Write-Host "  [3/6] Checking environment files..." -ForegroundColor Yellow

$backendEnv = Join-Path $BackendDir ".env"
if (-not (Test-Path $backendEnv)) {
    $example = Join-Path $BackendDir ".env.example"
    if (Test-Path $example) {
        Copy-Item $example $backendEnv
        Write-Host "    Created backend/.env from .env.example" -ForegroundColor Gray
        Write-Host "    ** FILL IN YOUR API KEYS in backend/.env **" -ForegroundColor Red
    }
} else {
    Write-Host "    backend/.env exists" -ForegroundColor Gray
}

$frontendEnv = Join-Path $FrontendDir ".env"
if (-not (Test-Path $frontendEnv)) {
    "VITE_PORT=$FrontendPort`nVITE_BACKEND_URL=http://localhost:$BackendPort" | Out-File -FilePath $frontendEnv -Encoding utf8
    Write-Host "    Created frontend-v2/.env" -ForegroundColor Gray
} else {
    $content = Get-Content $frontendEnv -Raw -ErrorAction SilentlyContinue
    if ($content -and $content -notmatch "VITE_BACKEND_URL") {
        Add-Content $frontendEnv "`nVITE_BACKEND_URL=http://localhost:$BackendPort"
    }
    Write-Host "    frontend-v2/.env exists" -ForegroundColor Gray
}

# ----------------------------------------------------------------
# PHASE 4: Verify backend port is truly free
# ----------------------------------------------------------------
Write-Host "  [4/6] Verifying port $BackendPort is free..." -ForegroundColor Yellow

$portCheck = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "    ERROR: Port $BackendPort still in use!" -ForegroundColor Red
    Write-Host "    PIDs: $($portCheck.OwningProcess -join ', ')" -ForegroundColor Red
    Read-Host "  Press Enter to exit"
    exit 1
}
Write-Host "    Port $BackendPort is free" -ForegroundColor Green

# ----------------------------------------------------------------
# PHASE 5: Start frontend in a new window
# ----------------------------------------------------------------
Write-Host "  [5/6] Starting frontend..." -ForegroundColor Yellow

$feArgs = "-NoExit -Command `"Set-Location '$FrontendDir'; `$env:VITE_PORT='$FrontendPort'; `$env:VITE_BACKEND_URL='http://localhost:$BackendPort'; npm run dev`""
$frontendProc = Start-Process powershell -ArgumentList $feArgs -PassThru
Write-Host "    Frontend PID: $($frontendProc.Id)" -ForegroundColor Gray

Start-Sleep -Seconds 3

# ----------------------------------------------------------------
# PHASE 6: Start backend in THIS terminal
# ----------------------------------------------------------------
Write-Host "  [6/6] Starting backend on :$BackendPort..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Backend:   http://localhost:$BackendPort/docs" -ForegroundColor White
Write-Host "    Health:    http://localhost:$BackendPort/health" -ForegroundColor White
Write-Host "    Dashboard: http://localhost:$FrontendPort/dashboard" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend logs below. Ctrl+C stops everything." -ForegroundColor DarkGray
Write-Host ""

# Auto-open browser after backend has time to start
$null = Start-Job -ScriptBlock {
    param($port)
    Start-Sleep -Seconds 10
    Start-Process "http://localhost:$port/dashboard"
} -ArgumentList $FrontendPort

# Run backend — this blocks until Ctrl+C
try {
    Set-Location $BackendDir
    & $PythonExe start_server.py
} finally {
    Write-Host ""
    Write-Host "  Shutting down..." -ForegroundColor Yellow
    # Kill frontend window
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    # Kill any leftover vite nodes
    Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -and $cmd -match "vite") { Stop-Process -Id $_.Id -Force }
        } catch {}
    }
    Write-Host "  All services stopped." -ForegroundColor DarkGray
}
