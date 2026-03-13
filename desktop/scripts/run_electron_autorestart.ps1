# run_electron_autorestart.ps1 - Run Electron desktop app with auto-restart on exit (24/7)
# Usage: from repo root: .\desktop\scripts\run_electron_autorestart.ps1
#        from desktop:   .\scripts\run_electron_autorestart.ps1
#
# - Restarts when the Electron process exits (crash or user close).
# - Expects backend and frontend to already be running (use run_all_autorestart.ps1 or start-embodier.ps1 -Watch first).
# - Electron will connect to backend/frontend via .embodier-ports.json or device-config defaults.
# Press Ctrl+C once to stop the loop.

param(
    [int]$RestartDelaySeconds = 5
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$DesktopDir = if (Test-Path (Join-Path $ScriptDir "..\package.json")) { (Resolve-Path (Join-Path $ScriptDir "..")).Path } else { Split-Path (Split-Path $ScriptDir -Parent) -Parent | Join-Path -ChildPath "desktop" }
if (-not (Test-Path (Join-Path $DesktopDir "package.json"))) {
    Write-Host "ERROR: package.json not found in $DesktopDir" -ForegroundColor Red
    exit 1
}

Set-Location $DesktopDir
$runCount = 0
$ElectronBin = Join-Path $DesktopDir "node_modules\.bin\electron.cmd"
if (-not (Test-Path $ElectronBin)) {
    Write-Host "  Electron not found. Running npm install..." -ForegroundColor Yellow
    & npm install
    if (-not (Test-Path $ElectronBin)) {
        Write-Host "  ERROR: Electron still not found after npm install. Check desktop/package.json." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "    Embodier Trader - Electron auto-restart" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "  Desktop: $DesktopDir" -ForegroundColor Gray
Write-Host "  Restart delay: ${RestartDelaySeconds}s. Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

while ($true) {
    $runCount++
    Write-Host "  [Run #$runCount] Starting Electron..." -ForegroundColor Yellow
    try {
        & $ElectronBin "."
        $code = $LASTEXITCODE
        Write-Host "  Electron exited (code $code). Restarting in ${RestartDelaySeconds}s..." -ForegroundColor Magenta
    } catch {
        Write-Host "  Error: $_" -ForegroundColor Red
    }
    Start-Sleep -Seconds $RestartDelaySeconds
}
