# start-embodier.ps1 - Bulletproof Embodier Trader Launcher
# Usage: powershell -ExecutionPolicy Bypass -File start-embodier.ps1
# Or double-click start-embodier.bat
#
# WHAT THIS DOES:
#   1. Kills ALL zombie Python/Node processes from previous runs
#   2. Frees ports 8000 and 5173 (retries until no process holds them)
#   3. Clears DuckDB lock files that cause "file in use" errors
#   4. Creates .env files if missing
#   5. Waits for port 8000 to be free (retries ~10x; handles TIME_WAIT/PID 0)
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
Write-Host "    EMBODIER TRADER v5.0.0  Smart Launcher" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# ----------------------------------------------------------------
# PHASE 1: Kill zombie processes from previous runs
# ----------------------------------------------------------------
Write-Host "  [1/6] Cleaning up stale processes..." -ForegroundColor Yellow

$killedCount = 0

# Kill stale Python processes (uvicorn, start_server, etc) and their children
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -and ($cmd -match "elite-trading-system" -or $cmd -match "uvicorn" -or $cmd -match "start_server")) {
            & taskkill /F /T /PID $_.Id 2>$null | Out-Null
            $script:killedCount++
        }
    } catch {}
}

# Kill stale Node/Vite processes and their children
Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -and ($cmd -match "elite-trading-system" -or $cmd -match "vite")) {
            & taskkill /F /T /PID $_.Id 2>$null | Out-Null
            $script:killedCount++
        }
    } catch {}
}

# Force-free the backend and frontend ports (kill process tree so uvicorn/vite children release ports)
$portsToFree = @($BackendPort, $FrontendPort)
$maxPortRetries = 8
$portRetryDelay = 2
for ($r = 0; $r -lt $maxPortRetries; $r++) {
    $anyKilled = $false
    foreach ($p in $portsToFree) {
        Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 } |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object {
                $pidToKill = $_
                # Kill process tree (parent + children) so uvicorn reloader + workers all exit
                & taskkill /F /T /PID $pidToKill 2>$null | Out-Null
                $script:killedCount++
                $anyKilled = $true
                Write-Host "    Freed port $p (PID $pidToKill + tree)" -ForegroundColor Gray
            }
    }
    if (-not $anyKilled) { break }
    Start-Sleep -Seconds $portRetryDelay
}

if ($killedCount -gt 0) {
    Write-Host "    Killed $killedCount stale process(es)" -ForegroundColor Gray
    Write-Host "    Waiting 5s for ports and DuckDB to release..." -ForegroundColor DarkGray
} else {
    Write-Host "    No stale processes found" -ForegroundColor Gray
}

# Let OS release sockets and file handles (longer wait if we killed anything)
Start-Sleep -Seconds $(if ($killedCount -gt 0) { 5 } else { 3 })

# ----------------------------------------------------------------
# PHASE 2: Clear DuckDB lock files (backend/data/*.duckdb.wal, *.duckdb.tmp)
# ----------------------------------------------------------------
Write-Host "  [2/6] Clearing DuckDB locks..." -ForegroundColor Yellow

$lockCount = 0
Get-ChildItem -Path $BackendDir -Include "*.duckdb.wal","*.duckdb.tmp" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    Write-Host "    Removed $($_.Name)" -ForegroundColor Gray
    $lockCount++
}
if ($lockCount -eq 0) { Write-Host "    No stale locks found" -ForegroundColor Gray }
else { Start-Sleep -Seconds 1 }

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
# PHASE 3b: Ensure backend venv exists (fresh clone)
# ----------------------------------------------------------------
if (-not (Test-Path $PythonExe)) {
    Write-Host "  [3b] Backend venv not found." -ForegroundColor Yellow
    Write-Host "    Create it with:" -ForegroundColor Gray
    Write-Host "      cd $BackendDir" -ForegroundColor Gray
    Write-Host "      python -m venv venv" -ForegroundColor Gray
    Write-Host "      .\venv\Scripts\pip.exe install -r requirements.txt" -ForegroundColor Gray
    Write-Host "    See docs/PC1-SETUP.md for full run & verify steps." -ForegroundColor Gray
    Read-Host "  Press Enter to exit"
    exit 1
}

# ----------------------------------------------------------------
# PHASE 4: Verify backend port is free (retry until free or give up)
# ----------------------------------------------------------------
Write-Host "  [4/6] Verifying port $BackendPort is free..." -ForegroundColor Yellow

$maxVerifyRetries = 10
$verifyDelay = 4
$portFree = $false
for ($v = 0; $v -lt $maxVerifyRetries; $v++) {
    $conns = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue
    if (-not $conns) {
        $portFree = $true
        break
    }
    $pids = $conns.OwningProcess | Where-Object { $_ -ne 0 } | Select-Object -Unique
    if ($pids) {
        foreach ($pid in $pids) {
            & taskkill /F /T /PID $pid 2>$null | Out-Null
            Write-Host "    Killed PID $pid (tree) holding port $BackendPort" -ForegroundColor Gray
        }
    } else {
        # PID 0 = socket in TIME_WAIT or system; just wait for OS to release
        if ($v -eq 0) {
            Write-Host "    Port in TIME_WAIT, waiting for OS to release..." -ForegroundColor Gray
        }
    }
    if ($v -lt $maxVerifyRetries - 1) {
        Start-Sleep -Seconds $verifyDelay
    }
}

if (-not $portFree) {
    Write-Host "    ERROR: Port $BackendPort still in use after ${maxVerifyRetries} retries." -ForegroundColor Red
    Write-Host "    Close any app using port $BackendPort (e.g. another terminal running uvicorn) and try again." -ForegroundColor Yellow
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
Write-Host "    (Run only ONE instance - close other Embodier windows first)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Backend:   http://localhost:$BackendPort/docs" -ForegroundColor White
Write-Host "    Health:    http://localhost:$BackendPort/health" -ForegroundColor White
Write-Host "    Dashboard: http://localhost:$FrontendPort/dashboard" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend logs below. Ctrl+C stops everything." -ForegroundColor DarkGray
Write-Host "  If you see 'DuckDB file in use' or 'connection limit exceeded', close other Embodier windows and restart." -ForegroundColor DarkGray
Write-Host ""

# Auto-open browser after backend has time to start
$null = Start-Job -ScriptBlock {
    param($port)
    Start-Sleep -Seconds 10
    Start-Process "http://localhost:$port/dashboard"
} -ArgumentList $FrontendPort

# Run backend (this blocks until Ctrl+C)
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
