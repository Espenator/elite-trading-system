# Embodier Trader — Install Auto-Start on Windows Boot
# ============================================================================
# Run this ONCE to set up:
#   1. Windows Task Scheduler task → starts Embodier on login
#   2. Desktop shortcut → one-click manual launch
#   3. Start Menu shortcut
#
# Usage (run as Administrator for Task Scheduler):
#   .\install-autostart.ps1
#   .\install-autostart.ps1 -PC pc1    # Force PC1 mode
#   .\install-autostart.ps1 -PC pc2    # Force PC2 mode
# ============================================================================

param(
    [ValidateSet("pc1", "pc2", "auto")]
    [string]$PC = "auto"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Auto-detect PC role
if ($PC -eq "auto") {
    $envFile = Join-Path $RepoRoot "backend\.env"
    if (Test-Path $envFile) {
        $roleLine = Get-Content $envFile | Where-Object { $_ -match "^PC_ROLE=" }
        if ($roleLine -match "secondary") { $PC = "pc2" } else { $PC = "pc1" }
    } else {
        $hostname = [System.Net.Dns]::GetHostName().ToUpper()
        if ($hostname -match "PROFIT") { $PC = "pc2" } else { $PC = "pc1" }
    }
}

$launchScript = Join-Path $RepoRoot "start-$PC.ps1"
if (-not (Test-Path $launchScript)) {
    Write-Host "ERROR: $launchScript not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Embodier Trader — Auto-Start Installer" -ForegroundColor Cyan
Write-Host "  PC Role: $PC"
Write-Host "  Launch Script: $launchScript"
Write-Host ""

# ── 1. Desktop Shortcut ─────────────────────────────────────────────────
Write-Host "[1/3] Creating Desktop shortcut..." -ForegroundColor Yellow
$desktopPath = [System.Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Embodier Trader.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "pwsh.exe"
$shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$launchScript`""
$shortcut.WorkingDirectory = $RepoRoot
$shortcut.Description = "Embodier Trader — $($PC.ToUpper()) Auto-Launch"
$shortcut.WindowStyle = 1  # Normal window

# Use repo icon if available
$iconPath = Join-Path $RepoRoot "desktop\icons\icon.ico"
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
}

$shortcut.Save()
Write-Host "  Created: $shortcutPath" -ForegroundColor Green

# ── 2. Start Menu Shortcut ──────────────────────────────────────────────
Write-Host "[2/3] Creating Start Menu shortcut..." -ForegroundColor Yellow
$startMenuPath = Join-Path ([System.Environment]::GetFolderPath("StartMenu")) "Programs"
$startShortcut = Join-Path $startMenuPath "Embodier Trader.lnk"

$shortcut2 = $shell.CreateShortcut($startShortcut)
$shortcut2.TargetPath = "pwsh.exe"
$shortcut2.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$launchScript`""
$shortcut2.WorkingDirectory = $RepoRoot
$shortcut2.Description = "Embodier Trader — $($PC.ToUpper()) Auto-Launch"
if (Test-Path $iconPath) { $shortcut2.IconLocation = $iconPath }
$shortcut2.Save()
Write-Host "  Created: $startShortcut" -ForegroundColor Green

# ── 3. Windows Task Scheduler (auto-start on login) ────────────────────
Write-Host "[3/3] Creating Windows Task Scheduler task..." -ForegroundColor Yellow

$taskName = "EmbodierTrader-AutoStart"
$taskAction = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument "-WindowStyle Normal -ExecutionPolicy Bypass -File `"$launchScript`" -SkipPull" `
    -WorkingDirectory $RepoRoot

$taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$taskSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # No time limit (runs forever)

try {
    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $taskAction `
        -Trigger $taskTrigger `
        -Settings $taskSettings `
        -Description "Embodier Trader 24/7 auto-start — $($PC.ToUpper()) services with health monitoring" `
        -RunLevel Highest | Out-Null

    Write-Host "  Task '$taskName' registered — will start on login" -ForegroundColor Green
} catch {
    Write-Host "  Task Scheduler requires Admin. Run this script as Administrator." -ForegroundColor Red
    Write-Host "  Or manually create a Startup shortcut:" -ForegroundColor Yellow
    Write-Host "    Win+R → shell:startup → paste shortcut to start-$PC.ps1" -ForegroundColor Yellow
}

# ── Also add to shell:startup as backup ─────────────────────────────────
$startupFolder = [System.Environment]::GetFolderPath("Startup")
$startupShortcut = Join-Path $startupFolder "Embodier Trader.lnk"
$shortcut3 = $shell.CreateShortcut($startupShortcut)
$shortcut3.TargetPath = "pwsh.exe"
$shortcut3.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$launchScript`" -SkipPull"
$shortcut3.WorkingDirectory = $RepoRoot
if (Test-Path $iconPath) { $shortcut3.IconLocation = $iconPath }
$shortcut3.Save()
Write-Host "  Startup shortcut: $startupShortcut" -ForegroundColor Green

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  DONE! Embodier Trader will auto-start:" -ForegroundColor Green
Write-Host "    • On every Windows login (Task Scheduler + Startup folder)" -ForegroundColor White
Write-Host "    • Desktop shortcut for manual launch" -ForegroundColor White
Write-Host "    • Start Menu shortcut" -ForegroundColor White
Write-Host ""
Write-Host "  To start NOW:  .\start-$PC.ps1" -ForegroundColor Cyan
Write-Host "  To uninstall:  Unregister-ScheduledTask -TaskName '$taskName'" -ForegroundColor DarkGray
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
