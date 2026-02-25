#!/bin/bash
# migrate_openclaw.sh - Phase 1: Copy + Namespace OpenClaw into Elite Trading System
# Usage: Run from elite-trading-system root after cloning openclaw as sibling
#   git clone https://github.com/Espenator/openclaw.git ../openclaw
#   git checkout feat/absorb-openclaw
#   bash scripts/migrate_openclaw.sh
#
# See: https://github.com/Espenator/elite-trading-system/issues/6

set -euo pipefail

OPENCLAW_DIR="${1:-../openclaw}"
TARGET="backend/app/modules/openclaw"

if [ ! -d "$OPENCLAW_DIR" ]; then
  echo "ERROR: OpenClaw repo not found at $OPENCLAW_DIR"
  echo "Clone it first: git clone https://github.com/Espenator/openclaw.git $OPENCLAW_DIR"
  exit 1
fi

echo "=== Phase 1: Absorb OpenClaw into Elite Trading System ==="
echo "Source: $OPENCLAW_DIR"
echo "Target: $TARGET"
echo ""

# --- Create sub-package directories ---
echo "[1/7] Creating directory structure..."
mkdir -p "$TARGET/scanner"
mkdir -p "$TARGET/scorer"
mkdir -p "$TARGET/execution"
mkdir -p "$TARGET/streaming"
mkdir -p "$TARGET/intelligence"
mkdir -p "$TARGET/integrations"
mkdir -p "$TARGET/clawbots/meta_agent_alchemist"
mkdir -p "$TARGET/world_intel"
mkdir -p "$TARGET/pine"
mkdir -p "$TARGET/docs"

# --- Copy scanner files (Tier 1 Data) ---
echo "[2/7] Copying scanner modules..."
cp "$OPENCLAW_DIR/daily_scanner.py"     "$TARGET/scanner/"
cp "$OPENCLAW_DIR/finviz_scanner.py"    "$TARGET/scanner/"
cp "$OPENCLAW_DIR/whale_flow.py"        "$TARGET/scanner/"
cp "$OPENCLAW_DIR/short_detector.py"    "$TARGET/scanner/"
cp "$OPENCLAW_DIR/pullback_detector.py" "$TARGET/scanner/"
cp "$OPENCLAW_DIR/rebound_detector.py"  "$TARGET/scanner/"
cp "$OPENCLAW_DIR/amd_detector.py"      "$TARGET/scanner/"
cp "$OPENCLAW_DIR/earnings_calendar.py" "$TARGET/scanner/"
cp "$OPENCLAW_DIR/technical_checker.py" "$TARGET/scanner/"
cp "$OPENCLAW_DIR/fom_expected_moves.py" "$TARGET/scanner/"
cp "$OPENCLAW_DIR/sector_rotation.py"   "$TARGET/scanner/"
cp "$OPENCLAW_DIR/tradingview_watchlist.py" "$TARGET/scanner/"
cp "$OPENCLAW_DIR/tv_session_refresh.py" "$TARGET/scanner/"
cp "$OPENCLAW_DIR/uw_agents.py"         "$TARGET/scanner/"

# --- Copy scorer files (Tier 2) ---
echo "[3/7] Copying scorer modules..."
cp "$OPENCLAW_DIR/composite_scorer.py"  "$TARGET/scorer/"
cp "$OPENCLAW_DIR/ensemble_scorer.py"   "$TARGET/scorer/"
cp "$OPENCLAW_DIR/dynamic_weights.py"   "$TARGET/scorer/"

# --- Copy execution files (Tier 3) ---
echo "[4/7] Copying execution modules..."
cp "$OPENCLAW_DIR/auto_executor.py"     "$TARGET/execution/"
cp "$OPENCLAW_DIR/risk_governor.py"     "$TARGET/execution/"
cp "$OPENCLAW_DIR/position_sizer.py"    "$TARGET/execution/"
cp "$OPENCLAW_DIR/position_manager.py"  "$TARGET/execution/"
cp "$OPENCLAW_DIR/smart_entry.py"       "$TARGET/execution/"

# --- Copy streaming files ---
echo "[5/7] Copying streaming + intelligence modules..."
cp "$OPENCLAW_DIR/streaming_engine.py"  "$TARGET/streaming/"
cp "$OPENCLAW_DIR/session_monitor.py"   "$TARGET/streaming/"
cp "$OPENCLAW_DIR/live_dashboard.py"    "$TARGET/streaming/"

# --- Copy intelligence files ---
cp "$OPENCLAW_DIR/regime.py"            "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/hmm_regime.py"        "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/macro_context.py"     "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/mtf_alignment.py"     "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/sector_rotation.py"   "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/memory.py"            "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/memory_v3.py"         "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/llm_client.py"        "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/lora_trainer.py"      "$TARGET/intelligence/"
cp "$OPENCLAW_DIR/performance_tracker.py" "$TARGET/intelligence/"

# --- Copy integration files ---
cp "$OPENCLAW_DIR/alpaca_client.py"     "$TARGET/integrations/"
cp "$OPENCLAW_DIR/discord_listener.py"  "$TARGET/integrations/"
cp "$OPENCLAW_DIR/signal_parser.py"     "$TARGET/integrations/"
cp "$OPENCLAW_DIR/sheets_logger.py"     "$TARGET/integrations/"
cp "$OPENCLAW_DIR/bridge_sender.py"     "$TARGET/integrations/"
cp "$OPENCLAW_DIR/api_data_bridge.py"   "$TARGET/integrations/"
cp "$OPENCLAW_DIR/lstm_bridge_service.py" "$TARGET/integrations/"
cp "$OPENCLAW_DIR/db_logger.py"         "$TARGET/integrations/"

# --- Copy core files ---
cp "$OPENCLAW_DIR/config.py"            "$TARGET/"
cp "$OPENCLAW_DIR/app.py"              "$TARGET/"
cp "$OPENCLAW_DIR/main.py"             "$TARGET/"

# --- Copy clawbots ---
echo "[6/7] Copying clawbots + world_intel + pine..."
cp -r "$OPENCLAW_DIR/clawbots/"*       "$TARGET/clawbots/"
cp -r "$OPENCLAW_DIR/world_intel/"*    "$TARGET/world_intel/"
cp -r "$OPENCLAW_DIR/pine/"*           "$TARGET/pine/"

# --- Copy docs (.md files) ---
for md in "$OPENCLAW_DIR"/*.md; do
  [ -f "$md" ] && cp "$md" "$TARGET/docs/"
done

# --- Copy config files ---
echo "[7/7] Merging config files..."
cp "$OPENCLAW_DIR/.env.example"        "$TARGET/env.example.openclaw"
cp "$OPENCLAW_DIR/requirements.txt"    "$TARGET/requirements.openclaw.txt"

# --- Create __init__.py for all sub-packages ---
for pkg in scanner scorer execution streaming intelligence integrations; do
  cat > "$TARGET/$pkg/__init__.py" << 'EOF'
"""OpenClaw sub-package."""
EOF
done

echo ""
echo "=== Migration Complete ==="
echo "Files copied: $(find $TARGET -type f | wc -l)"
echo ""
echo "Next steps:"
echo "  1. git add backend/app/modules/openclaw/"
echo "  2. git commit -m 'feat(openclaw): Phase 1 - copy all openclaw modules #6'"
echo "  3. Run: python -c 'from app.modules.openclaw.scorer.composite_scorer import CompositeScorer; print(CompositeScorer)'"
echo "  4. Update imports (see Issue #6 Import Refactoring Map)"
echo "  5. Push and create PR"
