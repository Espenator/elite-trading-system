# run_full_stack_24_7.ps1 - Start backend + frontend with auto-restart (24/7) — DEFAULTS: CleanPorts, Supervisor, NoElectron
# Usage: .\scripts\run_full_stack_24_7.ps1   # runs automatically with port cleanup + supervisor + backend/frontend only
#        .\scripts\run_full_stack_24_7.ps1 -NoCleanPorts -NoSupervisor   # one-shot, no supervisor
#        .\scripts\run_full_stack_24_7.ps1 -Electron   # include Electron desktop
#
# Default (no args): CleanPorts + Supervisor + NoElectron = app runs and restarts automatically 24/7.

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$BackendPortMax = 8010,
    [int]$FrontendPortMax = 5183,
    [int]$RestartDelaySeconds = 3,
    [int]$BackendWaitSeconds = 120,
    [int]$SupervisorCheckSeconds = 15,
    [switch]$CleanPorts,
    [switch]$NoCleanPorts,
    [switch]$NoElectron,
    [switch]$Electron,
    [switch]$Supervisor,
    [switch]$NoSupervisor,
    [switch]$EnableAutoExecute,
    [switch]$NoEnableAutoExecute
)

$env:PYTHONUTF8 = "1"

# Hardcode 24/7 defaults: port clearing, supervisor, no Electron, auto-execute enabled
if (-not $NoCleanPorts) { $CleanPorts = $true }
if (-not $NoSupervisor) { $Supervisor = $true }
if (-not $Electron) { $NoElectron = $true }
if (-not $NoEnableAutoExecute) { $EnableAutoExecute = $true }

$ErrorActionPreference = "SilentlyContinue"
$Root = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { Split-Path -Parent $PSScriptRoot }
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$DesktopDir = Join-Path $Root "desktop"
$PortsFile = Join-Path $Root ".embodier-ports.json"
$BackendAutorestart = Join-Path $BackendDir "scripts\run_backend_autorestart.ps1"
$FrontendAutorestart = Join-Path $FrontendDir "scripts\run_frontend_autorestart.ps1"
$ElectronAutorestart = Join-Path $DesktopDir "scripts\run_electron_autorestart.ps1"

# Use ports from .embodier-ports.json only when NOT cleaning (so default run always uses 8000/5173 after clear)
if (-not $CleanPorts -and (Test-Path $PortsFile)) {
    try {
        $ports = Get-Content $PortsFile -Raw | ConvertFrom-Json
        if ($ports.backendPort) { $BackendPort = $ports.backendPort }
        if ($ports.frontendPort) { $FrontendPort = $ports.frontendPort }
    } catch {}
}

function Get-PortStatus { param([int]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if (-not $conns) { return "Free" }
        $listeners = $conns | Where-Object { $_.State -eq "Listen" }
        if (($listeners | Where-Object { $_.OwningProcess -gt 0 })) { return "InUseByProcess" }
        return "Stuck"
    } catch { return "Free" }
}

function Kill-ProcessesOnPort { param([int]$Port)
    try {
        Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -gt 0 } |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object { taskkill /F /T /PID $_ 2>$null | Out-Null }
    } catch {}
}

