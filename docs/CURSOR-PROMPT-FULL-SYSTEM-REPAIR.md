# Cursor Prompt — Full System Repair & Verification (March 14, 2026)

> Paste this into Cursor on PC1 (ESPENMAIN). Read CLAUDE.md first.

## Current State (CONFIRMED WORKING)
- Backend: port 8000, /healthz 200 in ~1.3s, DuckDB 955K rows, 33 council agents
- Frontend: port 5174, React served instantly
- WebSocket: connected with auth token, receiving real-time data
- Alpaca stream: running, 50 symbols
- MessageBus: running, 109K+ events
- Ollama: OK, 6 models loaded
- Council: vetoing off-hours signals correctly via circuit breaker

## 3 FAILING TESTS TO FIX

### Test 1: test_main_lifespan_order_scheduler_after_duckdb
**File**: `backend/tests/test_scheduler_resilience.py:126`
**Problem**: Test searches for literal string `duckdb_store.init_schema()` in main.py source code, but the actual code uses `asyncio.to_thread(duckdb_store.init_schema)` (no trailing parens). The `source.find("duckdb_store.init_schema()")` returns -1.
**Fix**: Update the test assertion to match the actual code pattern:
```python
# Change: idx_duckdb = source.find("duckdb_store.init_schema()")
# To:     idx_duckdb = source.find("duckdb_store.init_schema")
```

### Test 2: test_bayesian_update (TestSelfAwareness)
**File**: `backend/tests/test_phase_c.py:313`
**Problem**: Test expects `win_streak == 5` after 5 wins, but gets 70. The SelfAwareness StreakTracker is accumulating streaks across test runs because it reads persisted data from DuckDB (955K rows of real data). Test needs isolation.
**Fix**: Either mock the DuckDB connection or reset the streak tracker state before the test:
```python
# Add to test setup: reset streak state so test starts clean
sa = SelfAwareness()
sa.streaks = StreakTracker()  # fresh tracker, no persisted state
```

### Test 3: test_account_positions_orders_alpaca_api
**File**: `backend/tests/test_alpaca_broker_integration_audit.py:261`
**Problem**: Test calls real Alpaca API with invalid/missing keys → 401 unauthorized. This is an integration test that requires valid API keys.
**Fix**: Skip if API keys are not configured:
```python
import pytest
api_key = os.getenv("ALPACA_API_KEY", "")
if not api_key or api_key.startswith("your-"):
    pytest.skip("Alpaca API keys not configured")
```

## REMAINING EVENT LOOP BLOCKERS TO AUDIT

PC2 identified 10 suspect services. 3 were fixed. The other 7 were clean but should be verified. Run this search to find any remaining sync DuckDB calls in async functions:

```bash
# Find sync DuckDB calls NOT wrapped in asyncio.to_thread
cd backend
grep -rn "duckdb_store\." app/services/ app/council/ app/api/ --include="*.py" | \
  grep -v "asyncio.to_thread" | grep -v "import" | grep -v "#" | grep -v "test"
```

For each hit, check if it's inside an `async def` function. If yes, wrap in `asyncio.to_thread()`.

**Known clean files** (already audited, skip these):
- correlation_radar.py ✓
- off_hours_monitor.py ✓
- session_scanner.py ✓
- market_data_agent.py ✓
- streaming_discovery.py ✓
- idea_triage.py ✓
- discovery_signal_bridge.py ✓
- position_manager.py ✓

**Already fixed**:
- health_monitor.py ✓ (SQLite call wrapped)
- regime_publisher.py ✓ (cursor moved inside to_thread)
- risk_governor.py ✓ (wrong import fixed)
- kelly_position_sizer.py ✓ (audit trail offloaded)
- order_executor.py ✓ (ATR fetch + calculate wrapped)

## WEBSOCKET VERIFICATION CHECKLIST

1. Confirm `frontend-v2/.env` has `VITE_API_AUTH_TOKEN=<matching backend token>`
2. Confirm `Dashboard.jsx` does NOT call `ws.disconnect()` on unmount (fixed)
3. Confirm WS channels receiving data:
   - `signals` — signal.generated events
   - `council` / `council_verdict` — council verdicts
   - `order` — order events
   - `market` — price updates
   - `risk` — risk metrics
   - `swarm` — discovery results
4. Open browser DevTools → Network → WS → verify messages flowing

## API ENDPOINT VERIFICATION

Test these critical endpoints respond within 2 seconds:

