# create-desktop-shortcut.ps1 - Create "Embodier Trader" desktop shortcut (24/7 launcher)
# Run once from repo root: .\scripts\create-desktop-shortcut.ps1
# Shortcut: stops existing processes, clears ports, starts backend + frontend with supervisor and auto-execute.

$ErrorActionPreference = "Stop"
$Root = if (Test-Path (Join-Path $PSScriptRoot "backend")) { $PSScriptRoot } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$Launcher = Join-Path $Root "start-embodier.ps1"
if (-not (Test-Path $Launcher)) {
    Write-Host "ERROR: start-embodier.ps1 not found at $Launcher" -ForegroundColor Red
    exit 1
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Embodier Trader.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$Launcher`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "Embodier Trader 24/7: port clear, backend + frontend + auto-execute, supervisor keeps it running."
$Shortcut.WindowStyle = 1
$Shortcut.Save()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host ""
Write-Host "  Desktop shortcut created:" -ForegroundColor Green
Write-Host "  $ShortcutPath" -ForegroundColor Cyan
Write-Host "  Double-click to start (stops existing, clears ports, API + WS + frontend with auto-restart and auto-execute)." -ForegroundColor Gray
Write-Host ""