function Find-FreePort { param([int]$Preferred, [int]$MaxPort)
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

if (-not (Test-Path $BackendAutorestart)) { Write-Host "ERROR: $BackendAutorestart not found." -ForegroundColor Red; exit 1 }
if (-not (Test-Path $FrontendAutorestart)) { Write-Host "ERROR: $FrontendAutorestart not found." -ForegroundColor Red; exit 1 }

# Use /healthz (lightweight liveness probe, <50ms) — /api/v1/health is too heavy
# and times out during DuckDB init, causing false restarts
$HealthUrl = "http://127.0.0.1:${BackendPort}/healthz"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "    Embodier Trader - Full stack 24/7 (PC1)" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "  Backend  :$BackendPort (restarts on failure or health-check failure)" -ForegroundColor White
Write-Host "  Frontend :$FrontendPort (restarts on exit)" -ForegroundColor White
if (-not $NoElectron) { Write-Host "  Electron : auto-restart on exit" -ForegroundColor White }
if ($Supervisor) {
    Write-Host "  Supervisor: THIS window keeps all components running 24/7. Do not close." -ForegroundColor Yellow
}
Write-Host "  Dashboard: http://localhost:${FrontendPort}/dashboard" -ForegroundColor Green
Write-Host ""

# Clean stale PID file before starting backend
$pidFile = Join-Path $BackendDir ".embodier.pid"
if (Test-Path $pidFile) {
    try {
        $pidContent = Get-Content $pidFile -ErrorAction SilentlyContinue
        $pidLine = $pidContent | Where-Object { $_ -match "^pid=" }
        if ($pidLine) {
            $stalePid = [int]($pidLine -replace "^pid=", "")
            $proc = Get-Process -Id $stalePid -ErrorAction SilentlyContinue
            if (-not $proc) {
                Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
                Write-Host "  Cleaned stale PID file (PID $stalePid)" -ForegroundColor Gray
            }
        }
    } catch {}
}

# Start backend in new window (with -PassThru when Supervisor so we can monitor/restart)
$backendArgs = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $BackendAutorestart, "-Port", $BackendPort.ToString(), "-RestartDelaySeconds", $RestartDelaySeconds, "-StartupGraceSeconds", "120")
$backendProc = Start-Process powershell -ArgumentList $backendArgs -WorkingDirectory $Root -PassThru
Write-Host "  Backend window started (PID $($backendProc.Id))." -ForegroundColor Gray

# Wait for backend API
Write-Host "  Waiting for backend to respond (max ${BackendWaitSeconds}s)..." -ForegroundColor Gray
$waited = 0
while ($waited -lt $BackendWaitSeconds) {
    Start-Sleep -Seconds 2
    $waited += 2
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Host "  Backend ready after ${waited}s." -ForegroundColor Green
            if ($EnableAutoExecute) {
                try {
                    $autoUrl = "http://127.0.0.1:${BackendPort}/api/v1/metrics/auto-execute"
                    Invoke-RestMethod -Uri $autoUrl -Method POST -ContentType "application/json" -Body '{"enabled":true}' -TimeoutSec 5 -ErrorAction Stop
                    Write-Host "  Auto-execute enabled via API." -ForegroundColor Green
                } catch {
                    Write-Host "  Auto-execute API skipped (set AUTO_EXECUTE_TRADES=true in backend/.env for 24/7)." -ForegroundColor Gray
                }
            }
            break
        }
    } catch {}
    if ($waited -ge $BackendWaitSeconds) {
        Write-Host "  Backend did not respond in ${BackendWaitSeconds}s. Frontend will show API OFFLINE until backend is up." -ForegroundColor Yellow
    }
}

# Start frontend in new window
$frontendArgs = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $FrontendAutorestart, "-FrontendPort", $FrontendPort.ToString(), "-BackendPort", $BackendPort.ToString())
$frontendProc = Start-Process powershell -ArgumentList $frontendArgs -WorkingDirectory $Root -PassThru
Write-Host "  Frontend window started (PID $($frontendProc.Id))." -ForegroundColor Gray

# Start Electron in new window (optional)
$electronProc = $null
$electronArgs = @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $ElectronAutorestart)
if (-not $NoElectron -and (Test-Path $ElectronAutorestart)) {
    $electronProc = Start-Process powershell -ArgumentList $electronArgs -WorkingDirectory $Root -PassThru
    Write-Host "  Electron window started (PID $($electronProc.Id))." -ForegroundColor Gray
} elseif (-not $NoElectron) {
    Write-Host "  Electron script not found at $ElectronAutorestart - skipping." -ForegroundColor Yellow
}

