# ============================================================
#  Embodier Trader — Cold Start Cleanup (Step 0)
#  Run this BEFORE starting backend/frontend when things are broken.
#  Kills Python/Node, frees ports 8000/5173, clears DuckDB WAL/lock.
#  Usage: powershell -ExecutionPolicy Bypass -File scripts/cold-start-cleanup.ps1
# ============================================================

$ErrorActionPreference = "Continue"
$Root = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path) }
# If run from repo root, scripts/cold-start-cleanup.ps1 -> Root = scripts; go up one.
if ((Split-Path -Leaf $Root) -eq "scripts") { $Root = Split-Path -Parent $Root }
$BackendDir = Join-Path $Root "backend"

Write-Host "=== Killing all conflicting processes ===" -ForegroundColor Red
Get-Process -Name python, python3 -ErrorAction SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch {} }
Get-Process -Name node -ErrorAction SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch {} }
Start-Sleep -Seconds 3

$ports = @(8000, 5173)
foreach ($p in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($conn) {
        $procIds = $conn.OwningProcess | Select-Object -Unique
        foreach ($procId in $procIds) {
            if ($procId -gt 0) {
                Write-Host "WARNING: Port $p still in use by PID $procId" -ForegroundColor Yellow
                try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch {}
            }
        }
    } else {
        Write-Host "Port $p is free" -ForegroundColor Green
    }
}

# Clear DuckDB WAL/lock and SQLite WAL that cause "database locked" on startup
$patterns = @("*.wal", "*.lock", "*.tmp")
$removed = 0
foreach ($pat in $patterns) {
    Get-ChildItem -Path $BackendDir -Recurse -Include $pat -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        $removed++
    }
}
if ($removed -gt 0) {
    Write-Host "Removed $removed WAL/lock/tmp file(s) under backend/" -ForegroundColor Yellow
}

Write-Host "=== All clear ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Terminal 1: cd backend && venv\Scripts\Activate.ps1 && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Write-Host "  2. Wait for 'Uvicorn running on http://0.0.0.0:8000'"
Write-Host "  3. Verify: Invoke-RestMethod http://localhost:8000/api/v1/health"
Write-Host "  4. Terminal 2: cd frontend-v2 && npm install && npm run dev"
Write-Host "  5. Open http://localhost:5173/dashboard and check DevTools Network/WS"
Write-Host ""
