<#
.SYNOPSIS
    Embodier Trader - Git Auto-Pull Script
    Called by Windows Task Scheduler every N minutes.
    Checks if origin/main has new commits and pulls if so.

.DESCRIPTION
    This script is designed to run silently via Task Scheduler.
    It only pulls when there are actual new commits (no unnecessary pulls).
    All activity is logged to a local log file.

.PARAMETER RepoPath
    Path to the local git repo. Defaults based on hostname.

.EXAMPLE
    # From repo root (auto-detects repo):
    .\scripts\auto-pull.ps1

    # Override path:
    .\scripts\auto-pull.ps1 -RepoPath "C:\Users\Espen\elite-trading-system"

    # Installed by setup-auto-sync.ps1 as a scheduled task
#>

param(
    [string]$RepoPath = "",
    [string]$Branch   = "main",
    [string]$LogFile  = "$env:TEMP\embodier-auto-sync.log"
)

# Auto-detect repo path: script in scripts/ => parent is repo root; else use hostname or env
if (-not $RepoPath) {
    $scriptDir = $PSScriptRoot
    if ($scriptDir) {
        $maybeRepo = Split-Path -Parent $scriptDir
        if (Test-Path (Join-Path $maybeRepo ".git")) {
            $RepoPath = $maybeRepo
        }
    }
    if (-not $RepoPath) {
        $hostname = $env:COMPUTERNAME
        switch ($hostname) {
            "ESPENMAIN"    { $RepoPath = "C:\Users\Espen\elite-trading-system" }
            "PROFITTRADER" { $RepoPath = "C:\Users\ProfitTrader\elite-trading-system" }
            default        { $RepoPath = if ($env:REPO_ROOT) { $env:REPO_ROOT } else { "$env:USERPROFILE\elite-trading-system" } }
        }
    }
}

# ---- Logging helper ----
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] [$Level] [$env:COMPUTERNAME] $Message"
    Add-Content -Path $LogFile -Value $entry -ErrorAction SilentlyContinue
    if ($Level -eq "ERROR") {
        Write-Error $Message
    } else {
        Write-Output $Message
    }
}

# ---- Validate ----
if (-not (Test-Path (Join-Path $RepoPath ".git"))) {
    Write-Log "Not a git repo: $RepoPath" "ERROR"
    exit 1
}

try {
    Set-Location $RepoPath

    # Stash any local changes to avoid pull conflicts
    $status = git status --porcelain 2>&1
    $hadChanges = $false
    if ($status) {
        Write-Log "Local changes detected, stashing..."
        git stash push -m "auto-sync-stash-$(Get-Date -Format 'yyyyMMdd-HHmmss')" 2>&1 | Out-Null
        $hadChanges = $true
    }

    # Fetch latest from origin
    git fetch origin $Branch 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "git fetch failed (exit code $LASTEXITCODE)" "ERROR"
        if ($hadChanges) { git stash pop 2>&1 | Out-Null }
        exit 1
    }

    # Check how many commits we're behind
    $behind = git rev-list HEAD.."origin/$Branch" --count 2>&1
    $behind = [int]$behind

    if ($behind -gt 0) {
        # Pull the new commits
        $pullOutput = git pull origin $Branch 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Pulled $behind new commit(s) from origin/$Branch"
            Write-Log "  $pullOutput"

            # Re-install pip deps if requirements.txt changed
            $changedFiles = git diff --name-only HEAD~$behind HEAD 2>&1
            if ($changedFiles -match "requirements\.txt") {
                Write-Log "requirements.txt changed - updating pip packages..."
                $venvPip = Join-Path $RepoPath "backend\.venv\Scripts\pip.exe"
                if (Test-Path $venvPip) {
                    & $venvPip install -r (Join-Path $RepoPath "backend\requirements.txt") --quiet 2>&1 | Out-Null
                    Write-Log "pip install complete"
                }
            }

            # Re-install npm deps if package.json changed
            if ($changedFiles -match "frontend-v2/package\.json") {
                Write-Log "package.json changed - updating npm packages..."
                $npmDir = Join-Path $RepoPath "frontend-v2"
                if (Test-Path (Join-Path $npmDir "package.json")) {
                    Push-Location $npmDir
                    npm install --silent 2>&1 | Out-Null
                    Pop-Location
                    Write-Log "npm install complete"
                }
            }
        } else {
            Write-Log "git pull failed (exit code $LASTEXITCODE): $pullOutput" "ERROR"
        }
    }
    # If behind is 0, do nothing (no new commits) - silent

    # Restore stashed changes if any
    if ($hadChanges) {
        git stash pop 2>&1 | Out-Null
        Write-Log "Restored stashed local changes"
    }

} catch {
    Write-Log "Exception: $($_.Exception.Message)" "ERROR"
    exit 1
}

# Trim log file if > 1MB
if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length -gt 1MB)) {
    $lines = Get-Content $LogFile -Tail 500
    Set-Content -Path $LogFile -Value $lines
    Write-Log "Log trimmed to last 500 lines"
}
