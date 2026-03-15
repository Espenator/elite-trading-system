# run_all_autorestart.ps1 - Start backend and frontend with auto-restart on failure (24/7)
# Usage: .\scripts\run_all_autorestart.ps1
#        .\scripts\run_all_autorestart.ps1 -CleanPorts   # kill processes on ports first, then start
#
# - Backend: runs in a separate window; restarts on crash or when /health fails (watchdog).
# - Frontend: runs in another window with auto-restart on exit.
# - Waits for backend to respond before starting frontend so API data flows immediately.
# - If .embodier-ports.json exists (e.g. from start-embodier.ps1), uses those ports.
# - With -CleanPorts: frees 8000/5173 (or next free in 8000..8010, 5173..5183) and writes .embodier-ports.json.
#
# For full bulletproof (cleanup + port resolution + watch): .\start-embodier.ps1 -Watch

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$BackendPortMax = 8010,
    [int]$FrontendPortMax = 5183,
    [int]$RestartDelaySeconds = 3,
    [int]$BackendWaitSeconds = 60,
    [switch]$CleanPorts
)

$ErrorActionPreference = "SilentlyContinue"
# When run as .\scripts\run_all_autorestart.ps1, PSScriptRoot is ...\scripts; repo root is parent
$Root = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { Split-Path -Parent $PSScriptRoot }
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

function Get-PortStatus {
    param([int]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if (-not $conns) { return "Free" }
        $listeners = $conns | Where-Object { $_.State -eq "Listen" }
        if (($listeners | Where-Object { $_.OwningProcess -gt 0 })) { return "InUseByProcess" }
        return "Stuck"
    } catch { return "Free" }
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

function Find-FreePort {
    param([int]$Preferred, [int]$MaxPort)
    for ($p = $Preferred; $p -le $MaxPort; $p++) {
        $status = Get-PortStatus -Port $p
        if ($status -eq "Free") { return $p }
        if ($status -eq "InUseByProcess") {
            Kill-ProcessesOnPort -Port $p
            Start-Sleep -Seconds 2
            if ((Get-PortStatus -Port $p) -eq "Free") { return $p }
        }
    }
    return $null
}

if ($CleanPorts) {
    Write-Host "  Cleaning and resolving ports..." -ForegroundColor Yellow
    Kill-ProcessesOnPort -Port $BackendPort
    Kill-ProcessesOnPort -Port $FrontendPort
    Start-Sleep -Seconds 2
    $resolvedBackend = Find-FreePort -Preferred $BackendPort -MaxPort $BackendPortMax
    $resolvedFrontend = Find-FreePort -Preferred $FrontendPort -MaxPort $FrontendPortMax
    if ($resolvedBackend) { $BackendPort = $resolvedBackend }
    if ($resolvedFrontend) { $FrontendPort = $resolvedFrontend }
    @{ backendPort = $BackendPort; frontendPort = $FrontendPort; updated = (Get-Date).ToString("o") } |
        ConvertTo-Json | Set-Content -Path $PortsFile -Encoding utf8 -Force
    Write-Host "  Using backend :$BackendPort, frontend :$FrontendPort (saved to .embodier-ports.json)" -ForegroundColor Gray
}

# Ensure frontend .env has VITE_PORT, VITE_BACKEND_URL, VITE_WS_URL (API + WebSocket auto-fixed)
$frontendEnv = Join-Path $FrontendDir ".env"
$backendUrl = "http://localhost:$BackendPort"
$wsUrl = "ws://localhost:$BackendPort"
if (Test-Path $frontendEnv) {
    $lines = Get-Content $frontendEnv -ErrorAction SilentlyContinue
    $hasPort = $false
    $hasBackend = $false
    $hasWs = $false
    $newLines = $lines | ForEach-Object {
        if ($_ -match "^\s*VITE_PORT\s*=") { $hasPort = $true; "VITE_PORT=$FrontendPort" }
        elseif ($_ -match "^\s*VITE_BACKEND_URL\s*=") { $hasBackend = $true; "VITE_BACKEND_URL=$backendUrl" }
        elseif ($_ -match "^\s*VITE_WS_URL\s*=") { $hasWs = $true; "VITE_WS_URL=$wsUrl" }
        else { $_ }
    }
    if (-not $hasPort) { $newLines += "VITE_PORT=$FrontendPort" }
    if (-not $hasBackend) { $newLines += "VITE_BACKEND_URL=$backendUrl" }
    if (-not $hasWs) { $newLines += "VITE_WS_URL=$wsUrl" }
    $newLines | Set-Content -Path $frontendEnv -Encoding utf8
} else {
    @("VITE_PORT=$FrontendPort", "VITE_BACKEND_URL=$backendUrl", "VITE_WS_URL=$wsUrl") | Set-Content -Path $frontendEnv -Encoding utf8
}

if (-not (Test-Path $BackendAutorestart)) {
    Write-Host "ERROR: $BackendAutorestart not found." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $FrontendAutorestart)) {
    Write-Host "ERROR: $FrontendAutorestart not found." -ForegroundColor Red
    exit 1
}

$HealthUrl = "http://127.0.0.1:${BackendPort}/healthz"

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
Write-Host "  Open http://localhost:${FrontendPort}/dashboard - data flows when backend is up." -ForegroundColor Green
Write-Host '  Close the backend/frontend windows to stop. For full port cleanup use: .\start-embodier.ps1 -Watch' -ForegroundColor DarkGray
Write-Host ""
