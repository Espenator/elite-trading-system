<#
.SYNOPSIS
    Start the health monitor as a background job.
    This watches backend (8001) and frontend (3000), restarting if they crash.
#>
$REPO = "C:\Users\Espen\elite-trading-system"
$SCRIPT = Join-Path $REPO "scripts\start-all.ps1"

# Check if monitor already running
$existing = Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object {
    try {
        $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmdline -like "*start-all.ps1*"
    } catch { $false }
}

if ($existing) {
    Write-Host "  [OK] Health monitor already running (PID: $($existing.Id))"
    exit 0
}

# Launch hidden PowerShell running start-all.ps1
$proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$SCRIPT`"" `
    -WindowStyle Hidden `
    -PassThru

Write-Host "  [OK] Health monitor started (PID: $($proc.Id))"
Write-Host "       Watching backend:8001 + frontend:3000"
Write-Host "       Auto-restarts on crash, checks every 15s"
