# nuke-and-restart.ps1 — One command to rule them all
# Stops EVERYTHING, clears ports, clears DuckDB locks, restarts fresh.
# Usage: .\nuke-and-restart.ps1

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = Get-Location }
$BackendDir = Join-Path $Root "backend"

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Red
Write-Host "    EMBODIER NUKE & RESTART — Full Clean Restart" -ForegroundColor Red
Write-Host "  ================================================" -ForegroundColor Red
Write-Host ""

# ── Step 1: Kill ALL supervisors (they respawn things) ──
Write-Host "  [1/5] Killing supervisors..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "run_backend_autorestart|run_full_stack_24_7|run_all_autorestart|start-embodier|start_embodier|watchdog") {
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
}
