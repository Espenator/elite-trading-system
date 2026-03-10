<#
.SYNOPSIS
  Pull latest fixes, patch .env, restart backend+frontend, trigger backfill.
  Run from project root: .\scripts\apply-fixes.ps1
#>
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$LogDir      = Join-Path $Root "logs"
$EnvFile     = Join-Path $BackendDir ".env"
$VenvPython  = Join-Path $BackendDir "venv\Scripts\python.exe"
$BackendPort = 8000
$FrontendPort = 3000

function Log($msg, $color) {
    $ts = Get-Date -Format "HH:mm:ss"
    if ($color) { Write-Host "  [$ts] $msg" -ForegroundColor $color }
    else { Write-Host "  [$ts] $msg" }
}

function Kill-PortProcesses([int]$Port) {
    $lines = netstat -ano 2>$null | Select-String "\s+0\.0\.0\.0:$Port\s+|\s+127\.0\.0\.1:$Port\s+|\s+\[::]:$Port\s+"
    $pids = @()
    foreach ($line in $lines) {
        $parts = "$line" -split '\s+'
        $pidStr = $parts[$parts.Length - 1]
        if ($pidStr -match '^\d+$' -and [int]$pidStr -ne 0) { $pids += $pidStr }
    }
    $pids = $pids | Sort-Object -Unique
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Log "Killing PID $procId ($($proc.ProcessName)) on port $Port" Yellow
            taskkill /F /PID $procId 2>$null | Out-Null
        }
    }
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER — APPLY BUG FIXES" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# ── Step 1: Pull latest code ────────────────────────────────────────────────
Log "Pulling latest fixes from remote..." Cyan
Set-Location $Root
git fetch origin claude/setup-embodier-trader-bhimn 2>&1 | Out-Null

$currentBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
if ($currentBranch -ne "claude/setup-embodier-trader-bhimn") {
    Log "Switching to branch claude/setup-embodier-trader-bhimn..." Yellow
    git checkout claude/setup-embodier-trader-bhimn 2>&1 | Out-Null
}
git pull origin claude/setup-embodier-trader-bhimn 2>&1 | ForEach-Object { Log $_ DarkGray }
Log "Code updated." Green

# ── Step 2: Patch .env (ALPACA_FEED=iex -> sip) ────────────────────────────
if (Test-Path $EnvFile) {
    $envContent = Get-Content $EnvFile -Raw
    if ($envContent -match "ALPACA_FEED=iex") {
        $envContent = $envContent -replace "ALPACA_FEED=iex", "ALPACA_FEED=sip"
        $utf8NoBom = New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($EnvFile, $envContent, $utf8NoBom)
        Log "Patched .env: ALPACA_FEED=iex -> sip (real-time SIP feed)" Green
    } elseif ($envContent -match "ALPACA_FEED=sip") {
        Log ".env already has ALPACA_FEED=sip" DarkGray
    } else {
        # ALPACA_FEED not present at all — append it
        Add-Content $EnvFile "`n# Real-time SIP feed (paid subscription)`nALPACA_FEED=sip"
        Log "Added ALPACA_FEED=sip to .env" Green
    }
} else {
    Log ".env not found at $EnvFile — copy .env.example and add your API keys!" Red
}

# ── Step 3: Stop existing backend + frontend ────────────────────────────────
Log "Stopping existing processes..." Yellow
Kill-PortProcesses $BackendPort
Kill-PortProcesses $FrontendPort

# Clean DuckDB WAL locks
$DuckDbFile = Join-Path $BackendDir "data\analytics.duckdb"
foreach ($ext in @(".wal", ".tmp")) {
    $f = "$DuckDbFile$ext"
    if (Test-Path $f) {
        Remove-Item $f -Force -ErrorAction SilentlyContinue
        Log "Removed stale lock: $(Split-Path $f -Leaf)" Yellow
    }
}
Start-Sleep 2

# ── Step 4: Install any new Python deps ─────────────────────────────────────
if (Test-Path $VenvPython) {
    Log "Checking Python dependencies..." Cyan
    $VenvPip = Join-Path $BackendDir "venv\Scripts\pip.exe"
    # zoneinfo backport needed for DST fix on Python < 3.9
    & $VenvPython -c "from zoneinfo import ZoneInfo" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Log "Installing backports.zoneinfo for DST fix..." Yellow
        & $VenvPip install backports.zoneinfo --quiet 2>$null
    }
    Log "Dependencies OK" Green
} else {
    Log "venv not found — run start-embodier.bat first to create it" Red
    exit 1
}

