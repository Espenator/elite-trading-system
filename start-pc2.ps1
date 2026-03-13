# Embodier Trader — PC2 (ProfitTrader) FULL AUTO Launcher
# ============================================================================
# ONE script to rule them all. Handles:
#   - Kill stale processes on all ports
#   - Git pull latest code
#   - npm install if node_modules broken
#   - Start backend (uvicorn on port 8001) with auto-restart
#   - Start frontend (Vite on port 3000) with auto-restart
#   - Start Ollama if available
#   - Start brain_service if available
#   - Health monitoring loop — restarts anything that dies
#   - Opens browser when ready
#   - Runs 24/7 until you close this window
#
# Usage:
#   .\start-pc2.ps1              # Full auto start
#   .\start-pc2.ps1 -SkipPull    # Skip git pull
#   .\start-pc2.ps1 -DryRun      # Show what would happen
# ============================================================================

param(
    [switch]$DryRun,
    [switch]$SkipPull,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend-v2"
$BrainDir = Join-Path $RepoRoot "brain_service"
$LogDir = Join-Path $RepoRoot "scripts\logs"
$BackendPort = 8001
$FrontendPort = 3000
$BrainPort = 50051
$OllamaPort = 11434

# Ensure log dir exists
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# ── Helper Functions ─────────────────────────────────────────────────────

function Write-Step($num, $total, $msg) {
    Write-Host "[$num/$total] $msg" -ForegroundColor Yellow
}

function Write-Ok($msg) { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ! $msg" -ForegroundColor DarkYellow }
function Write-Fail($msg) { Write-Host "  ✗ $msg" -ForegroundColor Red }

function Kill-Port($port) {
    try {
        $lines = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
        foreach ($line in $lines) {
            $parts = $line.ToString().Trim() -split '\s+'
            $pid = $parts[-1]
            if ($pid -and $pid -ne "0") {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                $name = if ($proc) { $proc.ProcessName } else { "unknown" }
                Write-Host "  Killing PID $pid ($name) on port $port" -ForegroundColor DarkGray
                taskkill /PID $pid /F /T 2>$null | Out-Null
                Start-Sleep -Milliseconds 500
            }
        }
    } catch {}
}

function Test-Port($port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-ForPort($port, $timeoutSec = 60, $label = "") {
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
        if (Test-Port $port) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

# ── Global process tracking ──────────────────────────────────────────────
$script:BackendProc = $null
$script:FrontendProc = $null
$script:BrainProc = $null
$script:BackendCrashes = 0
$script:FrontendCrashes = 0
$script:BrainCrashes = 0
$script:MaxCrashes = 20
$script:Running = $true

# ══════════════════════════════════════════════════════════════════════════
# MAIN STARTUP
# ══════════════════════════════════════════════════════════════════════════

Clear-Host
Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  EMBODIER TRADER — PC2 (ProfitTrader) 24/7 Auto-Launcher" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkCyan
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$hostname = [System.Net.Dns]::GetHostName()
Write-Host "  Hostname: $hostname" -ForegroundColor Gray
Write-Host "  Repo:     $RepoRoot" -ForegroundColor Gray
Write-Host "  Role:     PC2 (secondary) — Backend:$BackendPort Frontend:$FrontendPort" -ForegroundColor Gray
Write-Host ""

if ($DryRun) {
    Write-Host "  *** DRY RUN MODE — nothing will be started ***" -ForegroundColor Magenta
    Write-Host ""
}

$totalSteps = 7

# ── Step 1: Git Pull ─────────────────────────────────────────────────────
if (-not $SkipPull) {
    Write-Step 1 $totalSteps "Pulling latest code..."
    Set-Location $RepoRoot
    $pullResult = git pull origin main 2>&1
    $pullResult | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    Write-Ok "Git pull done"
} else {
    Write-Step 1 $totalSteps "Skipping git pull"
}
Write-Host ""

# ── Step 2: Clear All Ports ──────────────────────────────────────────────
Write-Step 2 $totalSteps "Clearing stale processes on ports..."
Kill-Port $BackendPort
Kill-Port $FrontendPort
Kill-Port $BrainPort
# Don't kill Ollama — it may be system-managed
Write-Ok "Ports cleared ($BackendPort, $FrontendPort, $BrainPort)"
Write-Host ""

# ── Step 3: Verify Environment ──────────────────────────────────────────
Write-Step 3 $totalSteps "Verifying environment..."

# Python venv
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $BackendDir "venv\Scripts\uvicorn.exe"
if (Test-Path $VenvPython) {
    Write-Ok "Python venv found"
} else {
    Write-Fail "Python venv MISSING at $VenvPython"
    Write-Host "  Run: cd backend && python -m venv venv && venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    if (-not $DryRun) { exit 1 }
}

# Node/npm
$npmPath = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($npmPath) {
    $nodeVer = node --version 2>$null
    Write-Ok "Node $nodeVer found"
} else {
    Write-Fail "Node/npm NOT found — frontend won't start"
}

# Frontend node_modules
$rollupCheck = Join-Path $FrontendDir "node_modules\@rollup\rollup-win32-x64-msvc"
if (-not (Test-Path $rollupCheck)) {
    Write-Warn "Frontend node_modules missing or broken — running npm install..."
    if (-not $DryRun) {
        Set-Location $FrontendDir
        # Clean broken state
        if (Test-Path (Join-Path $FrontendDir "node_modules")) {
            Remove-Item -Recurse -Force (Join-Path $FrontendDir "node_modules") -ErrorAction SilentlyContinue
        }
        if (Test-Path (Join-Path $FrontendDir "package-lock.json")) {
            Remove-Item -Force (Join-Path $FrontendDir "package-lock.json") -ErrorAction SilentlyContinue
        }
        npm install 2>&1 | Select-Object -Last 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        Write-Ok "npm install complete"
    }
} else {
    Write-Ok "Frontend node_modules OK"
}

# .env file
$envFile = Join-Path $BackendDir ".env"
if (Test-Path $envFile) {
    Write-Ok ".env file present"
} else {
    Write-Fail ".env file MISSING at $envFile"
}

# Ollama
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Ok "Ollama found"
} else {
    Write-Warn "Ollama not found — brain_service will use remote fallback"
}

Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN complete. Would start:" -ForegroundColor Magenta
    Write-Host "  - Backend (uvicorn) on port $BackendPort"
    Write-Host "  - Frontend (Vite) on port $FrontendPort"
    Write-Host "  - Brain Service (gRPC) on port $BrainPort"
    Write-Host "  - Health monitor loop every 30s with auto-restart"
    exit 0
}

# ── Step 4: Start Backend ───────────────────────────────────────────────
Write-Step 4 $totalSteps "Starting Backend (port $BackendPort)..."

$backendLog = Join-Path $LogDir "backend.log"
$backendErr = Join-Path $LogDir "backend.err.log"

$script:BackendProc = Start-Process -FilePath $VenvUvicorn -ArgumentList @(
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "$BackendPort",
    "--reload"
) -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr

Write-Host "  PID: $($script:BackendProc.Id)" -ForegroundColor DarkGray

# Wait for backend to be ready
Write-Host "  Waiting for backend..." -ForegroundColor DarkGray -NoNewline
if (Wait-ForPort $BackendPort 45) {
    Write-Ok "Backend READY on port $BackendPort"
} else {
    Write-Warn "Backend not responding yet — monitor loop will keep checking"
}
Write-Host ""

# ── Step 5: Start Frontend ──────────────────────────────────────────────
Write-Step 5 $totalSteps "Starting Frontend (port $FrontendPort)..."

$frontendLog = Join-Path $LogDir "frontend.log"
$frontendErr = Join-Path $LogDir "frontend.err.log"

$script:FrontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev") `
    -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr

Write-Host "  PID: $($script:FrontendProc.Id)" -ForegroundColor DarkGray

Write-Host "  Waiting for Vite..." -ForegroundColor DarkGray -NoNewline
if (Wait-ForPort $FrontendPort 30) {
    Write-Ok "Frontend READY on port $FrontendPort"
} else {
    Write-Warn "Frontend not responding yet — monitor loop will keep checking"
}
Write-Host ""

# ── Step 6: Start Brain Service ─────────────────────────────────────────
Write-Step 6 $totalSteps "Starting Brain Service (port $BrainPort)..."

$brainServer = Join-Path $BrainDir "server.py"
if ((Test-Path $brainServer) -and (Test-Path $VenvPython)) {
    $brainLog = Join-Path $LogDir "brain_service.log"
    $brainErr = Join-Path $LogDir "brain_service.err.log"

    $script:BrainProc = Start-Process -FilePath $VenvPython -ArgumentList @($brainServer) `
        -WorkingDirectory $BrainDir -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $brainLog -RedirectStandardError $brainErr

    Write-Host "  PID: $($script:BrainProc.Id)" -ForegroundColor DarkGray
    Write-Ok "Brain service started"
} else {
    Write-Warn "Brain service not available (server.py not found)"
}
Write-Host ""

# ── Step 7: Open Browser ───────────────────────────────────────────────
if (-not $NoBrowser) {
    Write-Step 7 $totalSteps "Opening browser..."
    Start-Process "http://localhost:$FrontendPort"
    Start-Process "http://localhost:$BackendPort/docs"
    Write-Ok "Browser opened (Dashboard + API docs)"
} else {
    Write-Step 7 $totalSteps "Skipping browser (use -NoBrowser)"
}

# ══════════════════════════════════════════════════════════════════════════
# 24/7 HEALTH MONITOR LOOP
# ══════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ALL SERVICES RUNNING — 24/7 Health Monitor Active" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:$BackendPort" -ForegroundColor White
Write-Host "  Frontend: http://localhost:$FrontendPort" -ForegroundColor White
Write-Host "  Brain:    gRPC :$BrainPort" -ForegroundColor White
Write-Host "  Logs:     $LogDir" -ForegroundColor DarkGray
Write-Host "  Press CTRL+C to stop everything" -ForegroundColor DarkYellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

# Trap CTRL+C for graceful shutdown
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    $script:Running = $false
}
trap {
    $script:Running = $false
    Write-Host "`n[SHUTDOWN] Stopping all services..." -ForegroundColor Yellow
    if ($script:BackendProc -and -not $script:BackendProc.HasExited) {
        taskkill /PID $script:BackendProc.Id /F /T 2>$null | Out-Null
    }
    if ($script:FrontendProc -and -not $script:FrontendProc.HasExited) {
        taskkill /PID $script:FrontendProc.Id /F /T 2>$null | Out-Null
    }
    if ($script:BrainProc -and -not $script:BrainProc.HasExited) {
        taskkill /PID $script:BrainProc.Id /F /T 2>$null | Out-Null
    }
    Write-Host "[SHUTDOWN] All services stopped." -ForegroundColor Yellow
    break
}

function Restart-Backend {
    Write-Host "  [RESTART] Backend (crash #$($script:BackendCrashes + 1))..." -ForegroundColor Yellow
    $script:BackendCrashes++
    Kill-Port $BackendPort
    Start-Sleep -Seconds 2

    $backendLog = Join-Path $LogDir "backend.log"
    $backendErr = Join-Path $LogDir "backend.err.log"

    $script:BackendProc = Start-Process -FilePath $VenvUvicorn -ArgumentList @(
        "app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort", "--reload"
    ) -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden `
      -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr

    Write-Host "  [RESTART] Backend restarted (PID $($script:BackendProc.Id))" -ForegroundColor Green
}

function Restart-Frontend {
    Write-Host "  [RESTART] Frontend (crash #$($script:FrontendCrashes + 1))..." -ForegroundColor Yellow
    $script:FrontendCrashes++
    Kill-Port $FrontendPort
    Start-Sleep -Seconds 2

    $frontendLog = Join-Path $LogDir "frontend.log"
    $frontendErr = Join-Path $LogDir "frontend.err.log"

    $script:FrontendProc = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev") `
        -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr

    Write-Host "  [RESTART] Frontend restarted (PID $($script:FrontendProc.Id))" -ForegroundColor Green
}

function Restart-Brain {
    Write-Host "  [RESTART] Brain Service (crash #$($script:BrainCrashes + 1))..." -ForegroundColor Yellow
    $script:BrainCrashes++

    $brainLog = Join-Path $LogDir "brain_service.log"
    $brainErr = Join-Path $LogDir "brain_service.err.log"

    $script:BrainProc = Start-Process -FilePath $VenvPython -ArgumentList @($brainServer) `
        -WorkingDirectory $BrainDir -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $brainLog -RedirectStandardError $brainErr

    Write-Host "  [RESTART] Brain restarted (PID $($script:BrainProc.Id))" -ForegroundColor Green
}

# ── Main loop: check every 30 seconds ───────────────────────────────────
$checkInterval = 30
$iteration = 0

while ($script:Running) {
    Start-Sleep -Seconds $checkInterval
    $iteration++
    $now = Get-Date -Format "HH:mm:ss"

    $backendAlive = $script:BackendProc -and -not $script:BackendProc.HasExited
    $frontendAlive = $script:FrontendProc -and -not $script:FrontendProc.HasExited
    $brainAlive = $script:BrainProc -and -not $script:BrainProc.HasExited

    $backendPort = if (Test-Port $BackendPort) { "OK" } else { "DOWN" }
    $frontendPort = if (Test-Port $FrontendPort) { "OK" } else { "DOWN" }

    $bIcon = if ($backendAlive -and $backendPort -eq "OK") { "OK" } elseif ($backendAlive) { ".." } else { "XX" }
    $fIcon = if ($frontendAlive -and $frontendPort -eq "OK") { "OK" } elseif ($frontendAlive) { ".." } else { "XX" }
    $brIcon = if ($brainAlive) { "OK" } else { "--" }

    # Status line every 5 checks (2.5 min)
    if ($iteration % 5 -eq 0) {
        Write-Host "[$now] Backend=$bIcon(:$BackendPort) | Frontend=$fIcon(:$FrontendPort) | Brain=$brIcon | Restarts: B=$($script:BackendCrashes) F=$($script:FrontendCrashes)" -ForegroundColor DarkGray
    }

    # Auto-restart crashed services
    if (-not $backendAlive -and $script:BackendCrashes -lt $script:MaxCrashes) {
        Restart-Backend
    }
    if (-not $frontendAlive -and $script:FrontendCrashes -lt $script:MaxCrashes) {
        Restart-Frontend
    }
    if (-not $brainAlive -and $script:BrainProc -and $script:BrainCrashes -lt $script:MaxCrashes) {
        Restart-Brain
    }

    # If port is down but process alive, something is wrong — kill and restart
    if ($backendAlive -and $backendPort -eq "DOWN" -and $iteration -gt 2) {
        Write-Host "[$now] Backend process alive but port $BackendPort not responding — restarting" -ForegroundColor Yellow
        taskkill /PID $script:BackendProc.Id /F /T 2>$null | Out-Null
        Start-Sleep -Seconds 2
        Restart-Backend
    }
    if ($frontendAlive -and $frontendPort -eq "DOWN" -and $iteration -gt 2) {
        Write-Host "[$now] Frontend process alive but port $FrontendPort not responding — restarting" -ForegroundColor Yellow
        taskkill /PID $script:FrontendProc.Id /F /T 2>$null | Out-Null
        Start-Sleep -Seconds 2
        Restart-Frontend
    }
}
