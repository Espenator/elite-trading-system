# rollback.ps1 — Revert to last known good commit (tag or HEAD~1).
# Usage: .\scripts\rollback.ps1 [ref]
#   ref = git ref (e.g. v5.0.0 or HEAD~1). Default: HEAD~1

param([string]$Ref = "HEAD~1")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$rev = git rev-parse $Ref 2>$null
if (-not $rev) {
    Write-Host "Invalid ref: $Ref" -ForegroundColor Red
    exit 1
}
Write-Host "Rolling back to $Ref ($rev)" -ForegroundColor Yellow
git reset --hard $rev
Write-Host "Done. Restart services (deploy-pc1.ps1 / deploy-pc2.ps1) if needed." -ForegroundColor Green
