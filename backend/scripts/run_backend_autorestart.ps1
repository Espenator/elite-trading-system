# run_backend_autorestart.ps1 - Run backend with auto-restart on failure or hang
# Usage: from repo root: .\backend\scripts\run_backend_autorestart.ps1 -Port 8000
# Or from backend: .\scripts\run_backend_autorestart.ps1
#
# - Restarts when uvicorn process exits (crash).
# - Watchdog: pings GET /health every HealthCheckIntervalSeconds;
#   if UnhealthyCountMax consecutive failures, kills the process and restarts (handles hang).
# - StartupGraceSeconds: no failure count during initial startup (avoids false restarts).
# Press Ctrl+C once to stop.

param(
    [int]$Port = 8000,
    [int]$RestartDelaySeconds = 3,
    [int]$HealthCheckIntervalSeconds = 30,
    [int]$UnhealthyCountMax = 3,
    [int]$StartupGraceSeconds = 45
)

$ErrorActionPreference = "Stop"
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
$HealthUrl = "http://127.0.0.1:${Port}/health"

Write-Host ""
Write-Host "  Backend auto-restart (port $Port). Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "  Restart delay: ${RestartDelaySeconds}s | Health check every ${HealthCheckIntervalSeconds}s (max $UnhealthyCountMax failures)" -ForegroundColor Gray
Write-Host ""

function Test-BackendHealth {
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

while ($true) {
    $runCount++
    Write-Host "  [Run #$runCount] Starting uvicorn..." -ForegroundColor Yellow
    $proc = $null
    try {
        $proc = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", $Port.ToString() -WorkingDirectory $BackendDir -PassThru
    } catch {
        Write-Host "  Process start error: $_" -ForegroundColor Red
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
                Write-Host "  Health check failed ($unhealthyCount/$UnhealthyCountMax)" -ForegroundColor DarkYellow
                if ($unhealthyCount -ge $UnhealthyCountMax) {
                    Write-Host "  API unhealthy (no response). Killing backend and restarting..." -ForegroundColor Magenta
                    try { $proc.Kill() } catch { }
                    $exited = $true
                    break
                }
            }
        }
    }

    if ($null -ne $proc -and $proc.HasExited) {
        $code = $proc.ExitCode
        Write-Host "  Backend exited (code $code). Restarting in ${RestartDelaySeconds}s..." -ForegroundColor Magenta
    }
    Start-Sleep -Seconds $RestartDelaySeconds
}
