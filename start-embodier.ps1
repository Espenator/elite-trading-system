# start-embodier.ps1 - Embodier Trader Launcher (v5.0.0) — DEFAULT: run 24/7 with auto-restart
# Usage: .\start-embodier.ps1   # DEFAULT: stop existing, then run full stack 24/7 (CleanPorts + Supervisor, no Electron)
#        .\start-embodier.ps1 -OneShot   # one-shot start (no supervisor, backend in this window)
#        .\start-embodier.ps1 -Watch    # watch mode: backend + frontend auto-restart, press Enter to stop
#        .\start-embodier.ps1 -FullStack   # 24/7 with Electron
#
# Default (no args): runs .\scripts\stop_embodier.ps1 then .\scripts\run_full_stack_24_7.ps1 so the app runs and restarts automatically.

param(
    [int]$BackendPort  = 8000,
    [int]$FrontendPort = 5173,
    [int]$BackendPortMax  = 8010,
    [int]$FrontendPortMax = 5183,
    [switch]$Watch,
    [switch]$FullStack,
    [switch]$OneShot
)

$ErrorActionPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = Get-Location }
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$PythonExe   = Join-Path $BackendDir "venv\Scripts\python.exe"
$PortsFile   = Join-Path $Root ".embodier-ports.json"

# ----------------------------------------------------------------
# DEFAULT: Run 24/7 with auto-restart (stop existing, then full stack supervisor)
# ----------------------------------------------------------------
if (-not $Watch -and -not $FullStack -and -not $OneShot) {
    $stopScript = Join-Path $Root "scripts\stop_embodier.ps1"
    $runScript  = Join-Path $Root "scripts\run_full_stack_24_7.ps1"
    if (Test-Path $stopScript) {
        Write-Host "  Stopping any existing Embodier processes..." -ForegroundColor Yellow
        & $stopScript 2>$null
        Start-Sleep -Seconds 2
    }
    if (Test-Path $runScript) {
        Write-Host "  Starting 24/7 stack (auto-restart + supervisor)..." -ForegroundColor Cyan
        & $runScript
        exit 0
    }
}

# ----------------------------------------------------------------
# Helpers: port status and free-port discovery
# ----------------------------------------------------------------

function Get-PortStatus {
    param([int]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if (-not $conns) { return "Free" }
        $listeners = $conns | Where-Object { $_.State -eq "Listen" }
        $withPid   = $listeners | Where-Object { $_.OwningProcess -gt 0 }
        if ($withPid) { return "InUseByProcess" }
        if ($listeners) { return "Stuck" }  # Listen but no OwningProcess
        # TimeWait or other
        return "Stuck"
    } catch {
        return "Free"
    }
}

function Kill-ProcessesOnPort {
    param([int]$Port)
    $killed = 0
    try {
        Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -gt 0 } |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object {
                & taskkill /F /T /PID $_ 2>$null | Out-Null
                $script:killed++
            }
    } catch {}
    return $killed
}

function Find-FreeBackendPort {
    param([int]$Preferred, [int]$MaxPort)
    for ($p = $Preferred; $p -le $MaxPort; $p++) {
        $status = Get-PortStatus -Port $p
        if ($status -eq "Free") {
            return $p
        }
        if ($status -eq "InUseByProcess") {
            Kill-ProcessesOnPort -Port $p | Out-Null
            Start-Sleep -Seconds 2
            if ((Get-PortStatus -Port $p) -eq "Free") { return $p }
        }
        # Stuck (e.g. TIME_WAIT) — try next port
    }
    return $null
}

function Find-FreeFrontendPort {
    param([int]$Preferred, [int]$MaxPort)
    for ($p = $Preferred; $p -le $MaxPort; $p++) {
        if ((Get-PortStatus -Port $p) -eq "Free") { return $p }
        if ((Get-PortStatus -Port $p) -eq "InUseByProcess") {
            Kill-ProcessesOnPort -Port $p | Out-Null
            Start-Sleep -Seconds 2
            if ((Get-PortStatus -Port $p) -eq "Free") { return $p }
        }
    }
    return $null
}

# ----------------------------------------------------------------
# Banner
# ----------------------------------------------------------------
Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "    EMBODIER TRADER v5.0.0  Smart Launcher" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# ----------------------------------------------------------------
# PHASE 1: Clean stale processes (optional — frees ports for preferred)
# ----------------------------------------------------------------
Write-Host "  [1/6] Cleaning up stale processes..." -ForegroundColor Yellow

$killedCount = 0
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -and ($cmd -match "elite-trading-system" -or $cmd -match "uvicorn" -or $cmd -match "start_server")) {
            & taskkill /F /T /PID $_.Id 2>$null | Out-Null
            $killedCount++
        }
    } catch {}
}
Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmd -and ($cmd -match "elite-trading-system" -or $cmd -match "vite")) {
            & taskkill /F /T /PID $_.Id 2>$null | Out-Null
            $killedCount++
        }
    } catch {}
}

