# run_backend_autorestart.ps1 - Run backend with auto-restart on failure or hang (24/7)
# Usage: from repo root: .\backend\scripts\run_backend_autorestart.ps1 -Port 8000
# Or from backend: .\scripts\run_backend_autorestart.ps1
#
# Keeps API + WebSocket (/ws) up 24/7:
# - Restarts when uvicorn process exits (crash).
# - Watchdog: pings GET /api/v1/health every HealthCheckIntervalSeconds;
#   if UnhealthyCountMax consecutive failures, kills the process and restarts (handles hang).
# - StartupGraceSeconds: no failure count during initial startup (avoids false restarts).
# - Circuit breaker: stops restarting after MaxCrashesInWindow crashes in CrashWindowMinutes.
# Press Ctrl+C once to stop.

param(
    [int]$Port = 8000,
    [int]$RestartDelaySeconds = 3,
    [int]$HealthCheckIntervalSeconds = 30,
    [int]$UnhealthyCountMax = 3,
    [int]$StartupGraceSeconds = 120,
    [int]$MaxCrashesInWindow = 5,
    [int]$CrashWindowMinutes = 10,
    [switch]$ShowBackendWindow  # If set, uvicorn opens in visible console (for debugging). Default: hidden to avoid new window every restart.
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$BackendDir = $PSScriptRoot | Split-Path -Parent
if (-not (Test-Path (Join-Path $BackendDir "app\main.py"))) {
    $BackendDir = (Get-Location).Path
}
$PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Set-Location $BackendDir
$runCount = 0
# Use /healthz (lightweight liveness probe, <50ms) — avoids false restarts when
# the heavy /health endpoint times out due to busy event loop (scouts, streams, etc.)
$HealthUrl = "http://127.0.0.1:${Port}/healthz"
$HealthUrlFallback = "http://127.0.0.1:${Port}/readyz"

# Circuit breaker: track crash timestamps
$crashTimes = [System.Collections.ArrayList]@()

Write-Host ""
Write-Host "  Backend auto-restart (port $Port). Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "  Startup grace: ${StartupGraceSeconds}s | Health check every ${HealthCheckIntervalSeconds}s (max $UnhealthyCountMax failures)" -ForegroundColor Gray
Write-Host "  Circuit breaker: max $MaxCrashesInWindow crashes in ${CrashWindowMinutes}min" -ForegroundColor Gray
Write-Host ""

function Test-BackendHealth {
    # Try /api/v1/health first (reliable JSON endpoint)
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { return $true }
    } catch { }
    # Fallback to /health
    try {
        $r = Invoke-WebRequest -Uri $HealthUrlFallback -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Test-PortInUse {
    param([int]$P)
    try {
        $conn = Get-NetTCPConnection -LocalPort $P -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $conn -and $conn.Count -gt 0)
    } catch {
        return $false
    }
}

function Test-CircuitBreaker {
    # Remove crashes outside the window
    $windowStart = (Get-Date).AddMinutes(-$CrashWindowMinutes)
    $toRemove = @()
    for ($i = 0; $i -lt $crashTimes.Count; $i++) {
        if ($crashTimes[$i] -lt $windowStart) { $toRemove += $i }
    }
    for ($i = $toRemove.Count - 1; $i -ge 0; $i--) {
        $crashTimes.RemoveAt($toRemove[$i])
    }
    return $crashTimes.Count -ge $MaxCrashesInWindow
}

while ($true) {
    # Circuit breaker check
    if (Test-CircuitBreaker) {
        Write-Host ""
        Write-Host "  CIRCUIT BREAKER OPEN: Backend crashed $($crashTimes.Count) times in ${CrashWindowMinutes} minutes." -ForegroundColor Red
        Write-Host "  Stopping auto-restart. Check logs and fix the root cause." -ForegroundColor Red
        Write-Host "  To resume: restart this script or run .\scripts\run_full_stack_24_7.ps1" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }

    # Prevent second backend: if port already in use, another instance is running (DuckDB single-writer). Wait instead of starting a duplicate.
    if (Test-PortInUse -P $Port) {
        Write-Host "  [$(Get-Date -Format 'HH:mm:ss')] Port $Port in use (backend already running). Waiting 60s to avoid duplicate..." -ForegroundColor DarkYellow
        Start-Sleep -Seconds 60
        continue
    }

    # Clean stale PID file before starting
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

    $runCount++
    Write-Host "  [Run #$runCount] Starting uvicorn on port $Port..." -ForegroundColor Yellow
    $proc = $null
    try {
        $env:PORT = $Port.ToString()
        $procParams = @{
            FilePath     = $PythonExe
            ArgumentList = "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", $Port.ToString()
            WorkingDirectory = $BackendDir
            PassThru     = $true
        }
        if (-not $ShowBackendWindow) {
            $procParams["WindowStyle"] = "Hidden"
        }
        $proc = Start-Process @procParams
    } catch {
        Write-Host "  Process start error: $_" -ForegroundColor Red
        [void]$crashTimes.Add((Get-Date))
        Start-Sleep -Seconds $RestartDelaySeconds
        continue
    }

    $unhealthyCount = 0
    $exited = $false
    $processStartTime = Get-Date
    while (-not $exited) {
        # Wait one interval; then check if process exited or health failed
        for ($i = 0; $i -lt $HealthCheckIntervalSeconds; $i++) {
            Start-Sleep -Seconds 1
            if ($proc.HasExited) {
                $exited = $true
                break
            }
        }
        if ($exited) { break }

        $elapsed = ((Get-Date) - $processStartTime).TotalSeconds
        $inGrace = $elapsed -lt $StartupGraceSeconds
        if (Test-BackendHealth) {
            $unhealthyCount = 0
        } else {
            if (-not $inGrace) {
                $unhealthyCount++
                Write-Host "  Health check failed ($unhealthyCount/$UnhealthyCountMax) [elapsed: $([math]::Round($elapsed))s]" -ForegroundColor DarkYellow
                if ($unhealthyCount -ge $UnhealthyCountMax) {
                    Write-Host "  API unhealthy (no response after $UnhealthyCountMax checks). Killing backend and restarting..." -ForegroundColor Magenta
                    try { $proc.Kill() } catch { }
                    $exited = $true
                    [void]$crashTimes.Add((Get-Date))
                    break
                }
            } else {
                Write-Host "  Health check pending (startup grace: $([math]::Round($StartupGraceSeconds - $elapsed))s remaining)" -ForegroundColor DarkGray
            }
        }
    }

    if ($null -ne $proc -and $proc.HasExited) {
        $code = $proc.ExitCode
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        if ($code -eq 2) {
            Write-Host "  [$ts] Duplicate instance (DuckDB in use). Another backend is already running." -ForegroundColor DarkYellow
            Write-Host "  This window will close. Use the other backend, or run: .\scripts\stop_embodier.ps1 then start again." -ForegroundColor Gray
            Start-Sleep -Seconds 3
            exit 0
        }
        if ($code -eq 3) {
            Write-Host "  [$ts] Process lock: another healthy backend is running. Exiting." -ForegroundColor DarkYellow
            Start-Sleep -Seconds 3
            exit 0
        }
        [void]$crashTimes.Add((Get-Date))
        Write-Host "  [$ts] Backend exited (code $code, crashes in window: $($crashTimes.Count)/$MaxCrashesInWindow). Restarting in ${RestartDelaySeconds}s..." -ForegroundColor Magenta
        # Write to ops log
        $logDir = Join-Path ($BackendDir | Split-Path -Parent) "logs"
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        Add-Content -Path (Join-Path $logDir "backend_autorestart.log") -Value "[$ts] Run #$runCount exit_code=$code port=$Port crashes_in_window=$($crashTimes.Count)" -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds $RestartDelaySeconds
}
