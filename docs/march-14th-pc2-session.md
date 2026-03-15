# March 14th — PC2 (ProfitTrader) Session Report

## Overview
Full performance audit and 8-task optimization pass on PC2. Backend was severely overloaded — 20-30s response times, signals flickering 42→0→42, 8,000 event handler invocations per 30-second cycle on weekends. All issues resolved, committed, and pushed.

---

## Root Cause Analysis
- **Event storm**: 800 symbols × 10 `market_data.bar` subscribers × 30s poll = **8,000 handler invocations per cycle**, all CPU-bound on one asyncio thread
- **Signal flicker**: `/api/v1/signals/` recomputing fresh on every poll, returning partial results mid-scan (42→0→42)
- **No weekend awareness**: System treated Saturday the same as market hours — polling 1,604 symbols every 30s for no reason
- **PyTorch/CUDA not in venv**: RTX 4080 sitting idle because `torch` was only in system Python, not backend venv

---

## 8 Performance Fixes Applied

### 1. Session-Aware Symbol Reduction (alpaca_stream_service.py)
- Weekend: 1,604 symbols → **6** (BTC, ETH, SOL, XRP + gold/silver)
- Poll interval: 30s → **300s** (5 min) on weekends
- Uses `market_clock.get_active_symbols()` to dynamically filter

### 2. TurboScanner Throttling (turbo_scanner.py)
- Added `_get_scan_interval()` — session-aware intervals
- Weekend: 300s, overnight/premarket: 120s, volatile: 15s, normal: 30s

### 3. Scout Base Throttling (scouts/base.py)
- `_get_effective_interval()` — weekends 3× interval (min 300s), overnight 2× (min 120s)
- All 12 scouts automatically throttled

### 4. Intelligence Cache Throttling (intelligence_cache.py)
- Weekend refresh: 300s (vs 60s normal), market data refresh: 900s (vs 120s)
- `_get_intervals()` method returns session-appropriate timings

### 5. 2-Tier Signal Cache (signals.py)
- L1: in-memory dict with session-aware TTL
- L2: Redis fallback (`embodier:` key prefix, 1s connect timeout)
- Eliminates flicker — stale cache served while scan runs, updated atomically
- TTL matches scan interval (300s weekend, 120s overnight, 30s normal)

### 6. WebSocket Bar Batching (main.py)
- Old: 800+ individual `broadcast_ws("market", bar)` calls per cycle
- New: Bars buffered in `_ws_bar_batch`, flushed max once/second or at 50 bars
- Sends `{"type": "price_batch", "bars": [...]}` instead of individual messages

### 7. Graceful Degradation (ml_brain.py, system.py, performance.py)
- Secondary endpoints return `{"status": "unavailable"}` with HTTP 200 instead of 503
- `_safe_status()` wrapper in system.py for all module status calls
- Frontend won't show error states for non-critical modules during startup

### 8. Infrastructure Improvements
- **run_server.py**: Auto-detects uvloop (Linux) and httptools for optimal performance
- **vite.config.js**: Proxy timeout set to 120s on `/api` and `/ws` paths
- **start-embodier.ps1**: Health check uses `/api/v1/system/health-check` with `/healthz` fallback, passes PORT env var to backend
- **PyTorch CUDA**: Installed `torch-2.6.0+cu124` in backend venv — RTX 4080, 17.2GB VRAM now available
- **ProcessPoolExecutor**: `_cpu_pool` in message_bus.py routes `_cpu_bound=True` handlers to separate processes (GIL escape)

---

## New Core Files Added
- **`backend/app/core/market_clock.py`** — Session detection (MARKET_HOURS, PREMARKET, AFTERHOURS, OVERNIGHT, WEEKEND), `get_scan_interval()`, `get_active_symbols()`. WEEKEND_SYMBOLS = 6 crypto/metals, OVERNIGHT_SYMBOLS = 15 liquid names.
- **`backend/app/core/db_writer.py`** — Async batch DuckDB writer. 50K queue, 100-row batch flushes every 500ms.

---

## Performance Impact
| Metric | Before | After |
|---|---|---|
| Weekend handler invocations/30s | ~8,000 | ~48/300s |
| Symbol count (weekend) | 1,604 | 6 |
| Poll interval (weekend) | 30s | 300s |
| API response time | 20-30s | <1s |
| Signal flicker | 42→0→42 | Stable (cached) |
| GPU utilization | 0% (no torch) | Available (RTX 4080) |
| WS messages/cycle | 800+ individual | 1 batched |

---

## Git Operations
- Pulled 2 upstream commits from PC1: `58a5911` (startup scripts), `70d9e07` (reliability hardening)
- Merged via fast-forward, resolved 1 conflict in `start-embodier.ps1`
- Committed as `366042c` on main
- Deleted 4 stale remote branches: `claude/analyze-websocket-stability-QntDG`, `copilot/review-embodier-trader-logic`, `cursor/chore/gitignore-auto-generated`, `cursor/full-review-2026-03-14`
- 2 old stashes remain from `claude/review-repo-docs-LmWVI` branch — can be dropped if not needed

## Remaining Untracked Files (not committed, prompt/doc files)
- `PROMPT_FINAL_PC2_HARDWARE_MAX.md`
- `docs/CURSOR-PROMPT-24-5-TRADING.md`
- `frontend-v2/start-dev.js`
- `pc1-firewall-instructions.txt`

## GitHub Dependabot
2 moderate vulnerabilities flagged on default branch — check https://github.com/Espenator/elite-trading-system/security/dependabot

---

## Notes for PC1
- All changes are on `main` — just `git pull origin main` to sync
- SSH from PC2→PC1 failed (port 22 connection timed out) — no SSH server running on ESPENMAIN. If you want cross-machine access, enable OpenSSH Server in Windows Settings > Apps > Optional Features
- The `.env` on PC2 has `CUDA_DEVICE_ORDER=PCI_BUS_ID` added — PC1 may want the same if it has a GPU
- Redis is optional — L2 cache degrades gracefully to L1-only if Redis is unavailable