# Free preferred ports if something is still on them
foreach ($p in @($BackendPort, $FrontendPort)) {
    $killedCount += Kill-ProcessesOnPort -Port $p
}
if ($killedCount -gt 0) {
    Write-Host "    Killed $killedCount stale process(es); waiting 3s for release..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
} else {
    Write-Host "    No stale processes found" -ForegroundColor Gray
}

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

# (Frontend .env updated later with chosen ports)

# ----------------------------------------------------------------
# PHASE 3b: Backend venv
# ----------------------------------------------------------------
if (-not (Test-Path $PythonExe)) {
    Write-Host "  [3b] Backend venv not found." -ForegroundColor Yellow
    Write-Host "    Create it: cd $BackendDir; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Gray
    Read-Host "  Press Enter to exit"
    exit 1
}

# ----------------------------------------------------------------
# PHASE 4: Find free ports (fallback if preferred is stuck)
# ----------------------------------------------------------------
Write-Host "  [4/6] Resolving ports (backend $BackendPort..$BackendPortMax, frontend $FrontendPort..$FrontendPortMax)..." -ForegroundColor Yellow

$chosenBackend  = Find-FreeBackendPort -Preferred $BackendPort -MaxPort $BackendPortMax
$chosenFrontend = Find-FreeFrontendPort -Preferred $FrontendPort -MaxPort $FrontendPortMax

if (-not $chosenBackend) {
    Write-Host "    ERROR: No free backend port in range $BackendPort..$BackendPortMax." -ForegroundColor Red
    Write-Host "    Close other apps using these ports and try again." -ForegroundColor Yellow
    Read-Host "  Press Enter to exit"
    exit 1
}
if (-not $chosenFrontend) {
    Write-Host "    ERROR: No free frontend port in range $FrontendPort..$FrontendPortMax." -ForegroundColor Red
    Read-Host "  Press Enter to exit"
    exit 1
}

if ($chosenBackend -ne $BackendPort) {
    Write-Host "    Backend: using port $chosenBackend (preferred $BackendPort was busy)" -ForegroundColor Cyan
} else {
    Write-Host "    Backend: port $chosenBackend" -ForegroundColor Green
}
if ($chosenFrontend -ne $FrontendPort) {
    Write-Host "    Frontend: using port $chosenFrontend (preferred $FrontendPort was busy)" -ForegroundColor Cyan
} else {
    Write-Host "    Frontend: port $chosenFrontend" -ForegroundColor Green
}

