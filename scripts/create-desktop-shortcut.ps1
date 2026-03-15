# ============================================================
#  Create Desktop Shortcuts for Embodier Trader
#  Creates "Embodier Trader" (nuke & restart) + "Stop Embodier" .lnk files.
#  Usage: powershell -ExecutionPolicy Bypass -File scripts\create-desktop-shortcut.ps1
# ============================================================

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $Root -or -not (Test-Path (Join-Path $Root "backend"))) {
    $Root = "C:\Users\Espen\elite-trading-system"
}
if (-not (Test-Path (Join-Path $Root "backend"))) {
    Write-Host "  ERROR: Cannot find repo at $Root" -ForegroundColor Red
    exit 1
}

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$WshShell = New-Object -ComObject WScript.Shell

# -- Icon --
$iconPath = Join-Path $Root "desktop\build\icon.ico"
if (-not (Test-Path $iconPath)) {
    $iconPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe,0"
}

# ── Start Shortcut (Nuke & Restart — bulletproof) ──
$startName = "Embodier Trader"
$startLnk = Join-Path $DesktopPath "$startName.lnk"
$nukeScript = Join-Path $Root "nuke-and-restart.ps1"

$shortcut = $WshShell.CreateShortcut($startLnk)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -NoProfile -File `"$nukeScript`""
$shortcut.WorkingDirectory = $Root
$shortcut.Description = "Kill everything, clear locks, restart Embodier Trader fresh"
$shortcut.WindowStyle = 1
if (Test-Path (Join-Path $Root "desktop\build\icon.ico")) {
    $shortcut.IconLocation = $iconPath
}
$shortcut.Save()

Write-Host ""
Write-Host "  [OK] Created: $startLnk" -ForegroundColor Green
Write-Host "       Action: Nuke & Restart (kills old processes, clears ports/locks, starts fresh)" -ForegroundColor Gray

# ── Stop Shortcut ──
$stopName = "Stop Embodier Trader"
$stopLnk = Join-Path $DesktopPath "$stopName.lnk"
$stopScript = Join-Path $Root "scripts\stop_embodier.ps1"

if (Test-Path $stopScript) {
    $stopShortcut = $WshShell.CreateShortcut($stopLnk)
    $stopShortcut.TargetPath = "powershell.exe"
    $stopShortcut.Arguments = "-ExecutionPolicy Bypass -NoProfile -File `"$stopScript`""
    $stopShortcut.WorkingDirectory = $Root
    $stopShortcut.Description = "Stop all Embodier Trader processes"
    $stopShortcut.WindowStyle = 1
    $stopShortcut.Save()

    Write-Host "  [OK] Created: $stopLnk" -ForegroundColor Green
}

# ── Done ──
Write-Host ""
Write-Host "  Two shortcuts on your Desktop:" -ForegroundColor Cyan
Write-Host "    'Embodier Trader'       — double-click to nuke & restart (always works)" -ForegroundColor White
Write-Host "    'Stop Embodier Trader'  — double-click to stop everything" -ForegroundColor White
Write-Host ""
