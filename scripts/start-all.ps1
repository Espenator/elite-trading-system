#Requires -Version 5.1
<#
.SYNOPSIS
    Embodier Trader — Bulletproof Master Startup Script (v2)
    Starts backend (FastAPI) + frontend (Vite) with auto-restart and port management.

.DESCRIPTION
    - Guard mode: if services already healthy, skips startup and enters health monitor
    - Kills any stale processes on ports 8000 (backend) and 3000 (frontend)
    - Starts backend Python server with auto-restart on crash
    - Starts frontend Vite dev server with auto-restart on crash
    - Health-checks backend every 15 seconds, frontend every 30 seconds
    - Writes PID file for external monitoring
    - Cleans up old log files (keeps last 7 days)
    - Runs as background task — register with Task Scheduler for auto-start

.NOTES
    Author: Embodier.ai
    PC: ProfitTrader (PC2, secondary role)
#>

$ErrorActionPreference = "Continue"
$REPO_ROOT = "C:\Users\Espen\elite-trading-system"
$BACKEND_DIR = Join-Path $REPO_ROOT "backend"
$FRONTEND_DIR = Join-Path $REPO_ROOT "frontend-v2"
$LOG_DIR = Join-Path $REPO_ROOT "logs"
$PID_FILE = Join-Path $REPO_ROOT "logs\services.pid"
$BACKEND_PORT = 8000
$FRONTEND_PORT = 5173
$BRAIN_PORT = 50051
$BRAIN_DIR = Join-Path $REPO_ROOT "brain_service"
$MAX_RESTARTS = 10
$RESTART_DELAY_SEC = 5
$HEALTH_CHECK_INTERVAL = 15
$LOG_RETENTION_DAYS = 7

# ── Ensure log directory exists ──
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backendLog = Join-Path $LOG_DIR "backend_$timestamp.log"
$frontendLog = Join-Path $LOG_DIR "frontend_$timestamp.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    try {
        Add-Content -Path (Join-Path $LOG_DIR "startup.log") -Value $line -ErrorAction SilentlyContinue
    } catch {}
}

# ── Log Cleanup (keep last N days) ──
function Clean-OldLogs {
    try {
        $cutoff = (Get-Date).AddDays(-$LOG_RETENTION_DAYS)
        Get-ChildItem -Path $LOG_DIR -Filter "*.log" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $cutoff } |
            ForEach-Object {
                Write-Log "Cleaning old log: $($_.Name)"
                Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            }
        Get-ChildItem -Path $LOG_DIR -Filter "*.err" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $cutoff } |
            ForEach-Object {
                Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            }
    } catch {}
}

# ── Port Management ──
function Free-Port {
    param([int]$Port)
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $pid = $conn.OwningProcess
            if ($pid -and $pid -ne 0) {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                Write-Log "Killing process $($proc.ProcessName) (PID $pid) on port $Port" "WARN"
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            }
        }
    } catch {
        # Port is free — good
    }
}

function Test-PortFree {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return ($null -eq $conn -or $conn.Count -eq 0)
    } catch {
        return $true
    }
}

function Test-ServiceHealthy {
    param([string]$Url, [int]$TimeoutSec = 3)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -ErrorAction SilentlyContinue
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}

# ── PID File Management ──
function Save-PidFile {
    param([int]$BackendPid, [int]$FrontendPid)
    $content = @"
# Embodier Trader — Service PIDs
# Updated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
BACKEND_PID=$BackendPid
FRONTEND_PID=$FrontendPid
MONITOR_PID=$PID
"@
    Set-Content -Path $PID_FILE -Value $content -ErrorAction SilentlyContinue
}

# ── Python Resolution ──
function Get-PythonPath {
    $venvPython = Join-Path $BACKEND_DIR "venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    # Try system python
    try {
        $null = & python --version 2>&1
        return "python"
    } catch {}
    return "python3"
}

