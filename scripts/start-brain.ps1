<#
.SYNOPSIS
    Start the Brain Service (gRPC on port 50051) for PC2.
#>
$REPO = "C:\Users\Espen\elite-trading-system"
$BRAIN_DIR = Join-Path $REPO "brain_service"
$LOGS_DIR = Join-Path $REPO "logs"

# Create logs dir if missing
if (-not (Test-Path $LOGS_DIR)) { New-Item -ItemType Directory -Path $LOGS_DIR -Force | Out-Null }

# Check if already running
$existing = Get-NetTCPConnection -LocalPort 50051 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  [OK] Brain Service already running on port 50051 (PID: $($existing.OwningProcess))"
    exit 0
}

# Find Python
$py = Join-Path $REPO "backend\venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$ts = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$proc = Start-Process -FilePath $py -ArgumentList "server.py" `
    -WorkingDirectory $BRAIN_DIR `
    -RedirectStandardOutput (Join-Path $LOGS_DIR "brain_$ts.log") `
    -RedirectStandardError (Join-Path $LOGS_DIR "brain_$ts.err") `
    -NoNewWindow -PassThru

Write-Host "  [..] Brain Service starting (PID: $($proc.Id))..."

# Wait up to 15s for port
for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    $check = Get-NetTCPConnection -LocalPort 50051 -State Listen -ErrorAction SilentlyContinue
    if ($check) {
        Write-Host "  [OK] Brain Service READY on port 50051 (took ${i}s)"
        exit 0
    }
}

Write-Host "  [FAIL] Brain Service did not start. Check logs\brain_$ts.err"
exit 1
