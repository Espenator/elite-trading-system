#!/usr/bin/env bash
# ============================================================================
# Embodier Trader — Desktop App Build Script
#
# Builds the complete Electron desktop application:
#   1. Bundles Python backend via PyInstaller
#   2. Builds React frontend via Vite
#   3. Packages everything via electron-builder
#
# Usage:
#   ./scripts/build-desktop.sh              # Build for current platform
#   ./scripts/build-desktop.sh --win        # Build Windows installer
#   ./scripts/build-desktop.sh --mac        # Build macOS DMG
#   ./scripts/build-desktop.sh --linux      # Build Linux AppImage
#   ./scripts/build-desktop.sh --all        # Build all platforms
#   ./scripts/build-desktop.sh --skip-backend  # Skip PyInstaller (use existing)
# ============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend-v2"
DESKTOP_DIR="$ROOT_DIR/desktop"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${CYAN}[BUILD]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Parse args
TARGET=""
SKIP_BACKEND=false
for arg in "$@"; do
  case $arg in
    --win)   TARGET="--win" ;;
    --mac)   TARGET="--mac" ;;
    --linux) TARGET="--linux" ;;
    --all)   TARGET="--win --mac --linux" ;;
    --skip-backend) SKIP_BACKEND=true ;;
    *) warn "Unknown arg: $arg" ;;
  esac
done

# Default to current platform
if [ -z "$TARGET" ]; then
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) TARGET="--win" ;;
    Darwin*) TARGET="--mac" ;;
    Linux*)  TARGET="--linux" ;;
    *) err "Unknown platform" ;;
  esac
fi

echo ""
echo "============================================================"
echo "  Embodier Trader — Desktop Build"
echo "  Target: $TARGET"
echo "============================================================"
echo ""

# ── Step 1: Backend (PyInstaller) ──────────────────────────────────────────
if [ "$SKIP_BACKEND" = false ]; then
  log "Step 1/3: Bundling Python backend with PyInstaller..."

  cd "$BACKEND_DIR"

  # Check PyInstaller is installed
  if ! python -m PyInstaller --version &>/dev/null; then
    warn "PyInstaller not found — installing..."
    pip install pyinstaller
  fi

  # Clean previous build
  rm -rf build/ dist/embodier-backend/

  # Run PyInstaller
  python -m PyInstaller embodier-backend.spec --noconfirm

  if [ -d "dist/embodier-backend" ]; then
    BACKEND_SIZE=$(du -sh dist/embodier-backend | cut -f1)
    ok "Backend bundled: dist/embodier-backend ($BACKEND_SIZE)"
  else
    err "PyInstaller failed — dist/embodier-backend not found"
  fi
else
  log "Step 1/3: Skipping backend build (--skip-backend)"
  if [ ! -d "$BACKEND_DIR/dist/embodier-backend" ]; then
    warn "No existing backend bundle found at $BACKEND_DIR/dist/embodier-backend"
  fi
fi

# ── Step 2: Frontend (Vite) ────────────────────────────────────────────────
log "Step 2/3: Building React frontend with Vite..."

cd "$FRONTEND_DIR"

# Install deps if needed
if [ ! -d "node_modules" ]; then
  log "Installing frontend dependencies..."
  npm install
fi

# Build
npm run build

if [ -d "dist" ]; then
  FRONTEND_SIZE=$(du -sh dist | cut -f1)
  ok "Frontend built: dist/ ($FRONTEND_SIZE)"
else
  err "Vite build failed — dist/ not found"
fi

# ── Step 3: Electron Package ───────────────────────────────────────────────
log "Step 3/3: Packaging Electron app..."

cd "$DESKTOP_DIR"

# Install Electron deps if needed
if [ ! -d "node_modules" ]; then
  log "Installing Electron dependencies..."
  npm install
fi

# Build
npx electron-builder $TARGET

if [ -d "release" ]; then
  ok "Desktop app built!"
  echo ""
  echo "============================================================"
  echo "  Build artifacts:"
  ls -la release/ 2>/dev/null || true
  echo "============================================================"
else
  err "electron-builder failed"
fi

echo ""
ok "Build complete! Installers are in desktop/release/"
