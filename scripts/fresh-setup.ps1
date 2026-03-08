<#
.SYNOPSIS
    One-shot fresh setup: pull latest code, install deps, create shortcut, and launch.
    Run this after cloning or when things are broken.

.USAGE
    Open PowerShell, cd to repo root, run:
    .\scripts\fresh-setup.ps1
#>

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "  ====================================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER — Fresh Setup & Launch" -ForegroundColor DarkCyan
Write-Host "  ====================================================" -ForegroundColor DarkCyan
Write-Host ""

# ── Step 1: Pull latest code ──
Write-Host "  [1/6] Pulling latest code from GitHub..." -ForegroundColor Cyan
git pull origin main 2>&1 | ForEach-Object { Write-Host "        $_" -ForegroundColor DarkGray }
Write-Host ""

# ── Step 2: Validate prerequisites ──
Write-Host "  [2/6] Checking prerequisites..." -ForegroundColor Cyan
$ok = $true

try {
    $pyVer = & python --version 2>&1
    Write-Host "        Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "        Python: NOT FOUND — install from https://python.org/downloads" -ForegroundColor Red
    $ok = $false
}

try {
    $nodeVer = & node --version 2>&1
    Write-Host "        Node.js: $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "        Node.js: NOT FOUND — install from https://nodejs.org" -ForegroundColor Red
    $ok = $false
}

try {
    $gitVer = & git --version 2>&1
    Write-Host "        Git: $gitVer" -ForegroundColor Green
} catch {
    Write-Host "        Git: NOT FOUND" -ForegroundColor Yellow
}

if (!$ok) {
    Write-Host ""
    Write-Host "  [ERROR] Missing prerequisites. Install them and re-run." -ForegroundColor Red
    pause
    exit 1
}
Write-Host ""

# ── Step 3: Backend setup ──
Write-Host "  [3/6] Setting up backend..." -ForegroundColor Cyan

$BackendDir = "$Root\backend"
Set-Location $BackendDir

# Create/refresh venv
if (Test-Path "venv") {
    Write-Host "        Removing old venv..." -ForegroundColor DarkGray
    Remove-Item "venv" -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "        Creating fresh Python venv..." -ForegroundColor DarkGray
python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "        [ERROR] Failed to create venv" -ForegroundColor Red
    pause
    exit 1
}

$VenvPip = "$BackendDir\venv\Scripts\pip.exe"
Write-Host "        Installing Python dependencies (this may take 1-2 minutes)..." -ForegroundColor DarkGray
& $VenvPip install --upgrade pip --quiet 2>&1 | Out-Null
& $VenvPip install -r requirements.txt 2>&1 | ForEach-Object {
    if ($_ -match "ERROR|error") { Write-Host "        $_" -ForegroundColor Red }
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "        [ERROR] pip install failed" -ForegroundColor Red
} else {
    Write-Host "        [OK] Backend dependencies installed" -ForegroundColor Green
}

# .env setup
$EnvFile = "$BackendDir\.env"
if (!(Test-Path $EnvFile)) {
    Copy-Item "$BackendDir\.env.example" $EnvFile
    Write-Host "        [IMPORTANT] Created backend\.env from template" -ForegroundColor Yellow
    Write-Host "        Edit backend\.env with your ALPACA_API_KEY and ALPACA_SECRET_KEY!" -ForegroundColor Yellow
} else {
    Write-Host "        [OK] backend\.env exists" -ForegroundColor Green
    # Check for placeholder keys
    $content = Get-Content $EnvFile -Raw
    if ($content -match "your-alpaca") {
        Write-Host "        [WARN] .env still has placeholder Alpaca keys — replace them!" -ForegroundColor Yellow
    }
}

# Generate FERNET_KEY if not set
$fernetLine = Get-Content $EnvFile | Where-Object { $_ -match "^FERNET_KEY=" }
$fernetVal = if ($fernetLine) { ($fernetLine -split "=", 2)[1].Trim() } else { "" }
if (!$fernetVal) {
    $VenvPython = "$BackendDir\venv\Scripts\python.exe"
    $fkey = & $VenvPython -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>&1
    if ($fkey -and $fkey.Length -gt 10) {
        if ($fernetLine) {
            (Get-Content $EnvFile) -replace "^FERNET_KEY=.*", "FERNET_KEY=$fkey" | Set-Content $EnvFile
        } else {
            Add-Content $EnvFile "`nFERNET_KEY=$fkey"
        }
        Write-Host "        [OK] Generated FERNET_KEY for credential encryption" -ForegroundColor Green
    }
}

# Ensure data directory exists
New-Item -ItemType Directory -Path "$BackendDir\data" -Force | Out-Null
New-Item -ItemType Directory -Path "$BackendDir\data\models" -Force | Out-Null
Write-Host ""

# ── Step 4: Frontend setup ──
Write-Host "  [4/6] Setting up frontend..." -ForegroundColor Cyan

$FrontendDir = "$Root\frontend-v2"
Set-Location $FrontendDir

if (Test-Path "node_modules") {
    Write-Host "        Removing old node_modules..." -ForegroundColor DarkGray
    Remove-Item "node_modules" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "        Running npm install (this may take 1-2 minutes)..." -ForegroundColor DarkGray
npm install 2>&1 | ForEach-Object {
    if ($_ -match "ERR!|error") { Write-Host "        $_" -ForegroundColor Red }
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "        [ERROR] npm install failed" -ForegroundColor Red
} else {
    Write-Host "        [OK] Frontend dependencies installed" -ForegroundColor Green
}
Write-Host ""

# ── Step 5: Create desktop shortcut ──
Write-Host "  [5/6] Creating desktop shortcut..." -ForegroundColor Cyan
Set-Location $Root
& "$Root\scripts\create-shortcut.ps1"
Write-Host ""

# ── Step 6: Launch! ──
Write-Host "  [6/6] Launching Embodier Trader..." -ForegroundColor Cyan
Write-Host ""
Set-Location $Root
& "$Root\start-embodier.ps1"
