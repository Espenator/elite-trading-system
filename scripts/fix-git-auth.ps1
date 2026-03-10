# fix-git-auth.ps1
# Run this in PowerShell on your Windows machine to fix GitHub push auth
# for both git CLI and Cursor IDE.
#
# Usage:
#   cd C:\Users\Espen\Dev\elite-trading-system
#   .\scripts\fix-git-auth.ps1

$ErrorActionPreference = "Stop"
$repoDir = "C:\Users\Espen\Dev\elite-trading-system"

Write-Host "`n=== Git Push Auth Fix ===" -ForegroundColor Cyan
Write-Host "This script configures GitHub authentication so both"
Write-Host "git CLI and Cursor can push to your repo.`n"

# ─── Step 1: Pick auth method ───
Write-Host "Choose authentication method:" -ForegroundColor Yellow
Write-Host "  [1] HTTPS with Personal Access Token (recommended)"
Write-Host "  [2] SSH key"
$choice = Read-Host "Enter 1 or 2"

if ($choice -eq "1") {
    # ─── HTTPS + PAT ───
    Write-Host "`n--- HTTPS + Personal Access Token ---" -ForegroundColor Green

    Write-Host "`nIf you don't have a PAT yet:"
    Write-Host "  1. Go to: https://github.com/settings/tokens"
    Write-Host "  2. Generate new token (classic)"
    Write-Host "  3. Enable the 'repo' scope"
    Write-Host "  4. Copy the token`n"

    $token = Read-Host "Paste your GitHub Personal Access Token (or press Enter to skip)"

    # Set remote to HTTPS
    Push-Location $repoDir

    if ($token) {
        # Embed token in remote URL (works instantly for CLI + Cursor)
        git remote set-url origin "https://Espenator:$token@github.com/Espenator/elite-trading-system.git"
        Write-Host "`nRemote URL updated with token." -ForegroundColor Green
        Write-Host "WARNING: Token is stored in .git/config. This is convenient but less secure." -ForegroundColor Yellow
        Write-Host "For better security, remove the token from the URL and use credential manager instead:`n"
        Write-Host "  git remote set-url origin https://github.com/Espenator/elite-trading-system.git"
        Write-Host "  git config --global credential.helper manager`n"
    }
    else {
        # No token provided - set up credential manager
        git remote set-url origin "https://github.com/Espenator/elite-trading-system.git"
        git config --global credential.helper manager
        Write-Host "`nRemote set to HTTPS. Credential Manager enabled." -ForegroundColor Green
        Write-Host "On next push, enter your GitHub username and PAT as password." -ForegroundColor Yellow
        Write-Host "Windows will remember it for future pushes (CLI + Cursor).`n"
    }

    Pop-Location
}
elseif ($choice -eq "2") {
    # ─── SSH ───
    Write-Host "`n--- SSH Key Setup ---" -ForegroundColor Green

    $keyPath = "$env:USERPROFILE\.ssh\id_ed25519"
    $pubPath = "$keyPath.pub"

    if (Test-Path $pubPath) {
        Write-Host "Existing SSH key found:" -ForegroundColor Green
        Get-Content $pubPath
    }
    else {
        Write-Host "No SSH key found. Generating one..." -ForegroundColor Yellow
        $email = Read-Host "Enter your GitHub email"
        ssh-keygen -t ed25519 -C $email -f $keyPath -N '""'
        Write-Host "`nNew SSH key generated." -ForegroundColor Green
    }

    Write-Host "`nCopy the public key below and add it to GitHub:" -ForegroundColor Yellow
    Write-Host "  https://github.com/settings/keys -> New SSH key`n"
    Get-Content $pubPath
    Write-Host ""
    Read-Host "Press Enter after you've added the key to GitHub"

    # Switch remote to SSH
    Push-Location $repoDir
    git remote set-url origin "git@github.com:Espenator/elite-trading-system.git"
    Pop-Location

    Write-Host "Remote URL switched to SSH." -ForegroundColor Green

    # Test SSH connection
    Write-Host "`nTesting SSH connection to GitHub..." -ForegroundColor Yellow
    ssh -T git@github.com 2>&1
}
else {
    Write-Host "Invalid choice. Exiting." -ForegroundColor Red
    exit 1
}

# ─── Step 2: Set git identity (if missing) ───
$userName = git config --global user.name 2>$null
$userEmail = git config --global user.email 2>$null

if (-not $userName) {
    $name = Read-Host "Enter your name for git commits"
    git config --global user.name $name
}
if (-not $userEmail) {
    $email = Read-Host "Enter your email for git commits"
    git config --global user.email $email
}

# ─── Step 3: Test push ───
Write-Host "`n=== Testing push ===" -ForegroundColor Cyan
Push-Location $repoDir

$currentBranch = git branch --show-current
Write-Host "Current branch: $currentBranch"
Write-Host "Attempting: git push -u origin $currentBranch`n"

try {
    git push -u origin $currentBranch 2>&1
    Write-Host "`nPush successful! Auth is working for git CLI and Cursor." -ForegroundColor Green
}
catch {
    Write-Host "`nPush failed. Check the error above." -ForegroundColor Red
    Write-Host "Common issues:"
    Write-Host "  - Token doesn't have 'repo' scope"
    Write-Host "  - Token is for a different GitHub account"
    Write-Host "  - SSH key not added to GitHub"
}

Pop-Location

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "Both git CLI and Cursor use the same git config,"
Write-Host "so fixing it here fixes it everywhere.`n"
