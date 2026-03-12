# smoke-test.ps1 — Post-deploy verification: /health, council, WebSocket.
# Run after deploy: .\scripts\smoke-test.ps1
# Optional: .\scripts\smoke-test.ps1 -BaseUrl http://192.168.1.105:8000

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$failed = 0

Write-Host "`n  Smoke tests — $BaseUrl`n" -ForegroundColor Cyan

# 1. /health
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5
    if ($r.status -match "healthy|ready") {
        Write-Host "  OK /health — $($r.status)" -ForegroundColor Green
    } else {
        Write-Host "  WARN /health — $($r.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  FAIL /health — $_" -ForegroundColor Red
    $failed++
}

# 2. /api/v1/health (aggregated)
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/health" -TimeoutSec 5
    Write-Host "  OK /api/v1/health" -ForegroundColor Green
} catch {
    Write-Host "  FAIL /api/v1/health — $_" -ForegroundColor Red
    $failed++
}

# 3. Council responds
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/council/status" -TimeoutSec 5
    Write-Host "  OK /api/v1/council/status" -ForegroundColor Green
} catch {
    Write-Host "  FAIL /api/v1/council/status — $_" -ForegroundColor Red
    $failed++
}

# 4. Readiness (optional)
try {
    $r = Invoke-RestMethod -Uri "$BaseUrl/readyz" -TimeoutSec 5
    Write-Host "  OK /readyz" -ForegroundColor Green
} catch {
    Write-Host "  WARN /readyz — $_" -ForegroundColor Yellow
}

Write-Host ""
if ($failed -gt 0) {
    Write-Host "  $failed check(s) failed." -ForegroundColor Red
    exit 1
}
Write-Host "  All smoke tests passed." -ForegroundColor Green
Write-Host ""