# ── Backend Startup ──
function Start-Backend {
    param([int]$RestartCount = 0)

    if ($RestartCount -ge $MAX_RESTARTS) {
        Write-Log "Backend exceeded max restarts ($MAX_RESTARTS). Giving up." "ERROR"
        return $null
    }

    # Free port if occupied
    if (-not (Test-PortFree $BACKEND_PORT)) {
        Free-Port $BACKEND_PORT
        Start-Sleep -Seconds 2
    }

    $python = Get-PythonPath
    Write-Log "Starting backend (attempt $($RestartCount + 1)) with $python on port $BACKEND_PORT"

    try {
        $backendProc = Start-Process -FilePath $python -ArgumentList "run_server.py" `
            -WorkingDirectory $BACKEND_DIR `
            -RedirectStandardOutput $backendLog `
            -RedirectStandardError "$backendLog.err" `
            -PassThru -NoNewWindow

        Write-Log "Backend started (PID $($backendProc.Id))"

        # Wait for health check (up to 90s for cold start)
        $healthy = $false
        for ($i = 0; $i -lt 90; $i++) {
            Start-Sleep -Seconds 1
            if ($backendProc.HasExited) {
                Write-Log "Backend process exited unexpectedly during startup" "ERROR"
                break
            }
            if (Test-ServiceHealthy "http://localhost:$BACKEND_PORT/healthz") {
                $healthy = $true
                break
            }
        }

        if ($healthy) {
            Write-Log "Backend is healthy on port $BACKEND_PORT (took ${i}s)" "OK"
            return $backendProc
        } else {
            Write-Log "Backend failed health check after 90s — restarting" "ERROR"
            if (-not $backendProc.HasExited) {
                Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Seconds $RESTART_DELAY_SEC
            return Start-Backend -RestartCount ($RestartCount + 1)
        }
    } catch {
        Write-Log "Backend start failed: $_" "ERROR"
        Start-Sleep -Seconds $RESTART_DELAY_SEC
        return Start-Backend -RestartCount ($RestartCount + 1)
    }
}

# ── Frontend Startup ──
function Start-Frontend {
    param([int]$RestartCount = 0)

    if ($RestartCount -ge $MAX_RESTARTS) {
        Write-Log "Frontend exceeded max restarts ($MAX_RESTARTS). Giving up." "ERROR"
        return $null
    }

    # Free port if occupied
    if (-not (Test-PortFree $FRONTEND_PORT)) {
        Free-Port $FRONTEND_PORT
        Start-Sleep -Seconds 2
    }

    Write-Log "Starting frontend (attempt $($RestartCount + 1)) on port $FRONTEND_PORT"

    try {
        # Use npx vite for most reliable startup
        $npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
        if (-not $npmPath) {
            Write-Log "npm not found in PATH" "ERROR"
            return $null
        }

        # npm run dev is most reliable — uses project's vite config
        $frontendProc = Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c npm run dev" `
            -WorkingDirectory $FRONTEND_DIR `
            -RedirectStandardOutput $frontendLog `
            -RedirectStandardError "$frontendLog.err" `
            -PassThru -NoNewWindow

        Write-Log "Frontend started (PID $($frontendProc.Id))"

        # Wait for frontend to respond (up to 45s)
        $ready = $false
        for ($i = 0; $i -lt 45; $i++) {
            Start-Sleep -Seconds 1
            if ($frontendProc.HasExited) {
                Write-Log "Frontend process exited unexpectedly during startup" "ERROR"
                break
            }
            if (Test-ServiceHealthy "http://localhost:$FRONTEND_PORT") {
                $ready = $true
                break
            }
        }

        if ($ready) {
            Write-Log "Frontend is ready on port $FRONTEND_PORT (took ${i}s)" "OK"
            return $frontendProc
        } else {
            Write-Log "Frontend not responding after 45s — restarting" "ERROR"
            if (-not $frontendProc.HasExited) {
                Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
            }
            # Also kill any orphaned node processes on the port
            Free-Port $FRONTEND_PORT
            Start-Sleep -Seconds $RESTART_DELAY_SEC
            return Start-Frontend -RestartCount ($RestartCount + 1)
        }
    } catch {
        Write-Log "Frontend start failed: $_" "ERROR"
        Start-Sleep -Seconds $RESTART_DELAY_SEC
        return Start-Frontend -RestartCount ($RestartCount + 1)
    }
}

# ── Brain Service Startup ──
function Start-BrainService {
    # Check if already running
    $existing = Get-NetTCPConnection -LocalPort $BRAIN_PORT -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Log "Brain Service already running on port $BRAIN_PORT (PID: $($existing.OwningProcess))" "OK"
        return (Get-Process -Id $existing.OwningProcess -ErrorAction SilentlyContinue)
    }

    $python = Get-PythonPath
    $brainLog = Join-Path $LOG_DIR "brain_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"

    Write-Log "Starting Brain Service (gRPC on port $BRAIN_PORT)..."
    try {
        $brainProc = Start-Process -FilePath $python -ArgumentList "server.py" `
            -WorkingDirectory $BRAIN_DIR `
            -RedirectStandardOutput $brainLog `
            -RedirectStandardError "$brainLog.err" `
            -PassThru -NoNewWindow

        for ($i = 0; $i -lt 15; $i++) {
            Start-Sleep -Seconds 1
            $check = Get-NetTCPConnection -LocalPort $BRAIN_PORT -State Listen -ErrorAction SilentlyContinue
            if ($check) {
                Write-Log "Brain Service READY on port $BRAIN_PORT (took ${i}s)" "OK"
                return $brainProc
            }
        }
        Write-Log "Brain Service failed to start within 15s" "WARN"
        return $null
    } catch {
        Write-Log "Brain Service start failed: $_" "WARN"
        return $null
    }
}

# ── Health Monitor (infinite loop) ──
function Start-HealthMonitor {
    param($BackendProc, $FrontendProc)

    Write-Log "Health monitor ACTIVE — checking every ${HEALTH_CHECK_INTERVAL}s"
    $backendRestarts = 0
    $frontendRestarts = 0
    $consecutiveBackendFails = 0
    $consecutiveFrontendFails = 0

    while ($true) {
        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL

        # ── Check Backend ──
        $backendAlive = Test-ServiceHealthy "http://localhost:$BACKEND_PORT/healthz" 5
        if ($backendAlive) {
            $consecutiveBackendFails = 0
        } else {
            $consecutiveBackendFails++
            # Only restart after 2 consecutive failures (avoid false positives)
            if ($consecutiveBackendFails -ge 2) {
                $backendRestarts++
                Write-Log "Backend health check FAILED x${consecutiveBackendFails} — restarting (#$backendRestarts)" "WARN"
                if ($BackendProc -and -not $BackendProc.HasExited) {
                    Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
                }
                Free-Port $BACKEND_PORT
                Start-Sleep -Seconds 2
                $BackendProc = Start-Backend -RestartCount 0
                $consecutiveBackendFails = 0
                if ($BackendProc) {
                    Save-PidFile -BackendPid $BackendProc.Id -FrontendPid ($FrontendProc.Id)
                }
            } else {
                Write-Log "Backend health check failed (attempt $consecutiveBackendFails/2 before restart)" "WARN"
            }
        }

        # ── Check Frontend ──
        $frontendAlive = Test-ServiceHealthy "http://localhost:$FRONTEND_PORT" 5
        if ($frontendAlive) {
            $consecutiveFrontendFails = 0
        } else {
            $consecutiveFrontendFails++
            if ($consecutiveFrontendFails -ge 2) {
                $frontendRestarts++
                Write-Log "Frontend health check FAILED x${consecutiveFrontendFails} — restarting (#$frontendRestarts)" "WARN"
                if ($FrontendProc -and -not $FrontendProc.HasExited) {
                    Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue
                }
                Free-Port $FRONTEND_PORT
                Start-Sleep -Seconds 2
                $FrontendProc = Start-Frontend -RestartCount 0
                $consecutiveFrontendFails = 0
                if ($FrontendProc) {
                    Save-PidFile -BackendPid ($BackendProc.Id) -FrontendPid $FrontendProc.Id
                }
            } else {
                Write-Log "Frontend health check failed (attempt $consecutiveFrontendFails/2 before restart)" "WARN"
            }
        }
    }
}

# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
Write-Log "═══════════════════════════════════════════════════"
Write-Log "  Embodier Trader — Master Startup v2"
Write-Log "  PC: ProfitTrader (secondary)"
Write-Log "  Backend port: $BACKEND_PORT | Frontend port: $FRONTEND_PORT"
Write-Log "═══════════════════════════════════════════════════"

# Clean old logs
Clean-OldLogs

# ── Guard Mode: check if services already running ──
$backendHealthy = Test-ServiceHealthy "http://localhost:$BACKEND_PORT/healthz"
$frontendHealthy = Test-ServiceHealthy "http://localhost:$FRONTEND_PORT"

if ($backendHealthy -and $frontendHealthy) {
    Write-Log "Both services already running and healthy — entering health monitor only" "OK"
    # Get existing process references for the health monitor
    $backendPid = (Get-NetTCPConnection -LocalPort $BACKEND_PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
    $frontendPid = (Get-NetTCPConnection -LocalPort $FRONTEND_PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
    $BackendProc = if ($backendPid) { Get-Process -Id $backendPid -ErrorAction SilentlyContinue } else { $null }
    $FrontendProc = if ($frontendPid) { Get-Process -Id $frontendPid -ErrorAction SilentlyContinue } else { $null }
    Save-PidFile -BackendPid ($BackendProc.Id) -FrontendPid ($FrontendProc.Id)
    # Ensure Brain Service is also running
    $brainProc = Start-BrainService
    Start-HealthMonitor -BackendProc $BackendProc -FrontendProc $FrontendProc
    exit 0
}

# ── Start services that aren't running ──
if ($backendHealthy) {
    Write-Log "Backend already healthy — skipping startup" "OK"
    $backendPid = (Get-NetTCPConnection -LocalPort $BACKEND_PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
    $backendProc = if ($backendPid) { Get-Process -Id $backendPid -ErrorAction SilentlyContinue } else { $null }
} else {
    $backendProc = Start-Backend
}

if ($frontendHealthy) {
    Write-Log "Frontend already healthy — skipping startup" "OK"
    $frontendPid = (Get-NetTCPConnection -LocalPort $FRONTEND_PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
    $frontendProc = if ($frontendPid) { Get-Process -Id $frontendPid -ErrorAction SilentlyContinue } else { $null }
} else {
    $frontendProc = Start-Frontend
}

# Verify both are up
$backendOk = Test-ServiceHealthy "http://localhost:$BACKEND_PORT/healthz"
$frontendOk = Test-ServiceHealthy "http://localhost:$FRONTEND_PORT"

if ($backendOk -and $frontendOk) {
    Write-Log "All services started successfully!" "OK"
    Write-Log "Backend:  http://localhost:$BACKEND_PORT"
    Write-Log "Frontend: http://localhost:$FRONTEND_PORT"
    Save-PidFile -BackendPid ($backendProc.Id) -FrontendPid ($frontendProc.Id)
    # Start Brain Service (non-blocking, won't prevent health monitor if it fails)
    $brainProc = Start-BrainService
    # Enter health monitor loop (infinite)
    Start-HealthMonitor -BackendProc $backendProc -FrontendProc $frontendProc
} elseif ($backendOk) {
    Write-Log "Backend OK but frontend failed — entering health monitor anyway" "WARN"
    Save-PidFile -BackendPid ($backendProc.Id) -FrontendPid 0
    Start-HealthMonitor -BackendProc $backendProc -FrontendProc $null
} elseif ($frontendOk) {
    Write-Log "Frontend OK but backend failed — entering health monitor anyway" "WARN"
    Save-PidFile -BackendPid 0 -FrontendPid ($frontendProc.Id)
    Start-HealthMonitor -BackendProc $null -FrontendProc $frontendProc
} else {
    Write-Log "Both services failed to start — will retry in health monitor" "ERROR"
    Start-HealthMonitor -BackendProc $null -FrontendProc $null
}
