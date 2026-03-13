Set-Location "C:\Users\Espen\elite-trading-system\frontend-v2"
Write-Host "Starting Vite dev server..."
$proc = Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory "C:\Users\Espen\elite-trading-system\frontend-v2" -PassThru -NoNewWindow
Write-Host "Frontend started (PID: $($proc.Id))"
# Wait for it to be ready
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "Frontend READY on http://localhost:3000"
            exit 0
        }
    } catch {}
}
Write-Host "Frontend started but may still be loading..."
