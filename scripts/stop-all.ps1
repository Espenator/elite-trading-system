#Requires -Version 5.1
<#
.SYNOPSIS
    Stop all Embodier Trader services (backend + frontend).
#>

$BACKEND_PORT = 8000
$FRONTEND_PORT = 5173

function Stop-PortProcess {
    param([int]$Port, [string]$Name)
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $pid = $conn.OwningProcess
            if ($pid -and $pid -ne 0) {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                Write-Host "[STOP] Killing $Name — $($proc.ProcessName) (PID $pid) on port $Port"
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Host "[OK] No process on port $Port"
    }
}

Write-Host ""
Write-Host "  Embodier Trader — Stopping All Services"
Write-Host "  ========================================"
Write-Host ""

Stop-PortProcess -Port $BACKEND_PORT -Name "Backend"
Stop-PortProcess -Port $FRONTEND_PORT -Name "Frontend"

# Also kill any running health monitors
Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*start-all*" -or $_.CommandLine -like "*start-all*"
} | ForEach-Object {
    Write-Host "[STOP] Killing health monitor (PID $($_.Id))"
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[OK] All services stopped."
Write-Host ""
