# run_all_autorestart.ps1 - Start backend and frontend with auto-restart on failure
# Usage: .\scripts\run_all_autorestart.ps1
#        .\scripts\run_all_autorestart.ps1 -CleanPorts   # kill processes on 8000/5173 first
#
# - Backend: runs in a separate window; restarts on crash or when /health fails (watchdog).
# - Frontend: runs in another window with auto-restart on exit.
# - Waits for backend to respond before starting frontend so data can flow immediately.
# - If .embodier-ports.json exists (e.g. from start-embodier.ps1), uses those ports.
#
# For full bulletproof (port conflict resolution + cleanup): .\start-embodier.ps1 -Watch

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$RestartDelaySeconds = 3,
    [int]$BackendWaitSeconds = 60,
    [switch]$CleanPorts
)

$ErrorActionPreference = "SilentlyContinue"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$PortsFile = Join-Path $Root ".embodier-ports.json"
$BackendAutorestart = Join-Path $BackendDir "scripts\run_backend_autorestart.ps1"
$FrontendAutorestart = Join-Path $FrontendDir "scripts\run_frontend_autorestart.ps1"

# Use ports from .embodier-ports.json if present (keeps in sync with start-embodier.ps1)
if (Test-Path $PortsFile) {
    try {
        $ports = Get-Content $PortsFile -Raw | ConvertFrom-Json
        if ($ports.backendPort) { $BackendPort = $ports.backendPort }
        if ($ports.frontendPort) { $FrontendPort = $ports.frontendPort }
    } catch {}
}

function Kill-ProcessesOnPort {
    param([int]$Port)
    try {
        Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -gt 0 } |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object { taskkill /F /T /PID $_ 2>$null | Out-Null }
    } catch {}
}

if ($CleanPorts) {
    Write-Host "  Cleaning ports $BackendPort and $FrontendPort..." -ForegroundColor Yellow
    Kill-ProcessesOnPort -Port $BackendPort
    Kill-ProcessesOnPort -Port $FrontendPort
    Start-Sleep -Seconds 2
}

if (-not (Test-Path $BackendAutorestart)) {
    Write-Host "ERROR: $BackendAutorestart not found." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $FrontendAutorestart)) {
    Write-Host "ERROR: $FrontendAutorestart not found." -ForegroundColor Red
    exit 1
}

$HealthUrl = "http://127.0.0.1:${BackendPort}/health"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "    Embodier Trader - Auto-restart launcher" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "  Backend  :$BackendPort (restarts on failure or health-check failure)" -ForegroundColor White
Write-Host "  Frontend :$FrontendPort (restarts on exit)" -ForegroundColor White
Write-Host "  Dashboard: http://localhost:${FrontendPort}/dashboard" -ForegroundColor Green
Write-Host ""

# Start backend in new window (auto-restart + health watchdog)
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $BackendAutorestart, "-Port", $BackendPort.ToString(), "-RestartDelaySeconds", $RestartDelaySeconds -WorkingDirectory $Root
Write-Host "  Backend window started (auto-restart + health watchdog)." -ForegroundColor Gray

# Wait for backend API to be up so Dashboard gets data when frontend loads
Write-Host "  Waiting for backend to respond (max ${BackendWaitSeconds}s)..." -ForegroundColor Gray
$waited = 0
while ($waited -lt $BackendWaitSeconds) {
    Start-Sleep -Seconds 2
    $waited += 2
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Host "  Backend ready after ${waited}s." -ForegroundColor Green
            break
        }
    } catch {}
    if ($waited -ge $BackendWaitSeconds) {
        Write-Host "  Backend did not respond in ${BackendWaitSeconds}s. Frontend will show API OFFLINE until backend is up." -ForegroundColor Yellow
    }
}

# Start frontend with auto-restart (same as start-embodier.ps1 -Watch)
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $FrontendAutorestart, "-FrontendPort", $FrontendPort.ToString(), "-BackendPort", $BackendPort.ToString() -WorkingDirectory $Root
Write-Host "  Frontend window started (auto-restart on exit)." -ForegroundColor Gray
Write-Host ""
Write-Host "  Open http://localhost:${FrontendPort}/dashboard — data flows when backend is up." -ForegroundColor Green
Write-Host "  Close the backend/frontend windows to stop. For full port cleanup use: .\start-embodier.ps1 -Watch" -ForegroundColor DarkGray
Write-Host ""
