# build-installer.ps1 — Build Embodier Trader into an installable desktop app
# Usage: powershell -ExecutionPolicy Bypass -File build-installer.ps1
#
# This script:
#   1. Builds the React frontend (frontend-v2/dist/)
#   2. Bundles the Python backend via PyInstaller (backend/dist/embodier-backend/)
#   3. Packages everything into an Electron installer (desktop/release/)
#
# Prerequisites: Python 3.10+, Node.js 18+, pip install pyinstaller

param(
    [ValidateSet("win", "mac", "linux", "all")]
    [string]$Platform = "win"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Step($num, $msg) {
    Write-Host ""
    Write-Host "  [$num/4] $msg" -ForegroundColor Cyan
}

function Ok($msg) {
    Write-Host "        $msg" -ForegroundColor Green
}

function Fail($msg) {
    Write-Host "        $msg" -ForegroundColor Red
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER — Build Installer" -ForegroundColor DarkCyan
Write-Host "   Target: $Platform" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan

# ── Step 1: Build React frontend ──────────────────────────────
Step 1 "Building React frontend..."
Set-Location (Join-Path $Root "frontend-v2")
if (-not (Test-Path "node_modules")) {
    npm install --silent 2>$null
}
npm run build 2>&1
if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed"; exit 1 }
if (Test-Path "dist/index.html") {
    Ok "Frontend built → frontend-v2/dist/"
} else {
    Fail "Frontend build output not found"; exit 1
}

# ── Step 2: Bundle backend with PyInstaller ───────────────────
Step 2 "Bundling Python backend with PyInstaller..."
Set-Location (Join-Path $Root "backend")

$VenvPython = Join-Path $Root "backend\venv\Scripts\python.exe"
$VenvPyInstaller = Join-Path $Root "backend\venv\Scripts\pyinstaller.exe"

if (-not (Test-Path $VenvPython)) {
    Fail "Python venv not found. Run: cd backend && python -m venv venv && venv\Scripts\pip install -r requirements.txt pyinstaller"
    exit 1
}

# Ensure PyInstaller is installed
& $VenvPython -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "        Installing PyInstaller..." -ForegroundColor DarkGray
    & (Join-Path $Root "backend\venv\Scripts\pip.exe") install pyinstaller --quiet
}

& $VenvPyInstaller embodier-backend.spec --noconfirm 2>&1 | Select-Object -Last 5
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller build failed"; exit 1 }
if (Test-Path "dist/embodier-backend") {
    Ok "Backend bundled → backend/dist/embodier-backend/"
} else {
    Fail "Backend bundle output not found"; exit 1
}

# ── Step 3: Install Electron dependencies ─────────────────────
Step 3 "Preparing Electron packager..."
Set-Location (Join-Path $Root "desktop")
if (-not (Test-Path "node_modules")) {
    npm install --silent 2>$null
}
Ok "Electron dependencies ready"

# ── Step 4: Package installer ─────────────────────────────────
Step 4 "Packaging Electron installer ($Platform)..."

switch ($Platform) {
    "win"   { npm run dist:win   2>&1 | Select-Object -Last 10 }
    "mac"   { npm run dist:mac   2>&1 | Select-Object -Last 10 }
    "linux" { npm run dist:linux 2>&1 | Select-Object -Last 10 }
    "all"   { npm run dist:all   2>&1 | Select-Object -Last 10 }
}

if ($LASTEXITCODE -ne 0) { Fail "Electron packaging failed"; exit 1 }

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   BUILD COMPLETE" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Installer location: desktop/release/" -ForegroundColor White
Write-Host ""

# List built artifacts
$releaseDir = Join-Path $Root "desktop\release"
if (Test-Path $releaseDir) {
    Get-ChildItem $releaseDir -Recurse -Include *.exe, *.dmg, *.AppImage, *.deb | ForEach-Object {
        $size = [math]::Round($_.Length / 1MB, 1)
        Write-Host "    $($_.Name)  ($size MB)" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "  Run the installer to get:" -ForegroundColor DarkGray
Write-Host "    - Desktop shortcut" -ForegroundColor DarkGray
Write-Host "    - Start Menu entry" -ForegroundColor DarkGray
Write-Host "    - System tray icon" -ForegroundColor DarkGray
Write-Host "    - Auto-start backend on launch" -ForegroundColor DarkGray
Write-Host ""
