# run_frontend_autorestart.ps1 - Run frontend (Vite) with auto-restart on exit
# Usage: from repo root, or call from start-embodier.ps1 -Watch:
#   .\frontend-v2\scripts\run_frontend_autorestart.ps1 -FrontendPort 5173 -BackendPort 8000
#
# - Restarts when Vite process exits (crash or close).
# - Uses VITE_PORT and VITE_BACKEND_URL so proxy targets the correct backend.
# Press Ctrl+C once to stop the loop.

param(
    [int]$FrontendPort = 5173,
    [int]$BackendPort = 8000,
    [int]$RestartDelaySeconds = 2
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot | Split-Path -Parent | Split-Path -Parent
$FrontendDir = if (Test-Path (Join-Path $Root "frontend-v2")) { Join-Path $Root "frontend-v2" } else { $Root }
if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Host "ERROR: package.json not found in $FrontendDir" -ForegroundColor Red
    exit 1
}

Set-Location $FrontendDir
$runCount = 0
$BackendUrl = "http://localhost:$BackendPort"
$WsUrl = "ws://localhost:$BackendPort"

Write-Host ""
Write-Host "  Frontend auto-restart (port $FrontendPort, backend $BackendUrl, WS $WsUrl). Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "  Restart delay: ${RestartDelaySeconds}s" -ForegroundColor Gray
Write-Host ""

while ($true) {
    $runCount++
    Write-Host "  [Run #$runCount] Starting Vite..." -ForegroundColor Yellow
    $env:VITE_PORT = $FrontendPort.ToString()
    $env:VITE_BACKEND_URL = $BackendUrl
    $env:VITE_WS_URL = $WsUrl
    try {
        & npm run dev
    } catch {
        Write-Host "  Error: $_" -ForegroundColor Red
    }
    Write-Host "  Frontend exited. Restarting in ${RestartDelaySeconds}s..." -ForegroundColor Magenta
    Start-Sleep -Seconds $RestartDelaySeconds
}