```bash
# Health & readiness
curl -s http://localhost:8000/healthz | jq .status
curl -s http://localhost:8000/api/v1/health | jq .
curl -s http://localhost:8000/readyz | jq .status

# Council
curl -s http://localhost:8000/api/v1/council/status | jq .agent_count
curl -s http://localhost:8000/api/v1/council/latest | jq .direction

# Signals & market
curl -s http://localhost:8000/api/v1/signals/ | jq '. | length'
curl -s http://localhost:8000/api/v1/market/regime | jq .regime

# Data sources
curl -s http://localhost:8000/api/v1/data-sources/health | jq .

# Portfolio & orders
curl -s -H "Authorization: Bearer $API_AUTH_TOKEN" \
  http://localhost:8000/api/v1/portfolio/summary | jq .

# Risk
curl -s http://localhost:8000/api/v1/risk/metrics | jq .

# System
curl -s http://localhost:8000/api/v1/system | jq .version
curl -s http://localhost:8000/api/v1/system/event-bus/status | jq .
```

## FRONTEND PAGE VERIFICATION

Visit each page and confirm it loads data (not blank/error):

| Page | URL | What to Check |
|------|-----|---------------|
| Dashboard | /dashboard | CNS vitals, performance widgets, trade activity |
| Agents | /agents | 33 agents listed with weights and stages |
| Signal Intelligence | /signal-intelligence-v3 | Active signals with scores |
| Sentiment | /sentiment | Sentiment sources and scores |
| Data Sources | /data-sources | All 10 sources with health status |
| ML Brain | /ml-brain | Model performance metrics |
| Patterns | /patterns | Technical patterns from DB |
| Backtest | /backtest | Backtesting interface |
| Performance | /performance | P&L charts and metrics |
| Market Regime | /market-regime | Current regime and probabilities |
| Trades | /trades | Positions and order history |
| Risk | /risk | Risk metrics, Monte Carlo, drawdown |
| Trade Execution | /trade-execution | Order form and execution controls |
| Settings | /settings | App configuration |

## DATA PIPELINE END-TO-END VERIFICATION

Confirm the full pipeline is flowing:

```
1. AlpacaStreamService → market_data.bar (check MessageBus stats)
2. EventDrivenSignalEngine → signal.generated (check /api/v1/signals/)
3. CouncilGate → council.verdict (check /api/v1/council/latest)
4. OrderExecutor → order.submitted (check /api/v1/orders/)
5. WebSocket bridges → frontend (check browser WS messages)
```

If any stage is broken, check:
- MessageBus topic subscribers: `GET /api/v1/system/event-bus/status`
- Service health: `GET /api/v1/health`
- Background task status: check uvicorn logs for errors

## BACKGROUND SERVICE HEALTH

These services should be running after startup:

| Service | Check | Expected |
|---------|-------|----------|
| AlpacaStreamManager | Logs show "connected" | Streaming 50 symbols |
| EventDrivenSignalEngine | /api/v1/signals/ has recent entries | Generating signals |
| CouncilGate | /api/v1/council/status shows agents | 33 agents registered |
| TurboScanner | Started after 60s delay | Scanning opportunities |
| WeightLearner | /api/v1/council/weights | 33 Bayesian weights |
| DataIngestion scheduler | Log shows "scheduler started" | Daily 4:30 AM + weekly Sunday |
| Heartbeat | WS stays connected | 30s ping/pong cycle |
| PositionManager | /api/v1/portfolio/summary | Tracking positions |

## PROACTOR FIX (Python 3.13 Windows)

If running Python 3.13 on Windows:
- Do NOT use `--reload` with uvicorn
- The ProactorEventLoop monkey-patch in main.py suppresses ConnectionResetError floods
- If you see 430+ connection reset errors in logs, the patch is working

## PC2 SYNC

After all fixes, update PC2:
```powershell
# On ProfitTrader (PC2):
cd C:\Users\ProfitTrader\elite-trading-system
git fetch origin claude/review-repo-docs-LmWVI
git checkout claude/review-repo-docs-LmWVI
git pull origin claude/review-repo-docs-LmWVI
```

## RULES
- Read CLAUDE.md section 16 for all coding rules
- No yfinance, no mock data, all frontend via useApi() hook
- DuckDB via duckdb_store only — never raw connections
- 4-space Python indentation
- Run tests after ALL changes: `cd backend && python -m pytest --tb=short -q`
- Do NOT use --reload with uvicorn
- Do NOT break the council pipeline or the 1552 passing tests
- Commit to branch `claude/review-repo-docs-LmWVI`
