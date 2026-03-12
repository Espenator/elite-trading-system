# set-git-remote-from-token.ps1
# Reads GitHub PAT from env GITHUB_TOKEN or file .github-token (repo root) and
# sets the git remote URL so push/pull work for both CLI and Cursor.
# Run from repo root: .\scripts\set-git-remote-from-token.ps1
# See docs/GIT-PUSH-SETUP.md and .env.example (GITHUB_TOKEN).

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot
$repoDir = if ($scriptDir -and (Test-Path (Join-Path (Split-Path -Parent $scriptDir) ".git"))) {
    Split-Path -Parent $scriptDir
} else {
    if ($env:REPO_ROOT) { $env:REPO_ROOT } else { "C:\Users\Espen\elite-trading-system" }
}

$token = $env:GITHUB_TOKEN
if (-not $token) {
    $tokenFile = Join-Path $repoDir ".github-token"
    if (Test-Path $tokenFile) {
        $token = (Get-Content $tokenFile -Raw).Trim()
    }
}

if (-not $token) {
    Write-Host "No GitHub token found." -ForegroundColor Yellow
    Write-Host "  Option 1: Set env var GITHUB_TOKEN (e.g. in .env or shell)"
    Write-Host "  Option 2: Create file .github-token in repo root with your PAT as single line"
    Write-Host "  Get a PAT: https://github.com/settings/tokens (classic, scope: repo)"
    Write-Host "  Then run this script again."
    exit 1
}

Push-Location $repoDir
try {
    $url = "https://Espenator:$token@github.com/Espenator/elite-trading-system.git"
    git remote set-url origin $url
    Write-Host "Git remote 'origin' updated with token. Push/pull should work for CLI and Cursor." -ForegroundColor Green
}
finally {
    Pop-Location
}
