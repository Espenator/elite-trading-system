# nuke-and-restart.ps1 — One command to rule them all
# Stops EVERYTHING, clears ports, clears DuckDB locks, restarts fresh.
# Works from ANY directory — desktop shortcut safe.
# Usage: .\nuke-and-restart.ps1
#        powershell -ExecutionPolicy Bypass -File "C:\Users\Espen\elite-trading-system\nuke-and-restart.ps1"

$ErrorActionPreference = "SilentlyContinue"

# ── Resolve repo root (works from shortcut, from any CWD, from script dir) ──
$Root = $null
if ($MyInvocation.MyCommand.Path) {
    $Root = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $Root -or -not (Test-Path (Join-Path $Root "backend"))) {
    # Hardcoded fallback — guarantees it works from desktop shortcut
    $Root = "C:\Users\Espen\elite-trading-system"
}
if (-not (Test-Path (Join-Path $Root "backend"))) {
    Write-Host "  ERROR: Cannot find repo at $Root" -ForegroundColor Red
    Write-Host "  Edit the `$Root path in nuke-and-restart.ps1 to match your repo location." -ForegroundColor Yellow
    Read-Host "  Press Enter to close"
    exit 1
}

$BackendDir = Join-Path $Root "backend"

# Change to repo root so all relative paths work
Set-Location $Root

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Red
Write-Host "    EMBODIER NUKE & RESTART — Full Clean Restart" -ForegroundColor Red
Write-Host "  ================================================" -ForegroundColor Red
Write-Host "  Repo: $Root" -ForegroundColor DarkGray
Write-Host ""

# ── Step 1: Kill ALL supervisors (they respawn things) ──
Write-Host "  [1/5] Killing supervisors..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    # Don't kill ourselves
    if ($_.ProcessId -eq $PID) { return }
    if ($cmd -match "run_backend_autorestart|run_full_stack_24_7|run_all_autorestart|start-embodier|start_embodier|watchdog|nuke-and-restart") {
        Write-Host "    Killed supervisor PID $($_.ProcessId)" -ForegroundColor Gray
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# ── Step 2: Kill ALL python/node processes related to this project ──
Write-Host "  [2/5] Killing backend + frontend processes..." -ForegroundColor Yellow
$killed = 0

# Kill python (uvicorn, start_server, etc.)
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "uvicorn|app\.main|run_server|elite-trading-system|start_server") {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
}

# Kill node (vite frontend)
Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "elite-trading-system|vite") {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
}

# Force-kill anything on ports 8000-8010 and 5173-5183
foreach ($port in 8000..8010 + 5173..5183) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -gt 0 } |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            taskkill /F /T /PID $_ 2>$null | Out-Null
            $killed++
        }
}

Write-Host "    Killed $killed process(es)" -ForegroundColor Gray

# ── Step 3: Wait for ports to fully release ──
Write-Host "  [3/5] Waiting for ports to release..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

# Verify ports are free
$stuck = @()
foreach ($port in @(8000, 5173)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
        $stuck += $port
    }
}
if ($stuck.Count -gt 0) {
    Write-Host "    Force-killed stubborn processes on port(s): $($stuck -join ', ')" -ForegroundColor Magenta
    Start-Sleep -Seconds 3
}
Write-Host "    Ports clear" -ForegroundColor Green

# ── Step 4: Clear DuckDB locks + stale PID files ──
Write-Host "  [4/5] Clearing DuckDB locks + PID files..." -ForegroundColor Yellow

$lockCount = 0
Get-ChildItem -Path $BackendDir -Include "*.duckdb.wal","*.duckdb.tmp" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    $lockCount++
}

$pidFile = Join-Path $BackendDir ".embodier.pid"
if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    $lockCount++
}

Write-Host "    Removed $lockCount lock/pid file(s)" -ForegroundColor Gray

# ── Step 5: Start fresh ──
Write-Host "  [5/5] Starting Embodier Trader..." -ForegroundColor Green
Write-Host ""

$launcher = Join-Path $Root "start-embodier.ps1"
if (Test-Path $launcher) {
    & $launcher
} else {
    Write-Host "  ERROR: start-embodier.ps1 not found at $launcher" -ForegroundColor Red
    Read-Host "  Press Enter to close"
    exit 1
}
