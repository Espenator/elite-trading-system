# Deploy PC2 (ProfitTrader): git pull, pip install, restart brain_service (+ optional backend).
# Usage: .\scripts\deploy-pc2.ps1 [-Rollback]
# Run from repo root.

param(
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }
if (-not (Test-Path (Join-Path $Root "brain_service"))) { $Root = Get-Location }
Set-Location $Root

$BackendDir = Join-Path $Root "backend"
$BrainDir = Join-Path $Root "brain_service"
$LastGoodFile = Join-Path $Root ".deploy-last-good-pc2"

# Prefer brain_service venv; fallback to backend venv for pip
$Pip = $null
if (Test-Path (Join-Path $BrainDir "venv\Scripts\pip.exe")) { $Pip = Join-Path $BrainDir "venv\Scripts\pip.exe" }
if (-not $Pip -and (Test-Path (Join-Path $BackendDir "venv\Scripts\pip.exe"))) { $Pip = Join-Path $BackendDir "venv\Scripts\pip.exe" }

function Write-Step { param($Msg) Write-Host "  [$Msg]" -ForegroundColor Cyan }
function Write-Ok   { param($Msg) Write-Host "  OK: $Msg" -ForegroundColor Green }
function Write-Fail { param($Msg) Write-Host "  FAIL: $Msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  === Embodier Trader — Deploy PC2 (ProfitTrader) ===" -ForegroundColor DarkCyan
Write-Host ""

if ($Rollback) {
    if (-not (Test-Path $LastGoodFile)) { Write-Fail "No last-good commit file. Run deploy once without -Rollback." }
    $lastGood = Get-Content $LastGoodFile -Raw
    Write-Step "Rolling back to $lastGood"
    git checkout $lastGood -- .
    git checkout $lastGood
    Write-Ok "Checked out $lastGood"
} else {
    $current = git rev-parse HEAD
    Set-Content $LastGoodFile $current -NoNewline
    Write-Ok "Saved last-good commit: $current"
}

Write-Step "Git pull"
git fetch origin main
git pull origin main
if ($LASTEXITCODE -ne 0) { Write-Fail "git pull failed" }
Write-Ok "Code updated to $(git rev-parse --short HEAD)"

Write-Step "Brain service: pip install"
if (Test-Path (Join-Path $BrainDir "requirements.txt")) {
    if ($Pip) {
        & $Pip install -r (Join-Path $BrainDir "requirements.txt") -q
        if ($LASTEXITCODE -ne 0) { Write-Fail "brain pip install failed" }
        Write-Ok "Brain deps installed"
    } else {
        Write-Host "  (No venv found; create brain_service/venv or backend/venv)" -ForegroundColor Yellow
    }
}

Write-Step "Backend (optional): pip install"
if (Test-Path (Join-Path $BackendDir "venv\Scripts\pip.exe")) {
    & (Join-Path $BackendDir "venv\Scripts\pip.exe") install -r (Join-Path $BackendDir "requirements.txt") -q
    Write-Ok "Backend deps installed"
}

Write-Step "Restart instructions"
Write-Host "  Brain:    cd $BrainDir; .\venv\Scripts\Activate.ps1; python server.py" -ForegroundColor Gray
Write-Host "  Backend: cd $BackendDir; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Gray
Write-Host ""

Write-Step "Smoke check (after services are up)"
Write-Host "  Backend:  .\scripts\smoke-test.ps1 -BaseUrl http://localhost:8000" -ForegroundColor Gray
Write-Host "  Brain:    Test-NetConnection localhost -Port 50051" -ForegroundColor Gray
Write-Host ""
Write-Ok "Deploy complete."
Write-Host ""
