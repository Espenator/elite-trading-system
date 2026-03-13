# kill_embodier.ps1 - Nuclear cleanup: kill all Embodier Trader processes before restart
# Usage (from repo root):  .\scripts\kill_embodier.ps1
# Usage (from anywhere):  & "C:\Users\Espen\Dev\elite-trading-system\scripts\kill_embodier.ps1"
# Run on ESPENMAIN when processes are stuck or ports are held. Then: .\start-embodier.ps1

$ErrorActionPreference = "SilentlyContinue"
$Root = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { Split-Path -Parent $PSScriptRoot }

Write-Host "=== Killing all Embodier Trader processes ===" -ForegroundColor Red

# 1. Kill all Python/uvicorn processes (backend)
Get-Process -Name python, python3, uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[OK] Python/uvicorn killed" -ForegroundColor Green

# 2. Kill all Node processes (frontend Vite dev server)
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[OK] Node killed" -ForegroundColor Green

# 3. DuckDB WAL/tmp — release lock holders (DuckDB is embedded in Python; .wal/.tmp can block restarts)
$duckdbDir = Join-Path $Root "backend\data"
if (Test-Path $duckdbDir) {
    Remove-Item (Join-Path $duckdbDir "analytics.duckdb.wal") -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $duckdbDir -Filter "*.tmp" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] DuckDB WAL/tmp files cleared" -ForegroundColor Green
} else {
    Write-Host "[SKIP] DuckDB data dir not found at $duckdbDir" -ForegroundColor Yellow
}

# 4. Free ports 8000 (backend) and 5173 (frontend)
foreach ($port in @(8000, 5173)) {
    $pids = (netstat -ano | Select-String ":$port\s" | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Sort-Object -Unique | Where-Object { $_ -ne "0" })
    foreach ($pid in $pids) {
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Killed PID $pid on port $port" -ForegroundColor Green
        } catch {}
    }
}
Write-Host "[OK] Ports 8000 + 5173 freed" -ForegroundColor Green

# 5. Kill any stale Redis (if running locally)
Get-Process -Name redis-server -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "[OK] Redis killed (if present)" -ForegroundColor Green

# 6. Small delay to let OS release everything
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "=== All clear. Ready to restart. ===" -ForegroundColor Cyan
Write-Host "Run: .\start-embodier.ps1" -ForegroundColor Cyan
