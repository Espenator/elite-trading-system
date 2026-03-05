# ============================================================================
# Embodier Trader — Desktop App Build Script (Windows PowerShell)
#
# Usage:
#   .\scripts\build-desktop.ps1                    # Build for Windows
#   .\scripts\build-desktop.ps1 -SkipBackend       # Skip PyInstaller step
# ============================================================================
param(
    [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend-v2"
$DesktopDir = Join-Path $RootDir "desktop"

function Log($msg) { Write-Host "[BUILD] $msg" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "============================================================"
Write-Host "  Embodier Trader — Desktop Build (Windows)"
Write-Host "============================================================"
Write-Host ""

# ── Step 1: Backend (PyInstaller) ──────────────────────────────────────────
if (-not $SkipBackend) {
    Log "Step 1/3: Bundling Python backend with PyInstaller..."
    Set-Location $BackendDir

    # Check PyInstaller
    $pyiVersion = python -m PyInstaller --version 2>$null
    if (-not $pyiVersion) {
        Warn "PyInstaller not found — installing..."
        pip install pyinstaller
    }

    # Clean
    if (Test-Path "dist\embodier-backend") { Remove-Item -Recurse -Force "dist\embodier-backend" }
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

    # Build
    python -m PyInstaller embodier-backend.spec --noconfirm
    if (-not (Test-Path "dist\embodier-backend")) { Err "PyInstaller failed" }
    Ok "Backend bundled: dist\embodier-backend"
} else {
    Log "Step 1/3: Skipping backend build (-SkipBackend)"
}

# ── Step 2: Frontend (Vite) ────────────────────────────────────────────────
Log "Step 2/3: Building React frontend with Vite..."
Set-Location $FrontendDir

if (-not (Test-Path "node_modules")) {
    Log "Installing frontend dependencies..."
    npm install
}

npm run build
if (-not (Test-Path "dist")) { Err "Vite build failed" }
Ok "Frontend built: dist\"

# ── Step 3: Electron Package ───────────────────────────────────────────────
Log "Step 3/3: Packaging Electron app..."
Set-Location $DesktopDir

if (-not (Test-Path "node_modules")) {
    Log "Installing Electron dependencies..."
    npm install
}

npx electron-builder --win
if (-not (Test-Path "release")) { Err "electron-builder failed" }

Ok "Desktop app built!"
Write-Host ""
Write-Host "============================================================"
Write-Host "  Build artifacts in: desktop\release\"
Get-ChildItem release\ | Format-Table Name, Length -AutoSize
Write-Host "============================================================"
Write-Host ""
Ok "Build complete! Run the .exe installer from desktop\release\"