# Persist chosen ports for other tools / user reference
@{
    backendPort  = $chosenBackend
    frontendPort = $chosenFrontend
    updated      = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Path $PortsFile -Encoding utf8 -Force
Write-Host "    Ports saved to .embodier-ports.json" -ForegroundColor DarkGray

# Update frontend .env so manual 'npm run dev' uses same ports (API + WebSocket)
$frontendEnv = Join-Path $FrontendDir ".env"
$backendUrlEnv = "http://localhost:$chosenBackend"
$wsUrlEnv = "ws://localhost:$chosenBackend"
if (Test-Path $frontendEnv) {
    $lines = Get-Content $frontendEnv -ErrorAction SilentlyContinue
    $hasPort = $false
    $hasBackend = $false
    $hasWs = $false
    $newLines = $lines | ForEach-Object {
        if ($_ -match "^\s*VITE_PORT\s*=") { $hasPort = $true; "VITE_PORT=$chosenFrontend" }
        elseif ($_ -match "^\s*VITE_BACKEND_URL\s*=") { $hasBackend = $true; "VITE_BACKEND_URL=$backendUrlEnv" }
        elseif ($_ -match "^\s*VITE_WS_URL\s*=") { $hasWs = $true; "VITE_WS_URL=$wsUrlEnv" }
        else { $_ }
    }
    if (-not $hasPort) { $newLines += "VITE_PORT=$chosenFrontend" }
    if (-not $hasBackend) { $newLines += "VITE_BACKEND_URL=$backendUrlEnv" }
    if (-not $hasWs) { $newLines += "VITE_WS_URL=$wsUrlEnv" }
    $newLines | Set-Content -Path $frontendEnv -Encoding utf8
}

# ----------------------------------------------------------------
# FULL STACK 24/7 with Electron (delegate to run_full_stack_24_7.ps1)
# ----------------------------------------------------------------
if ($FullStack) {
    $stopScript = Join-Path $Root "scripts\stop_embodier.ps1"
    $fullStackScript = Join-Path $Root "scripts\run_full_stack_24_7.ps1"
    if (Test-Path $stopScript) { & $stopScript 2>$null; Start-Sleep -Seconds 2 }
    if (Test-Path $fullStackScript) {
        & $fullStackScript -Electron
        exit 0
    }
    Write-Host "  ERROR: $fullStackScript not found." -ForegroundColor Red
    exit 1
}

# ----------------------------------------------------------------
# WATCH MODE: Auto-restart backend + frontend (bulletproof)
# ----------------------------------------------------------------
if ($Watch) {
    $backendScript = Join-Path $BackendDir "scripts\run_backend_autorestart.ps1"
    $frontendScript = Join-Path $FrontendDir "scripts\run_frontend_autorestart.ps1"
    if (-not (Test-Path $backendScript)) {
        Write-Host "  ERROR: $backendScript not found." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $frontendScript)) {
        Write-Host "  ERROR: $frontendScript not found." -ForegroundColor Red
        exit 1
    }
    Write-Host "  [Watch] Starting backend (auto-restart + health watchdog) on :$chosenBackend..." -ForegroundColor Yellow
    $backendProc = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScript, "-Port", $chosenBackend.ToString() -WorkingDirectory $Root -PassThru
    Write-Host "  [Watch] Waiting for backend health (max 90s)..." -ForegroundColor Gray
    $waited = 0
    $healthUrl = "http://127.0.0.1:$chosenBackend/health"
    while ($waited -lt 90) {
        Start-Sleep -Seconds 3
        $waited += 3
        try {
            $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Host "  [Watch] Backend ready after ${waited}s." -ForegroundColor Green
                break
            }
        } catch {}
        if ($waited -ge 90) {
            Write-Host "  [Watch] Backend did not respond in 90s; starting frontend anyway (will show OFFLINE until backend is up)." -ForegroundColor Yellow
        }
    }
    Write-Host "  [Watch] Starting frontend (auto-restart) on :$chosenFrontend..." -ForegroundColor Yellow
    $frontendProc = Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendScript, "-FrontendPort", $chosenFrontend.ToString(), "-BackendPort", $chosenBackend.ToString() -WorkingDirectory $Root -PassThru
    Write-Host ""
    Write-Host "  ============================================" -ForegroundColor Green
    Write-Host '    WATCH MODE - Backend and frontend auto-restart on crash' -ForegroundColor White
    Write-Host "    Backend:   http://localhost:$chosenBackend/docs" -ForegroundColor White
    Write-Host "    Dashboard: http://localhost:$chosenFrontend/dashboard" -ForegroundColor White
    Write-Host "  ============================================" -ForegroundColor Green
    Write-Host "  Press Enter in this window to stop both backend and frontend." -ForegroundColor DarkCyan
    Write-Host ""
    $null = Read-Host "  [Press Enter to stop all]"
    Write-Host "  Stopping backend and frontend windows..." -ForegroundColor Yellow
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  Done." -ForegroundColor DarkGray
    exit 0
}

# ----------------------------------------------------------------
# PHASE 5: Start frontend
# ----------------------------------------------------------------
Write-Host "  [5/6] Starting frontend on :$chosenFrontend..." -ForegroundColor Yellow

$feArgs = "-NoExit -Command `"Set-Location '$FrontendDir'; `$env:VITE_PORT='$chosenFrontend'; `$env:VITE_BACKEND_URL='http://localhost:$chosenBackend'; npm run dev`""
$frontendProc = Start-Process powershell -ArgumentList $feArgs -PassThru
Write-Host "    Frontend PID: $($frontendProc.Id)" -ForegroundColor Gray

Start-Sleep -Seconds 3

# ----------------------------------------------------------------
# PHASE 6: Start backend in this terminal (with PORT so it binds to chosen port)
# ----------------------------------------------------------------
Write-Host "  [6/6] Starting backend on :$chosenBackend..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Backend:   http://localhost:$chosenBackend/docs" -ForegroundColor White
Write-Host "    Health:    http://localhost:$chosenBackend/health" -ForegroundColor White
Write-Host "    Dashboard: http://localhost:$chosenFrontend/dashboard" -ForegroundColor White
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend logs below. Ctrl+C stops backend and frontend." -ForegroundColor DarkGray
Write-Host ""

# Auto-open browser
$null = Start-Job -ScriptBlock {
    param($port)
    Start-Sleep -Seconds 10
    Start-Process "http://localhost:$port/dashboard"
} -ArgumentList $chosenFrontend

# Run backend with chosen port (env so start_server.py / config reads it)
try {
    Set-Location $BackendDir
    $env:PORT = $chosenBackend
    & $PythonExe start_server.py
} finally {
    Write-Host ""
    Write-Host "  Shutting down..." -ForegroundColor Yellow
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -and $cmd -match "vite") { Stop-Process -Id $_.Id -Force }
        } catch {}
    }
    Write-Host '  All services stopped.' -ForegroundColor DarkGray
}