# Supervisor loop: keep this window open and restart any component that exits
if ($Supervisor) {
    Write-Host ""
    Write-Host "  --- 24/7 Supervisor active. Check every ${SupervisorCheckSeconds}s + health every 60s. Ctrl+C to stop. ---" -ForegroundColor Cyan
    Write-Host ""
    $supervisorHealthFailCount = 0
    $supervisorCheckCount = 0
    $healthCheckEveryN = [math]::Max(1, [math]::Floor(60 / $SupervisorCheckSeconds))  # Health check every ~60s
    $supervisorStartTime = Get-Date

    while ($true) {
        Start-Sleep -Seconds $SupervisorCheckSeconds
        $restarted = $false
        $supervisorCheckCount++

        if ($backendProc -and $backendProc.HasExited) {
            Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Backend exited (code $($backendProc.ExitCode)). Restarting..." -ForegroundColor Magenta
            $backendProc = Start-Process powershell -ArgumentList $backendArgs -WorkingDirectory $Root -PassThru
            Write-Host "  Backend restarted (PID $($backendProc.Id))." -ForegroundColor Green
            $supervisorHealthFailCount = 0
            $supervisorStartTime = Get-Date
            $restarted = $true
        }
        if ($frontendProc -and $frontendProc.HasExited) {
            Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Frontend exited (code $($frontendProc.ExitCode)). Restarting..." -ForegroundColor Magenta
            $frontendProc = Start-Process powershell -ArgumentList $frontendArgs -WorkingDirectory $Root -PassThru
            Write-Host "  Frontend restarted (PID $($frontendProc.Id))." -ForegroundColor Green
            $restarted = $true
        }
        if ($electronProc -and $electronProc.HasExited) {
            Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Electron exited (code $($electronProc.ExitCode)). Restarting..." -ForegroundColor Magenta
            $electronProc = Start-Process powershell -ArgumentList $electronArgs -WorkingDirectory $Root -PassThru
            Write-Host "  Electron restarted (PID $($electronProc.Id))." -ForegroundColor Green
            $restarted = $true
        }

        # Periodic health check: detect hung backends (process alive but not responding)
        $elapsed = ((Get-Date) - $supervisorStartTime).TotalSeconds
        if ((-not $restarted) -and ($supervisorCheckCount % $healthCheckEveryN -eq 0) -and ($elapsed -gt 120) -and ($backendProc -and -not $backendProc.HasExited)) {
            try {
                $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
                if ($r.StatusCode -eq 200) {
                    $supervisorHealthFailCount = 0
                }
            } catch {
                $supervisorHealthFailCount++
                Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Supervisor health check failed ($supervisorHealthFailCount/3)" -ForegroundColor DarkYellow
                if ($supervisorHealthFailCount -ge 3) {
                    Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Backend hung (process alive but API unresponsive). Killing autorestart window..." -ForegroundColor Red
                    try { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue } catch {}
                    Start-Sleep -Seconds 3
                    $backendProc = Start-Process powershell -ArgumentList $backendArgs -WorkingDirectory $Root -PassThru
                    Write-Host "  Backend restarted (PID $($backendProc.Id))." -ForegroundColor Green
                    $supervisorHealthFailCount = 0
                    $supervisorStartTime = Get-Date
                    $restarted = $true
                }
            }
        }

        if (-not $restarted) {
            $b = if ($backendProc -and -not $backendProc.HasExited) { "OK" } else { "DOWN" }
            $f = if ($frontendProc -and -not $frontendProc.HasExited) { "OK" } else { "DOWN" }
            $e = if (-not $electronProc) { "n/a" } elseif (-not $electronProc.HasExited) { "OK" } else { "DOWN" }
            Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Backend=$b | Frontend=$f | Electron=$e" -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
Write-Host "  Open http://localhost:${FrontendPort}/dashboard - close any window to stop that component." -ForegroundColor Green
Write-Host '  For 24/7 with one supervisor window: .\scripts\run_full_stack_24_7.ps1 -Supervisor' -ForegroundColor DarkGray
Write-Host '  For full port cleanup first: .\scripts\run_full_stack_24_7.ps1 -CleanPorts' -ForegroundColor DarkGray
Write-Host ""