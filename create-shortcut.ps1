# Embodier Trader — Create Desktop Shortcut
# Run once after cloning: powershell -File create-shortcut.ps1

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [Environment]::GetFolderPath("Desktop")

Write-Host "`nCreating Embodier Trader desktop shortcut..." -ForegroundColor Cyan

$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut("$Desktop\Embodier Trader.lnk")
$shortcut.TargetPath = Join-Path $RepoRoot "launch.bat"
$shortcut.WorkingDirectory = $RepoRoot
$shortcut.Description = "Embodier Trader — AI-Powered Trading Platform"

# Use the icon if it exists
$iconPath = Join-Path $RepoRoot "desktop\icons\icon.ico"
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
}

$shortcut.Save()

Write-Host "[OK] Desktop shortcut created: $Desktop\Embodier Trader.lnk" -ForegroundColor Green
Write-Host "`nDouble-click the shortcut to launch Embodier Trader." -ForegroundColor Yellow
Write-Host "On first run, it will:" -ForegroundColor Yellow
Write-Host "  1. Install Electron + frontend + backend dependencies" -ForegroundColor Yellow
Write-Host "  2. Show a setup wizard for API keys" -ForegroundColor Yellow
Write-Host "  3. Build the frontend" -ForegroundColor Yellow
Write-Host "  4. Start the trading backend" -ForegroundColor Yellow
Write-Host "  5. Open the dashboard" -ForegroundColor Yellow
Write-Host "`nEvery subsequent launch auto-updates from git." -ForegroundColor Yellow
