# start-embodier.ps1 — Start Embodier Trader (backend + frontend)
# Usage: powershell -ExecutionPolicy Bypass -File start-embodier.ps1

param(
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0
)

function Get-EnvValue($key, $default) {
    $val = [System.Environment]::GetEnvironmentVariable($key)
    if ($val) { return $val } else { return $default }
}

if ($BackendPort -eq 0) { $BackendPort = [int](Get-EnvValue "BACKEND_PORT" "8000") }
if ($FrontendPort -eq 0) { $FrontendPort = [int](Get-EnvValue "FRONTEND_PORT" "3000") }

# Banner
Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER  v4.1.0" -ForegroundColor DarkCyan
Write-Host "   Backend :$BackendPort  |  Frontend :$FrontendPort" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start backend
$backendJob = Start-Job -ScriptBlock {
    param($root, $port)
    Set-Location (Join-Path $root "backend")
    & ".\venv\Scripts\python" -m uvicorn app.main:app --host 0.0.0.0 --port $port
} -ArgumentList $Root, $BackendPort

Write-Host "  Backend starting on :$BackendPort..." -ForegroundColor Green
Start-Sleep -Seconds 3

# Start frontend
$frontendJob = Start-Job -ScriptBlock {
    param($root, $port)
    Set-Location (Join-Path $root "frontend-v2")
    $env:PORT = $port
    npm run dev
} -ArgumentList $Root, $FrontendPort

Write-Host "  Frontend starting on :$FrontendPort..." -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard: http://localhost:$FrontendPort/dashboard" -ForegroundColor White
Write-Host "  API docs:  http://localhost:$BackendPort/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor DarkGray

try {
    while ($true) {
        Start-Sleep -Seconds 5
        $backendState = (Get-Job -Id $backendJob.Id).State
        $frontendState = (Get-Job -Id $frontendJob.Id).State
        if ($backendState -eq 'Failed') {
            Write-Host "  [WARN] Backend job failed" -ForegroundColor Red
            Receive-Job -Id $backendJob.Id
        }
        if ($frontendState -eq 'Failed') {
            Write-Host "  [WARN] Frontend job failed" -ForegroundColor Red
            Receive-Job -Id $frontendJob.Id
        }
    }
} finally {
    Stop-Job -Id $backendJob.Id, $frontendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $backendJob.Id, $frontendJob.Id -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "  Services stopped." -ForegroundColor DarkGray
}
