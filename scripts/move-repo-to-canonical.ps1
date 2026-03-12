# move-repo-to-canonical.ps1
# Moves the repo from Dev\elite-trading-system to C:\Users\Espen\elite-trading-system.
# Run this from C:\Users\Espen with PowerShell (NOT from inside the repo).
# Close Cursor and any terminals using the repo before running.
#
# Usage (from C:\Users\Espen):
#   .\Dev\elite-trading-system\scripts\move-repo-to-canonical.ps1

$ErrorActionPreference = "Stop"
$Source = "C:\Users\Espen\Dev\elite-trading-system"
$Dest   = "C:\Users\Espen\elite-trading-system"
$Backup = "C:\Users\Espen\elite-trading-system-backup"

# Must not be running from inside either folder
$pwd = Get-Location
if ($pwd.Path -eq $Source -or $pwd.Path -like "$Source\*") {
    Write-Host "ERROR: Do not run this script from inside the repo. Run from C:\Users\Espen" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $Source)) {
    Write-Host "ERROR: Source not found: $Source" -ForegroundColor Red
    exit 1
}

if (Test-Path $Dest) {
    Write-Host "Backing up existing $Dest to $Backup ..." -ForegroundColor Yellow
    if (Test-Path $Backup) { Remove-Item $Backup -Recurse -Force }
    Rename-Item -Path $Dest -NewName "elite-trading-system-backup"
}

Write-Host "Moving $Source -> $Dest ..." -ForegroundColor Cyan
Move-Item -Path $Source -Destination $Dest -Force

Write-Host "Done. Repo is now at $Dest" -ForegroundColor Green
Write-Host "Open Cursor at: $Dest" -ForegroundColor Green
Write-Host "You can remove the backup later: Remove-Item '$Backup' -Recurse -Force" -ForegroundColor Gray
