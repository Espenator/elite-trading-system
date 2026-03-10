# create-shortcut.ps1 — Create a Windows desktop shortcut for Embodier Trader
# Usage: Right-click → Run with PowerShell  (or: powershell -File create-shortcut.ps1)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "  Creating Embodier Trader desktop shortcut..." -ForegroundColor Cyan

$ws = New-Object -ComObject WScript.Shell
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Embodier Trader.lnk"

$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $Root "start-embodier.bat"
$shortcut.WorkingDirectory = $Root
$shortcut.Description = "Launch Embodier Trader — AI-Powered Trading Platform"

# Use the Electron app icon if available
$icoPath = Join-Path $Root "desktop\icons\icon.ico"
if (Test-Path $icoPath) {
    $shortcut.IconLocation = "$icoPath,0"
}

$shortcut.Save()

Write-Host "  Desktop shortcut created: $shortcutPath" -ForegroundColor Green
Write-Host ""

# Also create a Start Menu shortcut
$startMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "Embodier Trader"
if (-not (Test-Path $startMenuDir)) {
    New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
}
$startMenuShortcut = $ws.CreateShortcut((Join-Path $startMenuDir "Embodier Trader.lnk"))
$startMenuShortcut.TargetPath = Join-Path $Root "start-embodier.bat"
$startMenuShortcut.WorkingDirectory = $Root
$startMenuShortcut.Description = "Launch Embodier Trader — AI-Powered Trading Platform"
if (Test-Path $icoPath) {
    $startMenuShortcut.IconLocation = "$icoPath,0"
}
$startMenuShortcut.Save()

Write-Host "  Start Menu shortcut created: $startMenuDir" -ForegroundColor Green
Write-Host ""
Write-Host "  You can now launch Embodier Trader from:" -ForegroundColor White
Write-Host "    - Desktop icon" -ForegroundColor DarkGray
Write-Host "    - Start Menu > Embodier Trader" -ForegroundColor DarkGray
Write-Host "    - Double-click start-embodier.bat" -ForegroundColor DarkGray
Write-Host ""
