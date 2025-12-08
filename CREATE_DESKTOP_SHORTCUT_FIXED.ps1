<#
.SYNOPSIS
    Create Desktop Shortcut for Elite Trading System
.DESCRIPTION
    Automatically detects project path and creates desktop shortcut
.NOTES
    Run this script from the project directory
#>

# Auto-detect project root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = $SCRIPT_DIR

Write-Host "`n" -NoNewline
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "  ELITE TRADING SYSTEM - DESKTOP SHORTCUT CREATOR" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "`n" -NoNewline

# Verify project location
Write-Host "Project Root: $PROJECT_ROOT" -ForegroundColor Yellow
Write-Host "`n" -NoNewline

# Check if launcher exists
$launcherPath = Join-Path $PROJECT_ROOT "LAUNCH_ELITE_TRADER.ps1"
if (-not (Test-Path $launcherPath)) {
    Write-Host "ERROR: Launcher not found!" -ForegroundColor Red
    Write-Host "   Expected: $launcherPath" -ForegroundColor Red
    Write-Host "`n" -NoNewline
    pause
    exit 1
}

Write-Host "Launcher found: $launcherPath" -ForegroundColor Green

# Get desktop path
$desktopPath = [Environment]::GetFolderPath("Desktop")
Write-Host "Desktop path: $desktopPath" -ForegroundColor Green

# Create shortcut
$shortcutPath = Join-Path $desktopPath "Elite Trading System.lnk"

Write-Host "`nCreating shortcut..." -ForegroundColor Cyan

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($shortcutPath)

# Shortcut properties
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`""
$Shortcut.WorkingDirectory = $PROJECT_ROOT
$Shortcut.Description = "Elite Trading System - AI-Powered Trading Intelligence"
$Shortcut.IconLocation = "powershell.exe,0"

$Shortcut.Save()

Write-Host "`n" -NoNewline
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  DESKTOP SHORTCUT CREATED SUCCESSFULLY" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "`n" -NoNewline
Write-Host "Shortcut Details:" -ForegroundColor Cyan
Write-Host "  Name:       Elite Trading System.lnk" -ForegroundColor White
Write-Host "  Location:   $shortcutPath" -ForegroundColor White
Write-Host "  Launcher:   $launcherPath" -ForegroundColor White
Write-Host "  Project:    $PROJECT_ROOT" -ForegroundColor White
Write-Host "`n" -NoNewline
Write-Host "You can now launch the system from your desktop!" -ForegroundColor Green
Write-Host "`n" -NoNewline

pause
