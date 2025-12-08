<#
.SYNOPSIS
    Creates a desktop shortcut for Elite Trading System Glass House launcher
.DESCRIPTION
    Run this script once to create a desktop shortcut that launches the entire system
.NOTES
    Version: 1.0
    Date: December 7, 2025
#>

# Requires Administrator for creating shortcuts
#Requires -RunAsAdministrator

$PROJECT_ROOT = "C:\Users\Espen\elite-trading-system"
$DESKTOP = [Environment]::GetFolderPath("Desktop")
$SHORTCUT_PATH = Join-Path $DESKTOP "Elite Trading System.lnk"

Write-Host "" 
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Elite Trading System" -ForegroundColor Cyan
Write-Host "  Desktop Shortcut Creator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify project exists
if (-not (Test-Path $PROJECT_ROOT)) {
    Write-Host "ERROR: Project not found at: $PROJECT_ROOT" -ForegroundColor Red
    Write-Host "Please edit this script and update PROJECT_ROOT to your installation path." -ForegroundColor Yellow
    pause
    exit 1
}

# Create WScript Shell object
$WScriptShell = New-Object -ComObject WScript.Shell

# Create the shortcut
$Shortcut = $WScriptShell.CreateShortcut($SHORTCUT_PATH)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PROJECT_ROOT\LAUNCH_AURORA.ps1`""
$Shortcut.WorkingDirectory = $PROJECT_ROOT
$Shortcut.Description = "Launch Elite Trading System with Glass House UI"
$Shortcut.IconLocation = "powershell.exe,0"
$Shortcut.Save()

Write-Host "SUCCESS: Desktop shortcut created!" -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut location: $SHORTCUT_PATH" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click the shortcut on your desktop to launch:" -ForegroundColor Yellow
Write-Host "  - Backend API (http://localhost:8000)" -ForegroundColor White
Write-Host "  - Glass House UI (http://localhost:3000)" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
pause
