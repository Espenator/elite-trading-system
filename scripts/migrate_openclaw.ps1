# migrate_openclaw.ps1 - Phase 1: Copy + Namespace OpenClaw into Elite Trading System (Windows)
# Usage: Run from elite-trading-system root after cloning openclaw as sibling
#   git clone https://github.com/Espenator/openclaw.git ..\openclaw
#   git checkout feat/absorb-openclaw
#   .\scripts\migrate_openclaw.ps1
#
# See: https://github.com/Espenator/elite-trading-system/issues/6

$ErrorActionPreference = "Stop"

$OpenClawDir = if ($args[0]) { $args[0] } else { "..\openclaw" }
$Target = "backend\app\modules\openclaw"

if (-not (Test-Path $OpenClawDir)) {
    Write-Error "OpenClaw repo not found at $OpenClawDir. Clone it first: git clone https://github.com/Espenator/openclaw.git $OpenClawDir"
    exit 1
}

Write-Host "=== Phase 1: Absorb OpenClaw into Elite Trading System ===" -ForegroundColor Green
Write-Host "Source: $OpenClawDir"
Write-Host "Target: $Target"
Write-Host ""

# --- Create sub-package directories ---
Write-Host "[1/7] Creating directory structure..." -ForegroundColor Cyan
$dirs = @("scanner", "scorer", "execution", "streaming", "intelligence", "integrations",
          "clawbots\meta_agent_alchemist", "world_intel", "pine", "docs")
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path "$Target\$d" | Out-Null }

# --- Scanner files ---
Write-Host "[2/7] Copying scanner modules..." -ForegroundColor Cyan
$scannerFiles = @("daily_scanner.py", "finviz_scanner.py", "whale_flow.py", "short_detector.py",
    "pullback_detector.py", "rebound_detector.py", "amd_detector.py", "earnings_calendar.py",
    "technical_checker.py", "fom_expected_moves.py", "sector_rotation.py",
    "tradingview_watchlist.py", "tv_session_refresh.py", "uw_agents.py")
foreach ($f in $scannerFiles) { Copy-Item "$OpenClawDir\$f" "$Target\scanner\" }

# --- Scorer files ---
Write-Host "[3/7] Copying scorer modules..." -ForegroundColor Cyan
$scorerFiles = @("composite_scorer.py", "ensemble_scorer.py", "dynamic_weights.py")
foreach ($f in $scorerFiles) { Copy-Item "$OpenClawDir\$f" "$Target\scorer\" }

# --- Execution files ---
Write-Host "[4/7] Copying execution modules..." -ForegroundColor Cyan
$execFiles = @("auto_executor.py", "risk_governor.py", "position_sizer.py", "position_manager.py", "smart_entry.py")
foreach ($f in $execFiles) { Copy-Item "$OpenClawDir\$f" "$Target\execution\" }

# --- Streaming + Intelligence ---
Write-Host "[5/7] Copying streaming + intelligence modules..." -ForegroundColor Cyan
$streamFiles = @("streaming_engine.py", "session_monitor.py", "live_dashboard.py")
foreach ($f in $streamFiles) { Copy-Item "$OpenClawDir\$f" "$Target\streaming\" }

$intelFiles = @("regime.py", "hmm_regime.py", "macro_context.py", "mtf_alignment.py",
    "memory.py", "memory_v3.py", "llm_client.py", "lora_trainer.py", "performance_tracker.py")
foreach ($f in $intelFiles) { Copy-Item "$OpenClawDir\$f" "$Target\intelligence\" }

# --- Integration files ---
$integFiles = @("alpaca_client.py", "discord_listener.py", "signal_parser.py", "sheets_logger.py",
    "bridge_sender.py", "api_data_bridge.py", "lstm_bridge_service.py", "db_logger.py")
foreach ($f in $integFiles) { Copy-Item "$OpenClawDir\$f" "$Target\integrations\" }

# --- Core files ---
Copy-Item "$OpenClawDir\config.py" "$Target\"
Copy-Item "$OpenClawDir\app.py"    "$Target\"
Copy-Item "$OpenClawDir\main.py"   "$Target\"

# --- Clawbots + world_intel + pine ---
Write-Host "[6/7] Copying clawbots + world_intel + pine..." -ForegroundColor Cyan
Copy-Item "$OpenClawDir\clawbots\*"    "$Target\clawbots\" -Recurse -Force
Copy-Item "$OpenClawDir\world_intel\*" "$Target\world_intel\" -Recurse -Force
Copy-Item "$OpenClawDir\pine\*"        "$Target\pine\" -Recurse -Force

# --- Copy docs ---
Get-ChildItem "$OpenClawDir\*.md" | Copy-Item -Destination "$Target\docs\"

# --- Config files ---
Write-Host "[7/7] Merging config files..." -ForegroundColor Cyan
Copy-Item "$OpenClawDir\.env.example"    "$Target\env.example.openclaw"
Copy-Item "$OpenClawDir\requirements.txt" "$Target\requirements.openclaw.txt"

# --- Create __init__.py for sub-packages ---
$subpkgs = @("scanner", "scorer", "execution", "streaming", "intelligence", "integrations")
foreach ($pkg in $subpkgs) {
    Set-Content -Path "$Target\$pkg\__init__.py" -Value '"""OpenClaw sub-package."""'
}

$fileCount = (Get-ChildItem -Path $Target -Recurse -File).Count
Write-Host ""
Write-Host "=== Migration Complete ===" -ForegroundColor Green
Write-Host "Files copied: $fileCount"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. git add backend/app/modules/openclaw/"
Write-Host "  2. git commit -m 'feat(openclaw): Phase 1 - copy all openclaw modules #6'"
Write-Host "  3. python -c 'from app.modules.openclaw.scorer.composite_scorer import CompositeScorer; print(CompositeScorer)'"
Write-Host "  4. Update imports (see Issue #6 Import Refactoring Map)"
Write-Host "  5. git push origin feat/absorb-openclaw"
