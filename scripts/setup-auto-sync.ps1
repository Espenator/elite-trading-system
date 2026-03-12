#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Embodier Trader - One-Shot Auto-Sync Setup
    Run this ONCE on ESPENMAIN (as Administrator) to configure
    auto git-pull on BOTH PCs whenever main branch is pushed.

.DESCRIPTION
    This script does everything end-to-end:
      1. Installs the auto-pull scheduled task on THIS PC (ESPENMAIN)
      2. Copies auto-pull.ps1 to ProfitTrader over the LAN
      3. Installs the scheduled task on ProfitTrader remotely via PowerShell remoting
      4. Verifies both tasks are running

    Result: Within 2 minutes of any git push to main, both PCs
    automatically pull the latest code.

.NOTES
    Run from ESPENMAIN as Administrator (from repo root):
        Right-click PowerShell > Run as Administrator
        cd <repo root>   # e.g. C:\Users\Espen\elite-trading-system
        .\scripts\setup-auto-sync.ps1

    Paths: Use -PC1RepoPath / -PC2RepoPath if your clone is elsewhere. See PATH-STANDARD.md.
#>

[CmdletBinding()]
param(
    # Repo root on this PC (PC1). Default: parent of scripts/ when run from repo.
    [string]$PC1RepoPath   = "",
    [string]$PC2RepoPath   = "C:\Users\ProfitTrader\elite-trading-system",
    [string]$PC2IP         = "192.168.1.116",
    [string]$PC2Hostname   = "ProfitTrader",
    [string]$TaskName      = "EmbodierTrader-GitAutoSync",
    # Poll interval in minutes (how often to check for new commits)
    [int]$PollMinutes      = 2
)

$ErrorActionPreference = "Stop"
$ScriptPath = $PSScriptRoot
if (-not $ScriptPath) { $ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path }
# Default PC1 repo root = parent of scripts/ when run from repo
if (-not $PC1RepoPath -and $ScriptPath) {
    $maybeRepo = Split-Path -Parent $ScriptPath
    if (Test-Path (Join-Path $maybeRepo ".git")) { $PC1RepoPath = $maybeRepo }
}
if (-not $PC1RepoPath) { $PC1RepoPath = "C:\Users\Espen\elite-trading-system" }
$AutoPullScript = Join-Path $ScriptPath "auto-pull.ps1"

# ─────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Embodier Trader - Auto-Sync Setup           ║" -ForegroundColor Cyan
Write-Host "║  ESPENMAIN (PC1) + ProfitTrader (PC2)        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────
# STEP 1: Validate auto-pull.ps1 exists
# ─────────────────────────────────────────────
Write-Host "[1/5] Checking auto-pull.ps1..." -ForegroundColor Yellow
if (-not (Test-Path $AutoPullScript)) {
    Write-Host "  auto-pull.ps1 not found at: $AutoPullScript" -ForegroundColor Red
    Write-Host "  Make sure you ran: git pull origin main" -ForegroundColor Red
    exit 1
}
Write-Host "  Found: $AutoPullScript" -ForegroundColor Green

# ─────────────────────────────────────────────
# STEP 2: Install scheduled task on THIS PC (ESPENMAIN)
# ─────────────────────────────────────────────
Write-Host ""
Write-Host "[2/5] Installing scheduled task on ESPENMAIN..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$AutoPullScript`" -RepoPath `"$PC1RepoPath`""

$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes $PollMinutes) -Once -At (Get-Date)

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  Removed existing task." -ForegroundColor Gray
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Polls GitHub every $PollMinutes min and auto-pulls Embodier Trader on push to main" | Out-Null

Write-Host "  Task installed on ESPENMAIN: every $PollMinutes minutes" -ForegroundColor Green

# ─────────────────────────────────────────────
# STEP 3: Test connectivity to ProfitTrader
# ─────────────────────────────────────────────
Write-Host ""
Write-Host "[3/5] Testing connectivity to ProfitTrader ($PC2IP)..." -ForegroundColor Yellow

$ping = Test-Connection -ComputerName $PC2IP -Count 1 -Quiet
if (-not $ping) {
    Write-Host "  Cannot reach ProfitTrader at $PC2IP" -ForegroundColor Red
    Write-Host "  Is ProfitTrader on? Check LAN connection." -ForegroundColor Red
    Write-Host "  Skipping remote setup - run this script again when ProfitTrader is online." -ForegroundColor Yellow
    exit 0
}
Write-Host "  ProfitTrader reachable at $PC2IP" -ForegroundColor Green

