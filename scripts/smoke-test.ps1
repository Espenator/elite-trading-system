# Smoke test: hit /health, /api/v1/health, council and optional WebSocket.
# Usage: .\scripts\smoke-test.ps1 [-BaseUrl http://localhost:8000]
# Run after deploy to verify backend is up.

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$failed = 0

function Test-Endpoint {
    param([string]$Path, [string]$Name)
    try {
        $r = Invoke-WebRequest -Uri ($BaseUrl + $Path) -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) {
            Write-Host "  OK $Name -> $($r.StatusCode)" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "  FAIL $Name -> $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    Write-Host "  FAIL $Name -> $($r.StatusCode)" -ForegroundColor Red
    return $false
}

Write-Host ""
Write-Host "  === Smoke test: $BaseUrl ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Endpoint -Path "/healthz" -Name "GET /healthz")) { $script:failed++ }
if (-not (Test-Endpoint -Path "/health" -Name "GET /health")) { $script:failed++ }
if (-not (Test-Endpoint -Path "/api/v1/health" -Name "GET /api/v1/health")) { $script:failed++ }
if (-not (Test-Endpoint -Path "/api/v1/council/latest" -Name "GET /api/v1/council/latest")) { $script:failed++ }
if (-not (Test-Endpoint -Path "/api/v1/status/data" -Name "GET /api/v1/status/data")) { $script:failed++ }

Write-Host ""
if ($failed -eq 0) {
    Write-Host "  All smoke checks passed." -ForegroundColor Green
    Write-Host "  WebSocket: connect to ws://localhost:8000/ws/cns (token in .env API_AUTH_TOKEN)." -ForegroundColor Gray
} else {
    Write-Host "  $failed check(s) failed." -ForegroundColor Red
    exit 1
}
Write-Host ""
