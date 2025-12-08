<#
.SYNOPSIS
    Fix OneDrive Path Issues
.DESCRIPTION
    Detects actual project location (OneDrive vs Local) and updates all scripts
.NOTES
    Run this to fix path confusion
#>

Clear-Host
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  PATH DETECTION & FIX UTILITY" -ForegroundColor Cyan
Write-Host "================================================================================`n" -ForegroundColor Cyan

# Find all possible project locations
$possiblePaths = @(
    "C:\Users\Espen\elite-trading-system",
    "C:\Users\Espen\Documents\GitHub\elite-trading-system",
    "C:\Users\Espen\OneDrive\Documents\GitHub\elite-trading-system",
    (Get-Location).Path
)

Write-Host "Searching for project...`n" -ForegroundColor Yellow

$foundPaths = @()
foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        # Verify it's actually our project
        if ((Test-Path "$path\backend\main.py") -and (Test-Path "$path\config.yaml")) {
            $foundPaths += $path
            Write-Host "  FOUND: $path" -ForegroundColor Green
        }
    }
}

if ($foundPaths.Count -eq 0) {
    Write-Host "`nERROR: Project not found in any expected location!" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    pause
    exit 1
}

if ($foundPaths.Count -gt 1) {
    Write-Host "`nMultiple project locations found:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $foundPaths.Count; $i++) {
        Write-Host "  [$($i+1)] $($foundPaths[$i])" -ForegroundColor White
    }
    Write-Host "`nWhich one do you want to use? (1-$($foundPaths.Count)): " -ForegroundColor Yellow -NoNewline
    $choice = Read-Host
    $PROJECT_ROOT = $foundPaths[$choice - 1]
} else {
    $PROJECT_ROOT = $foundPaths[0]
}

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "  PROJECT LOCATION CONFIRMED" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "`n  Path: $PROJECT_ROOT`n" -ForegroundColor White

# Check if OneDrive path
$isOneDrive = $PROJECT_ROOT -like "*OneDrive*"

if ($isOneDrive) {
    Write-Host "DETECTED: OneDrive synchronized folder" -ForegroundColor Yellow
    Write-Host "This means your files are:" -ForegroundColor Yellow
    Write-Host "  - Stored in cloud (OneDrive)" -ForegroundColor White
    Write-Host "  - Synced locally to this path" -ForegroundColor White
    Write-Host "  - Accessible from any device with OneDrive" -ForegroundColor White
} else {
    Write-Host "DETECTED: Local folder (not synced to OneDrive)" -ForegroundColor Green
    Write-Host "This means your files are:" -ForegroundColor Green
    Write-Host "  - Stored only on this computer" -ForegroundColor White
    Write-Host "  - NOT backed up to cloud" -ForegroundColor White
    Write-Host "  - Only accessible from this PC" -ForegroundColor White
}

Write-Host "`nDo you want to use this location? (Y/N): " -ForegroundColor Yellow -NoNewline
$confirm = Read-Host

if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "`nCancelled." -ForegroundColor Red
    pause
    exit 0
}

# Save to config file
$configPath = Join-Path $PROJECT_ROOT ".project_path"
$PROJECT_ROOT | Out-File -FilePath $configPath -Encoding UTF8

Write-Host "`nProject path saved to: .project_path" -ForegroundColor Green

# Show summary
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURATION COMPLETE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "`nProject Root:" -ForegroundColor Yellow
Write-Host "  $PROJECT_ROOT" -ForegroundColor White
Write-Host "`nOneDrive Status:" -ForegroundColor Yellow
if ($isOneDrive) {
    Write-Host "  ENABLED - Files synced to cloud" -ForegroundColor Green
} else {
    Write-Host "  DISABLED - Local files only" -ForegroundColor Yellow
}

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. All scripts will now use this path automatically" -ForegroundColor White
Write-Host "  2. Run: .\INITIALIZE_SYSTEM.ps1 (to populate database)" -ForegroundColor White
Write-Host "  3. Run: .\LAUNCH_ELITE_TRADER.ps1 (to start system)" -ForegroundColor White

Write-Host "`n" -NoNewline
pause