# Enable PSRemoting on ProfitTrader (requires WinRM)
Write-Host "  Enabling WinRM on ProfitTrader (may prompt for credentials)..." -ForegroundColor Gray
try {
    # This uses the LAN - no internet needed
    $session = New-PSSession -ComputerName $PC2IP -ErrorAction Stop
    Write-Host "  PSRemoting session established." -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "  PSRemoting not yet enabled on ProfitTrader." -ForegroundColor Yellow
    Write-Host "  Run this on ProfitTrader first (as Admin), then re-run this script:" -ForegroundColor Yellow
    Write-Host "    Enable-PSRemoting -Force" -ForegroundColor White
    Write-Host "    Set-Item WSMan:\localhost\Client\TrustedHosts -Value '$PC2IP' -Force" -ForegroundColor White
    Write-Host ""
    Write-Host "  Or just run auto-pull.ps1 manually on ProfitTrader - see scripts/auto-pull.ps1" -ForegroundColor Gray
    exit 0
}

# ─────────────────────────────────────────────
# STEP 4: Copy auto-pull.ps1 to ProfitTrader & install task
# ─────────────────────────────────────────────
Write-Host ""
Write-Host "[4/5] Setting up ProfitTrader remotely..." -ForegroundColor Yellow

Invoke-Command -Session $session -ScriptBlock {
    param($RepoPath, $AutoPullContent, $TaskName, $PollMinutes)

    # Ensure repo path exists (clone if missing)
    if (-not (Test-Path $RepoPath)) {
        Write-Host "  Cloning repo to ProfitTrader..." -ForegroundColor Yellow
        $parent = Split-Path $RepoPath -Parent
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Set-Location $parent
        git clone https://github.com/Espenator/elite-trading-system.git
    }

    # Write auto-pull.ps1 to scripts folder on ProfitTrader
    $ScriptsDir = Join-Path $RepoPath "scripts"
    $TargetScript = Join-Path $ScriptsDir "auto-pull.ps1"
    New-Item -ItemType Directory -Force -Path $ScriptsDir | Out-Null
    Set-Content -Path $TargetScript -Value $AutoPullContent -Encoding UTF8
    Write-Host "  Wrote auto-pull.ps1 to $TargetScript" -ForegroundColor Green

    # Install scheduled task on ProfitTrader
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$TargetScript`" -RepoPath `"$RepoPath`""

    $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes $PollMinutes) -Once -At (Get-Date)

    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable

    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -RunLevel Highest `
        -Description "Polls GitHub every $PollMinutes min and auto-pulls Embodier Trader on push to main" | Out-Null

    Write-Host "  Task installed on ProfitTrader: every $PollMinutes minutes" -ForegroundColor Green

} -ArgumentList $PC2RepoPath, (Get-Content $AutoPullScript -Raw), $TaskName, $PollMinutes

Remove-PSSession $session

# ─────────────────────────────────────────────
# STEP 5: Verify both tasks
# ─────────────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Verifying tasks..." -ForegroundColor Yellow

$local = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($local) {
    Write-Host "  ESPENMAIN: Task '$TaskName' - $($local.State)" -ForegroundColor Green
} else {
    Write-Host "  ESPENMAIN: Task NOT found" -ForegroundColor Red
}

try {
    $session2 = New-PSSession -ComputerName $PC2IP
    $remote = Invoke-Command -Session $session2 -ScriptBlock {
        param($t) Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    } -ArgumentList $TaskName
    if ($remote) {
        Write-Host "  ProfitTrader: Task '$TaskName' - $($remote.State)" -ForegroundColor Green
    } else {
        Write-Host "  ProfitTrader: Task NOT found" -ForegroundColor Red
    }
    Remove-PSSession $session2
} catch {
    Write-Host "  ProfitTrader: Could not verify (check manually)" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────
Write-Host ""
Write-Host '=============================================' -ForegroundColor Green
Write-Host '  AUTO-SYNC SETUP COMPLETE' -ForegroundColor Green
Write-Host "  Both PCs will auto-pull every $PollMinutes minutes" -ForegroundColor Green
Write-Host "  Push to main -> both PCs update in <$PollMinutes min" -ForegroundColor Green
Write-Host '=============================================' -ForegroundColor Green
Write-Host ''
$verifyCmd = 'Get-ScheduledTask -TaskName "EmbodierTrader-GitAutoSync"'
$runCmd = 'Start-ScheduledTask -TaskName "EmbodierTrader-GitAutoSync"'
$removeCmd = 'Unregister-ScheduledTask -TaskName "EmbodierTrader-GitAutoSync" -Confirm:' + '$false'
$logPath = 'C:\Windows\Temp\embodier-auto-sync.log'
Write-Host "To verify: $verifyCmd" -ForegroundColor Gray
Write-Host "To run now: $runCmd" -ForegroundColor Gray
Write-Host "To remove: $removeCmd" -ForegroundColor Gray
Write-Host "Logs: $logPath" -ForegroundColor Gray
