param([int]$Port = 3000)
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        Write-Host "Killing PID: $($c.OwningProcess)"
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}
$check = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($check) { Write-Host "STILL OCCUPIED" } else { Write-Host "PORT $Port FREE" }
