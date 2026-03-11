# ============================================================================
# Embodier Trader — Desktop App Build Script (Windows PowerShell)
#
# Usage:
#   .\scripts\build-desktop.ps1                    # Full build
#   .\scripts\build-desktop.ps1 -SkipBackend       # Skip PyInstaller step
#   .\scripts\build-desktop.ps1 -SkipFrontend      # Skip Vite build step
#   .\scripts\build-desktop.ps1 -DirOnly           # Unpacked build (faster for testing)
# ============================================================================
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$DirOnly
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

    # Build (spec file is in desktop/)
    $SpecFile = Join-Path $DesktopDir "embodier-backend.spec"
    if (-not (Test-Path $SpecFile)) { Err "Spec file not found: $SpecFile" }
    python -m PyInstaller $SpecFile --noconfirm --clean
    if (-not (Test-Path "dist\embodier-backend")) { Err "PyInstaller failed" }
    Ok "Backend bundled: dist\embodier-backend"
} else {
    Log "Step 1/3: Skipping backend build (-SkipBackend)"
}

# ── Step 2: Frontend (Vite) ────────────────────────────────────────────────
if (-not $SkipFrontend) {
    Log "Step 2/3: Building React frontend with Vite..."
    Set-Location $FrontendDir

    if (-not (Test-Path "node_modules")) {
        Log "Installing frontend dependencies..."
        npm install
    }

    npm run build
    if (-not (Test-Path "dist")) { Err "Vite build failed" }
    Ok "Frontend built: dist\"
} else {
    Log "Step 2/3: Skipping frontend build (-SkipFrontend)"
}

# ── Step 3: Electron Package ───────────────────────────────────────────────
Log "Step 3/3: Packaging Electron app..."
Set-Location $DesktopDir

if (-not (Test-Path "node_modules")) {
    Log "Installing Electron dependencies..."
    npm install
}

# Ensure assets/ has icon (electron-builder references it)
$AssetsDir = Join-Path $DesktopDir "assets"
if (-not (Test-Path $AssetsDir)) { New-Item -ItemType Directory -Path $AssetsDir -Force | Out-Null }
$SrcIcon = Join-Path $DesktopDir "icons\icon.ico"
$DstIcon = Join-Path $AssetsDir "icon.ico"
if ((Test-Path $SrcIcon) -and -not (Test-Path $DstIcon)) {
    Copy-Item $SrcIcon $DstIcon
    Log "Copied icon.ico to assets/"
}

if ($DirOnly) {
    npx electron-builder --win --dir
} else {
    npx electron-builder --win
}
if (-not (Test-Path "release")) { Err "electron-builder failed" }

Ok "Desktop app built!"
Write-Host ""
Write-Host "============================================================"
Write-Host "  Build artifacts in: desktop\release\"
Get-ChildItem release\ | Format-Table Name, Length -AutoSize
Write-Host "============================================================"
Write-Host ""
Ok "Build complete! Run the .exe installer from desktop\release\"
