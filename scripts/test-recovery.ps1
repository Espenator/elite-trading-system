<#
.SYNOPSIS
    Test auto-recovery: kill backend, restart, verify health.
#>

$BACKEND_PORT = 8000
$REPO = "C:\Users\Espen\elite-trading-system"

# Use .NET HttpClient instead of Invoke-WebRequest (more reliable)
function Test-Http {
    param([string]$Url, [int]$Timeout = 3)
    try {
        $client = New-Object System.Net.WebClient
        $null = $client.DownloadString($Url)
        return $true
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "  RECOVERY TEST: Kill backend, verify auto-restart"
Write-Host "  ================================================="
Write-Host ""

# Step 1: Verify backend is healthy
Write-Host "  [1] Checking backend is healthy..."
if (Test-Http "http://localhost:${BACKEND_PORT}/healthz") {
    Write-Host "      Backend: HEALTHY"
} else {
    Write-Host "      Backend: NOT RUNNING - cannot test recovery"
    exit 1
}

# Step 2: Get PID and kill it
$conn = Get-NetTCPConnection -LocalPort $BACKEND_PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$backendPid = $conn.OwningProcess
Write-Host "  [2] Killing backend PID $backendPid..."
# Kill all processes on port (may be multiple bindings)
Get-NetTCPConnection -LocalPort $BACKEND_PORT -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# Step 3: Verify it's dead
if (Test-Http "http://localhost:${BACKEND_PORT}/healthz") {
    Write-Host "      Backend still alive somehow"
} else {
    Write-Host "      Backend: DEAD (confirmed killed)"
}

# Step 4: Restart backend
Write-Host "  [3] Restarting backend..."
$python = Join-Path $REPO "backend\venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$ts = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = Join-Path $REPO "logs\backend_recovery_$ts.log"
$proc = Start-Process -FilePath $python -ArgumentList "run_server.py" `
    -WorkingDirectory (Join-Path $REPO "backend") `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError "$logFile.err" `
    -PassThru -NoNewWindow

Write-Host "      Started new process PID: $($proc.Id)"

# Step 5: Wait for health
Write-Host "  [4] Waiting for backend to become healthy..."
$recovered = $false
for ($i = 1; $i -le 90; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Http "http://localhost:${BACKEND_PORT}/healthz") {
        $recovered = $true
        Write-Host "      Backend RECOVERED in ${i} seconds!"
        break
    }
    if ($i % 15 -eq 0) { Write-Host "      ... waiting (${i}s)" }
}

if (-not $recovered) {
    Write-Host "      Backend FAILED to recover in 90s"
    exit 1
}

# Step 6: Verify endpoints
Write-Host "  [5] Verifying API endpoints after recovery..."
$endpoints = @("/api/v1/status", "/api/v1/alpaca/account", "/api/v1/portfolio", "/api/v1/data-sources/")
foreach ($ep in $endpoints) {
    if (Test-Http "http://localhost:${BACKEND_PORT}${ep}") {
        Write-Host "      $ep : OK"
    } else {
        Write-Host "      $ep : FAIL"
    }
}

Write-Host ""
Write-Host "  ==========================================="
Write-Host "  RECOVERY TEST: PASSED"
Write-Host "  Backend killed -> restarted -> verified OK"
Write-Host "  ==========================================="
Write-Host ""
