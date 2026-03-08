# Embodier Trading Sync — Setup Guide

**Status**: Script ready, not yet deployed. Manual sync via OneDrive for now.

## What It Does
Syncs trading brain files, env configs, backtest results, and pine scripts between **ESPENMAIN** and **Profit Trader** via OneDrive every 5 minutes.

## Files
- `install-trading-sync.ps1` — One-click installer (run on BOTH PCs as Admin PowerShell)
- Creates `sync.py` in `OneDrive/Trading-Sync/` — the actual sync engine

## What Gets Synced
- `brain/` — CONTEXT.md, CLAUDE_INSTRUCTIONS.md, brain_tools.py, brain.db, journal, research, strategies, sessions, app_dev
- `env-configs/backend.env` → `elite-trading-system/backend/.env`
- `backtest-results/`, `pine-scripts/`

## How to Install (When Ready)
1. Open **Admin PowerShell** on PC #1 (ESPENMAIN)
2. Run: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force`
3. Run: `& "C:\Users\Espen\OneDrive\Trading\install-trading-sync.ps1"`
4. Repeat steps 1-3 on PC #2 (Profit Trader)
5. Verify: `python "OneDrive\Trading-Sync\sync.py" status`

## Manual Commands
```
python sync.py status   # See what's synced
python sync.py push     # Force push local → OneDrive
python sync.py pull     # Force pull OneDrive → local
python sync.py auto     # Smart bidirectional sync
python sync.py daemon   # Run continuously (every 5 min)
```

## Known Issue
Auto-scheduled task didn't work reliably. Options to revisit:
- Try running `sync.py daemon` manually in a terminal instead of Task Scheduler
- Or use a simple `.bat` file in Windows Startup folder
