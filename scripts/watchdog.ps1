# Embodier Trader — Simple Watchdog
# Checks backend + frontend every 20s, restarts if dead
$ErrorActionPreference = "Continue"
$REPO = "C:\Users\Espen\elite-trading-system"
$LOG = Join-Path $REPO "logs\watchdog.log"

function Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LOG -Value $line -ErrorAction SilentlyContinue
}

function IsUp($url) {
    try {
        $c = New-Object System.Net.WebClient
        $null = $c.DownloadString($url)
        return $true
    } catch { return $false }
}

function RestartBackend {
    Log "Restarting backend..."
    # Kill port
    Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    $py = Join-Path $REPO "backend\venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }
    $ts = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    Start-Process -FilePath $py -ArgumentList "run_server.py" `
        -WorkingDirectory (Join-Path $REPO "backend") `
        -RedirectStandardOutput (Join-Path $REPO "logs\backend_$ts.log") `
        -RedirectStandardError (Join-Path $REPO "logs\backend_${ts}.err") `
        -NoNewWindow
    # Wait for health
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        if (IsUp "http://localhost:8001/healthz") { Log "Backend recovered!"; return }
    }
    Log "Backend failed to recover"
}

function RestartFrontend {
    Log "Restarting frontend..."
    Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    $ts = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" `
        -WorkingDirectory (Join-Path $REPO "frontend-v2") `
        -RedirectStandardOutput (Join-Path $REPO "logs\frontend_$ts.log") `
        -RedirectStandardError (Join-Path $REPO "logs\frontend_${ts}.err") `
        -NoNewWindow
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (IsUp "http://localhost:3000") { Log "Frontend recovered!"; return }
    }
    Log "Frontend failed to recover"
}

Log "Watchdog started (PID $PID)"
$backendFails = 0
$frontendFails = 0

while ($true) {
    Start-Sleep -Seconds 20

    if (-not (IsUp "http://localhost:8001/healthz")) {
        $backendFails++
        if ($backendFails -ge 2) { RestartBackend; $backendFails = 0 }
        else { Log "Backend check failed ($backendFails/2)" }
    } else { $backendFails = 0 }

    if (-not (IsUp "http://localhost:3000")) {
        $frontendFails++
        if ($frontendFails -ge 2) { RestartFrontend; $frontendFails = 0 }
        else { Log "Frontend check failed ($frontendFails/2)" }
    } else { $frontendFails = 0 }
}
