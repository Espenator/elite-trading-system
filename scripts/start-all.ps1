#Requires -Version 5.1
<#
.SYNOPSIS
    Embodier Trader — Bulletproof Master Startup Script
    Starts backend (FastAPI) + frontend (Vite) with auto-restart and port management.

.DESCRIPTION
    - Kills any stale processes on ports 8001 (backend) and 3000 (frontend)
    - Starts backend Python server with auto-restart on crash
    - Starts frontend Vite dev server with auto-restart on crash
    - Health-checks backend every 15 seconds
    - Runs as background jobs — survives terminal close
    - Can be registered with Task Scheduler for auto-start on login

.NOTES
    Author: Embodier.ai
    PC: ProfitTrader (PC2, secondary role)
#>

$ErrorActionPreference = "Continue"
$REPO_ROOT = "C:\Users\Espen\elite-trading-system"
$BACKEND_DIR = Join-Path $REPO_ROOT "backend"
$FRONTEND_DIR = Join-Path $REPO_ROOT "frontend-v2"
$LOG_DIR = Join-Path $REPO_ROOT "logs"
$BACKEND_PORT = 8001
$FRONTEND_PORT = 3000
$MAX_RESTARTS = 10
$RESTART_DELAY_SEC = 5

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
    Add-Content -Path (Join-Path $LOG_DIR "startup.log") -Value $line
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
        return
    }

    # Free port
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

        # Wait for health check
        $healthy = $false
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/healthz" -TimeoutSec 3 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    $healthy = $true
                    break
                }
            } catch {}
        }

        if ($healthy) {
            Write-Log "Backend is healthy and ready on port $BACKEND_PORT" "OK"
            return $backendProc
        } else {
            Write-Log "Backend failed health check after 60s — restarting" "ERROR"
            Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
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
        return
    }

    # Free port
    if (-not (Test-PortFree $FRONTEND_PORT)) {
        Free-Port $FRONTEND_PORT
        Start-Sleep -Seconds 2
    }

    Write-Log "Starting frontend (attempt $($RestartCount + 1)) on port $FRONTEND_PORT"

    try {
        $npmCmd = "node"
        $viteBin = Join-Path $FRONTEND_DIR "node_modules\vite\bin\vite.js"

        if (-not (Test-Path $viteBin)) {
            Write-Log "Vite not found — running npm install first"
            Start-Process -FilePath "npm" -ArgumentList "install" `
                -WorkingDirectory $FRONTEND_DIR -Wait -NoNewWindow
        }

        $frontendProc = Start-Process -FilePath $npmCmd -ArgumentList "$viteBin --host 0.0.0.0 --port $FRONTEND_PORT" `
            -WorkingDirectory $FRONTEND_DIR `
            -RedirectStandardOutput $frontendLog `
            -RedirectStandardError "$frontendLog.err" `
            -PassThru -NoNewWindow

        Write-Log "Frontend started (PID $($frontendProc.Id))"

        # Wait for frontend to respond
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$FRONTEND_PORT" -TimeoutSec 3 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    $ready = $true
                    break
                }
            } catch {}
        }

        if ($ready) {
            Write-Log "Frontend is ready on port $FRONTEND_PORT" "OK"
            return $frontendProc
        } else {
            Write-Log "Frontend not responding after 30s — restarting" "ERROR"
            Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds $RESTART_DELAY_SEC
            return Start-Frontend -RestartCount ($RestartCount + 1)
        }
    } catch {
        Write-Log "Frontend start failed: $_" "ERROR"
        Start-Sleep -Seconds $RESTART_DELAY_SEC
        return Start-Frontend -RestartCount ($RestartCount + 1)
    }
}

# ── Health Monitor ──
function Start-HealthMonitor {
    param($BackendProc, $FrontendProc)

    Write-Log "Starting health monitor (every 15s)"
    $backendRestarts = 0
    $frontendRestarts = 0

    while ($true) {
        Start-Sleep -Seconds 15

        # Check backend
        $backendAlive = $false
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/healthz" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { $backendAlive = $true }
        } catch {}

        if (-not $backendAlive) {
            $backendRestarts++
            Write-Log "Backend health check FAILED — restarting (#$backendRestarts)" "WARN"
            if ($BackendProc -and -not $BackendProc.HasExited) {
                Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
            }
            $BackendProc = Start-Backend -RestartCount 0
        }

        # Check frontend
        $frontendAlive = $false
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$FRONTEND_PORT" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { $frontendAlive = $true }
        } catch {}

        if (-not $frontendAlive) {
            $frontendRestarts++
            Write-Log "Frontend health check FAILED — restarting (#$frontendRestarts)" "WARN"
            if ($FrontendProc -and -not $FrontendProc.HasExited) {
                Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue
            }
            $FrontendProc = Start-Frontend -RestartCount 0
        }
    }
}

# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
Write-Log "═══════════════════════════════════════════════════"
Write-Log "  Embodier Trader — Master Startup"
Write-Log "  PC: ProfitTrader (secondary)"
Write-Log "  Backend port: $BACKEND_PORT | Frontend port: $FRONTEND_PORT"
Write-Log "═══════════════════════════════════════════════════"

# Start services
$backendProc = Start-Backend
$frontendProc = Start-Frontend

if ($backendProc -and $frontendProc) {
    Write-Log "All services started successfully!" "OK"
    Write-Log "Backend:  http://localhost:$BACKEND_PORT"
    Write-Log "Frontend: http://localhost:$FRONTEND_PORT"

    # Enter health monitor loop
    Start-HealthMonitor -BackendProc $backendProc -FrontendProc $frontendProc
} else {
    Write-Log "Failed to start all services" "ERROR"
    exit 1
}
