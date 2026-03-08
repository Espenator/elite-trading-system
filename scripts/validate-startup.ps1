# Embodier Trader — Startup Validation Script
# Validates that all services are running correctly
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$BrainPort = 50051,
    [switch]$SkipBrain,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "SilentlyContinue"

function Test-Endpoint($Url, $Name) {
    try {
        $response = Invoke-RestMethod $Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✅ $Name" -ForegroundColor Green -NoNewline
        Write-Host " — $Url" -ForegroundColor DarkGray
        return $true
    } catch {
        Write-Host "  ❌ $Name" -ForegroundColor Red -NoNewline
        Write-Host " — $($_.Exception.Message)" -ForegroundColor DarkRed
        return $false
    }
}

function Test-Port($Port, $Name) {
    $tcp = New-Object Net.Sockets.TcpClient
    try {
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        Write-Host "  ✅ $Name" -ForegroundColor Green -NoNewline
        Write-Host " — Port $Port is open" -ForegroundColor DarkGray
        return $true
    } catch {
        Write-Host "  ❌ $Name" -ForegroundColor Red -NoNewline
        Write-Host " — Port $Port is NOT open" -ForegroundColor DarkRed
        return $false
    } finally {
        try { $tcp.Close() } catch { }
    }
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   EMBODIER TRADER — Startup Validation" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

$checks = @()

# ── Backend Core ─────────────────────────────────────────
Write-Host "  Backend (Core Services):" -ForegroundColor Yellow
$checks += Test-Endpoint "http://localhost:$BackendPort/health" "Health endpoint"
$checks += Test-Endpoint "http://localhost:$BackendPort/api/v1/status" "Status API"

# ── Backend Services ─────────────────────────────────────
Write-Host ""
Write-Host "  Backend (Intelligence):" -ForegroundColor Yellow

# Council status
try {
    $council = Invoke-RestMethod "http://localhost:$BackendPort/api/v1/council/status" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    $agentCount = $council.agents.Count
    if ($agentCount -ge 31) {
        Write-Host "  ✅ Council" -ForegroundColor Green -NoNewline
        Write-Host " — $agentCount agents loaded" -ForegroundColor DarkGray
        $checks += $true
    } elseif ($agentCount -gt 0) {
        Write-Host "  ⚠️  Council" -ForegroundColor Yellow -NoNewline
        Write-Host " — Only $agentCount/31 agents loaded" -ForegroundColor DarkYellow
        $checks += $true
    } else {
        Write-Host "  ❌ Council" -ForegroundColor Red -NoNewline
        Write-Host " — No agents loaded" -ForegroundColor DarkRed
        $checks += $false
    }
} catch {
    Write-Host "  ⚠️  Council" -ForegroundColor Yellow -NoNewline
    Write-Host " — Status unavailable (may be starting)" -ForegroundColor DarkYellow
}

# Data freshness
try {
    $data = Invoke-RestMethod "http://localhost:$BackendPort/api/v1/status/data" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    if ($data.daily_bars_date) {
        Write-Host "  ✅ Market Data" -ForegroundColor Green -NoNewline
        Write-Host " — Latest: $($data.daily_bars_date)" -ForegroundColor DarkGray
    } else {
        Write-Host "  ⚠️  Market Data" -ForegroundColor Yellow -NoNewline
        Write-Host " — No data ingested yet" -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "  ⚠️  Market Data" -ForegroundColor Yellow -NoNewline
    Write-Host " — Status unavailable" -ForegroundColor DarkYellow
}

# ── Frontend ─────────────────────────────────────────────
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "  Frontend:" -ForegroundColor Yellow
    $checks += Test-Port $FrontendPort "Frontend dev server"
}

# ── Brain Service ────────────────────────────────────────
if (-not $SkipBrain) {
    Write-Host ""
    Write-Host "  Optional Services:" -ForegroundColor Yellow
    $brainReachable = Test-Port $BrainPort "Brain Service (gRPC)"
    if ($brainReachable) {
        Write-Host "    ↳ LLM inference available via gRPC" -ForegroundColor DarkGray
    } else {
        Write-Host "    ↳ Brain service is optional — system will use cloud LLMs" -ForegroundColor DarkYellow
    }
}

# ── Summary ──────────────────────────────────────────────
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
$passed = ($checks | Where-Object { $_ -eq $true }).Count
$total = $checks.Count
if ($passed -eq $total) {
    Write-Host "   ✅ All $total critical checks PASSED" -ForegroundColor Green
    Write-Host "  ============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  System is ready for trading operations" -ForegroundColor Green
    exit 0
} else {
    Write-Host "   ⚠️  $passed/$total checks passed" -ForegroundColor Yellow
    Write-Host "  ============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Some services are unavailable — check logs" -ForegroundColor Yellow
    exit 1
}
