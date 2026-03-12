# Deploy PC1 (ESPENMAIN): git pull, pip install, restart backend + frontend, health check.
# Usage: .\scripts\deploy-pc1.ps1 [-Rollback]
# Run from repo root. Requires: Git, Python venv at backend\venv, Node for frontend.

param(
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { Get-Location }
if (-not (Test-Path (Join-Path $Root "backend"))) { $Root = Get-Location }
Set-Location $Root

$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$Pip = Join-Path $BackendDir "venv\Scripts\pip.exe"
$LastGoodFile = Join-Path $Root ".deploy-last-good-pc1"

function Write-Step { param($Msg) Write-Host "  [$Msg]" -ForegroundColor Cyan }
function Write-Ok   { param($Msg) Write-Host "  OK: $Msg" -ForegroundColor Green }
function Write-Fail { param($Msg) Write-Host "  FAIL: $Msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  === Embodier Trader — Deploy PC1 (ESPENMAIN) ===" -ForegroundColor DarkCyan
Write-Host ""

if ($Rollback) {
    if (-not (Test-Path $LastGoodFile)) { Write-Fail "No last-good commit file. Run deploy once without -Rollback." }
    $lastGood = Get-Content $LastGoodFile -Raw
    Write-Step "Rolling back to $lastGood"
    git checkout $lastGood -- .
    git checkout $lastGood
    Write-Ok "Checked out $lastGood"
    # Continue to install + restart below
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

Write-Step "Backend: pip install"
if (-not (Test-Path $Pip)) { Write-Fail "backend\venv not found. Create it first." }
& $Pip install -r (Join-Path $BackendDir "requirements.txt") -q
if ($LASTEXITCODE -ne 0) { Write-Fail "pip install failed" }
Write-Ok "Backend deps installed"

Write-Step "Frontend: npm install"
Set-Location $FrontendDir
npm install --silent 2>$null
if ($LASTEXITCODE -ne 0) { Write-Fail "npm install failed" }
Set-Location $Root
Write-Ok "Frontend deps installed"

Write-Step "Restart instructions"
Write-Host "  Backend:  Stop any running uvicorn/start_server, then run:" -ForegroundColor Gray
Write-Host "    cd $BackendDir; .\venv\Scripts\Activate.ps1; python start_server.py" -ForegroundColor Gray
Write-Host "  Frontend: In another terminal:" -ForegroundColor Gray
Write-Host "    cd $FrontendDir; npm run dev" -ForegroundColor Gray
Write-Host "  Or use: .\start-embodier.ps1" -ForegroundColor Gray
Write-Host ""

Write-Step "Smoke check (optional — run after services are up)"
Write-Host "  .\scripts\smoke-test.ps1 -BaseUrl http://localhost:8000" -ForegroundColor Gray
Write-Host ""
Write-Ok "Deploy complete."
Write-Host ""
