#!/bin/bash
# Embodier Trader — One-click launcher (Linux/macOS)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$SCRIPT_DIR/desktop"

echo ""
echo "  =============================="
echo "   Embodier Trader - Launching"
echo "  =============================="
echo ""

cd "$DESKTOP_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing Electron dependencies (first run)..."
    npm install
fi

# Launch Electron app
echo "Starting Embodier Trader..."
npm start
