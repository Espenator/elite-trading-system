# stop_embodier.ps1 - Stop all Embodier backend/frontend processes to break the window loop
# Usage (from repo root):  .\scripts\stop_embodier.ps1
# Usage (from anywhere):  & "C:\Users\Espen\Dev\elite-trading-system\scripts\stop_embodier.ps1"
# Then start a single launcher: .\scripts\run_full_stack_24_7.ps1 -Supervisor -CleanPorts

$ErrorActionPreference = "SilentlyContinue"
$Root = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { Split-Path -Parent $PSScriptRoot }
$BackendDir = Join-Path $Root "backend"
$RepoName = "elite-trading-system"

# 1. Kill processes on backend/frontend ports (8000-8010, 5173-5183)
foreach ($port in 8000..8010 + 5173..5183) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $conns | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            Write-Host "  Killing PID $_ on port $port" -ForegroundColor Yellow
            taskkill /F /T /PID $_ 2>$null | Out-Null
        }
    }
}

# 2. Kill any python.exe whose command line contains this repo path or uvicorn/app.main
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "uvicorn|app\.main|run_server|$RepoName") {
        Write-Host "  Killing backend Python PID $($_.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 3. Kill any PowerShell running run_backend_autorestart / run_full_stack / start-embodier
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = if ($_.CommandLine) { $_.CommandLine } else { "" }
    if ($cmd -match "run_backend_autorestart|run_full_stack_24_7|run_all_autorestart|start-embodier|start-all\.ps1") {
        Write-Host "  Killing launcher PowerShell PID $($_.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "  Done. Close any remaining Embodier windows, then run:" -ForegroundColor Green
Write-Host "  .\scripts\run_full_stack_24_7.ps1 -Supervisor -CleanPorts" -ForegroundColor Cyan
Write-Host ""
