# stop_embodier.ps1 - Stop all Embodier backend/frontend/supervisor processes
# Usage (from repo root):  .\scripts\stop_embodier.ps1
# Usage (from anywhere):  & "C:\Users\Espen\elite-trading-system\scripts\stop_embodier.ps1"
# Then start a single launcher: .\scripts\run_full_stack_24_7.ps1 -Supervisor -CleanPorts

$ErrorActionPreference = "SilentlyContinue"
$Root = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { Split-Path -Parent $PSScriptRoot }
$BackendDir = Join-Path $Root "backend"
$PidFile = Join-Path $BackendDir ".embodier.pid"
# Use full repo path for matching (prevents killing unrelated projects)
$RepoPath = $Root -replace '\\', '\\\\'

Write-Host ""
Write-Host "  Stopping Embodier Trader..." -ForegroundColor Cyan

# 1. Kill any PowerShell supervisors FIRST (they respawn processes every 15s)
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "run_backend_autorestart|run_full_stack_24_7|run_all_autorestart|start-embodier|start_embodier|start-all\.ps1|watchdog") {
        Write-Host "  Killing supervisor PID $($_.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 2. Kill processes on backend/frontend ports (8000-8010, 5173-5183)
foreach ($port in 8000..8010 + 5173..5183) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $conns | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            Write-Host "  Killing PID $_ on port $port" -ForegroundColor Yellow
            taskkill /F /T /PID $_ 2>$null | Out-Null
        }
    }
}

# 3. Kill any python.exe whose command line contains this repo path or uvicorn/app.main
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "uvicorn|app\.main|run_server|$RepoPath") {
        Write-Host "  Killing backend Python PID $($_.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 4. Wait for ports to free, then verify
Start-Sleep -Seconds 3

$portsStillBound = $false
foreach ($port in @(8000, 5173)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Host "  Port $port still held by PID $($listener.OwningProcess) — force killing" -ForegroundColor Magenta
        Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
        $portsStillBound = $true
    }
}
if ($portsStillBound) {
    Start-Sleep -Seconds 2
}

# 5. Clean up stale PID file
if (Test-Path $PidFile) {
    try {
        $pidContent = Get-Content $PidFile -ErrorAction SilentlyContinue
        $pidLine = $pidContent | Where-Object { $_ -match "^pid=" }
        if ($pidLine) {
            $stalePid = [int]($pidLine -replace "^pid=", "")
            $proc = Get-Process -Id $stalePid -ErrorAction SilentlyContinue
            if (-not $proc) {
                Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                Write-Host "  Cleaned stale PID file (PID $stalePid)" -ForegroundColor Gray
            }
        } else {
            Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
            Write-Host "  Cleaned malformed PID file" -ForegroundColor Gray
        }
    } catch {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "  Done. All Embodier processes stopped." -ForegroundColor Green
Write-Host "  To start:  .\scripts\run_full_stack_24_7.ps1 -Supervisor -CleanPorts" -ForegroundColor Cyan
Write-Host ""
