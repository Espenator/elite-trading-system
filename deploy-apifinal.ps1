# ══════════════════════════════════════════════════════════════
# APIFINAL Deploy Script — Embodier Trader
# Run on EACH PC to copy the right .env files into place
# ══════════════════════════════════════════════════════════════
#
# Usage:
#   On ESPENMAIN:      .\deploy-apifinal.ps1
#   On ProfitTrader:   .\deploy-apifinal.ps1
#
# The script auto-detects which PC it's running on and uses
# the correct Alpaca keys for that machine.
# ══════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$RepoRoot = "C:\Users\Espen\elite-trading-system"
$Hostname = $env:COMPUTERNAME
$Desktop = [Environment]::GetFolderPath("Desktop")

Write-Host "`n=== APIFINAL Deploy ===" -ForegroundColor Cyan
Write-Host "PC: $Hostname" -ForegroundColor Yellow
Write-Host "Repo: $RepoRoot" -ForegroundColor Yellow

# Detect which PC
if ($Hostname -eq "ESPENMAIN") {
    $BackendEnv = "APIFINAL-ESPENMAIN-backend.env"
    Write-Host "Using ESPENMAIN Alpaca keys" -ForegroundColor Green
} elseif ($Hostname -eq "ProfitTrader" -or $Hostname -like "*PROFIT*") {
    $BackendEnv = "APIFINAL-ProfitTrader-backend.env"
    Write-Host "Using ProfitTrader Alpaca keys" -ForegroundColor Green
} else {
    Write-Host "Unknown PC: $Hostname. Defaulting to ESPENMAIN keys." -ForegroundColor Yellow
    $BackendEnv = "APIFINAL-ESPENMAIN-backend.env"
}

# 1. Copy backend .env
$src = Join-Path $RepoRoot $BackendEnv
$dst = Join-Path $RepoRoot "backend\.env"
if (Test-Path $src) {
    Copy-Item $src $dst -Force
    Write-Host "[OK] backend\.env <- $BackendEnv" -ForegroundColor Green
} else {
    Write-Host "[SKIP] $BackendEnv not found in repo root" -ForegroundColor Red
}

# 2. Copy frontend .env
$src2 = Join-Path $RepoRoot "APIFINAL-frontend-v2.env"
$dst2 = Join-Path $RepoRoot "frontend-v2\.env"
if (Test-Path $src2) {
    Copy-Item $src2 $dst2 -Force
    Write-Host "[OK] frontend-v2\.env <- APIFINAL-frontend-v2.env" -ForegroundColor Green
} else {
    Write-Host "[SKIP] APIFINAL-frontend-v2.env not found" -ForegroundColor Red
}

# 3. Copy APIFINAL.xlsx to Desktop
$xlsx = Join-Path $RepoRoot "APIFINAL.xlsx"
$dstXlsx = Join-Path $Desktop "APIFINAL.xlsx"
if (Test-Path $xlsx) {
    Copy-Item $xlsx $dstXlsx -Force
    Write-Host "[OK] APIFINAL.xlsx -> Desktop" -ForegroundColor Green
} else {
    Write-Host "[SKIP] APIFINAL.xlsx not found in repo root" -ForegroundColor Red
}

Write-Host "`n=== Deploy Complete ===" -ForegroundColor Cyan
Write-Host "Files deployed:"
Write-Host "  backend\.env       (with $Hostname Alpaca keys)"
Write-Host "  frontend-v2\.env   (shared)"
Write-Host "  Desktop\APIFINAL.xlsx"
Write-Host "`nNote: .env files with secrets are git-ignored and will NOT be pushed." -ForegroundColor Yellow
Write-Host "The APIFINAL.xlsx on your Desktop has the full inventory." -ForegroundColor Yellow