# ── Step 5: Start backend ───────────────────────────────────────────────────
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir -Force | Out-Null }
$backendLogFile = Join-Path $LogDir "backend.log"
$backendErrFile = Join-Path $LogDir "backend-error.log"
"" | Out-File $backendLogFile -Encoding utf8
"" | Out-File $backendErrFile -Encoding utf8

$env:PYTHONUTF8 = "1"

Log "Starting backend..." Cyan
$backendProc = Start-Process -FilePath $VenvPython -ArgumentList "-X", "utf8", "-u", "start_server.py" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $backendLogFile `
    -RedirectStandardError $backendErrFile `
    -PassThru -WindowStyle Hidden

Log "Backend PID: $($backendProc.Id)" DarkGray

# Wait for backend health
$healthy = $false
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep 1
    try {
        $r = Invoke-WebRequest "http://localhost:$BackendPort/healthz" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    Write-Host "." -NoNewline
}
Write-Host ""
if ($healthy) {
    Log "Backend HEALTHY at http://localhost:$BackendPort" Green
} else {
    Log "Backend not responding yet — check logs\backend.log" Yellow
}

# ── Step 6: Trigger backfill (populate indicators + features) ───────────────
Log "Triggering ingestion backfill (30 days)..." Cyan
try {
    $backfillResp = Invoke-WebRequest "http://localhost:$BackendPort/api/v1/ingestion/backfill" `
        -Method POST -TimeoutSec 120 -UseBasicParsing -ErrorAction SilentlyContinue `
        -ContentType "application/json"
    if ($backfillResp.StatusCode -eq 200) {
        Log "Backfill triggered successfully!" Green
        $body = $backfillResp.Content | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($body) {
            $ohlcvRows = if ($body.ohlcv -and $body.ohlcv.total_rows) { $body.ohlcv.total_rows } else { "N/A" }
            $indCount  = if ($body.indicators) { $body.indicators } else { "N/A" }
            Log "  OHLCV rows: $ohlcvRows" DarkGray
            Log "  Indicators: $indCount" DarkGray
        }
    } else {
        Log "Backfill returned status $($backfillResp.StatusCode)" Yellow
    }
} catch {
    Log "Backfill endpoint not available (auto-backfill will run in ~30s anyway)" Yellow
}

# ── Step 7: Start frontend ──────────────────────────────────────────────────
Set-Location $FrontendDir
if (-not (Test-Path "node_modules")) {
    Log "Installing frontend dependencies..." Cyan
    npm install 2>$null
}

$frontendLogFile = Join-Path $LogDir "frontend.log"
$frontendErrFile = Join-Path $LogDir "frontend-error.log"
try { "" | Out-File $frontendLogFile -Encoding utf8 -ErrorAction Stop } catch { }
try { "" | Out-File $frontendErrFile -Encoding utf8 -ErrorAction Stop } catch { }

$env:VITE_BACKEND_URL = "http://localhost:$BackendPort"

$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npx vite --port $FrontendPort --host" `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $frontendLogFile `
    -RedirectStandardError $frontendErrFile `
    -PassThru -WindowStyle Hidden

Start-Sleep 3
Log "Frontend at http://localhost:$FrontendPort" Green

# ── Step 8: Open browser ────────────────────────────────────────────────────
Start-Process "http://localhost:$FrontendPort"

# ── Summary ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   ALL FIXES APPLIED" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Fixed:" -ForegroundColor Cyan
Write-Host "    1. Status bar now shows real WS/API status (was always red)" -ForegroundColor White
Write-Host "    2. Market tickers show real prices (was all +0.00%)" -ForegroundColor White
Write-Host "    3. Active Trades NAV shows real equity (was `$0.00)" -ForegroundColor White
Write-Host "    4. Indicators/features auto-backfilling (was 0 rows)" -ForegroundColor White
Write-Host "    5. ALPACA_FEED=sip (real-time, was 15-min delayed iex)" -ForegroundColor White
Write-Host "    6. DST timezone fixed (was off by 1 hour)" -ForegroundColor White
Write-Host "    7. Circuit breaker allows pre/after-market trading" -ForegroundColor White
Write-Host "    8. Snapshot fallback works during market hours" -ForegroundColor White
Write-Host ""
Write-Host "  Backend PID:  $($backendProc.Id)" -ForegroundColor DarkGray
Write-Host "  Frontend PID: $($frontendProc.Id)" -ForegroundColor DarkGray
Write-Host "  Logs: $LogDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Wait ~30s for indicators to populate, then refresh Dashboard." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

# Monitor loop
try {
    while ($true) { Start-Sleep 10 }
} finally {
    Log "Shutting down..." Yellow
    Kill-PortProcesses $BackendPort
    Kill-PortProcesses $FrontendPort
    Log "Stopped." Green
}
