# Architecture Audit: Real-Time Signal Pipeline
## Date: February 22, 2025
## Auditor: Perplexity AI (for Espen)

---

## VERDICT: Current bridge is NOT real-time. Major gaps exist.

The current Embodier Trader <-> OpenClaw integration uses a **Gist-polling bridge** with a
**15-minute cache**. This is fundamentally batch-oriented and cannot deliver instant trade signals.
Below is the full gap analysis and the action plan to fix it.

---

## 1. HOW OPENCLAW ACTUALLY WORKS (Real-Time)

OpenClaw has a fully real-time pipeline already built:

```
streaming_engine.py (Alpaca WebSocket 1-min bars)
  -> RollingIndicators (RSI, Williams %R, VWAP, ATR, SMA, volume ratio)
  -> CompositeScorer (5-pillar: regime 20pts, trend 25pts, pullback 25pts, momentum 20pts, pattern 10pts)
  -> Trigger detection (pullback_entry 75+, breakout_entry 80+, mean_reversion 70+)
  -> SIGNAL_READY event -> asyncio.Queue
  -> auto_executor.py consumes queue -> risk governor -> position sizer -> bracket order via AlpacaClient
  -> Slack alert + performance tracking
```

Key capabilities:
- Alpaca WebSocket for real-time 1-min bars (not polling)
- Continuous re-scoring on EVERY bar
- Signal triggers with entry/stop/target computed from ATR + FOM expected moves
- Bracket orders (entry + stop-loss + take-profit) via alpaca-py TradingClient
- Risk governor: daily trade limit, market hours, min score, regime-aware position sizing
- State persistence to disk for crash recovery
- Slack alerts on high-score crossings (>=80)

## 2. HOW EMBODIER TRADER v2 CURRENTLY WORKS (Batch)

```
main.py startup -> _market_data_tick_loop() every 60s
  -> market_data_agent.run_tick()
    -> Finviz (screener) -> symbol_universe
    -> Alpaca (clock check only)
    -> FRED (CPI macro)
    -> SEC EDGAR (filings)
    -> Unusual Whales (options flow)
    -> OpenClaw Bridge (Gist poll, 15-min cache)
  -> signal_engine.run_tick()
    -> get_tracked_symbols() from symbol_universe
    -> Finviz quote data (daily bars)
    -> Simple momentum/pattern score (open/close/high/low)
    -> OpenClaw regime multiplier + 60/40 blend with claw_scores
    -> Log messages returned
```

Current frontend display: WebSocket broadcasts log messages (strings), not structured signal data.

## 3. CRITICAL GAPS

### GAP 1: No Real-Time Data Stream
- **OpenClaw**: Alpaca WebSocket -> 1-min bars -> instant indicator computation
- **Embodier**: 60-second poll loop -> Finviz daily bars -> stale data
- **Impact**: Signals are 60 seconds to 15 minutes late. Cannot catch intraday momentum.

### GAP 2: No Signal Trigger System
- **OpenClaw**: 3 defined triggers (pullback_entry, breakout_entry, mean_reversion) with
  multi-condition checks (Williams %R cross, VWAP distance, volume surge, RSI oversold)
- **Embodier**: Simple momentum score (close vs open) + pattern label. No trigger conditions.
- **Impact**: No actionable BUY/SELL signals. Just a score number.

### GAP 3: No Order Execution Pipeline
- **OpenClaw**: auto_executor.py -> risk governor -> position sizer -> bracket orders via AlpacaClient
- **Embodier**: alpaca_service.py can place single orders but nothing connects signals to orders
- **Impact**: Even if a score hits 90, nothing happens. No auto-execution capability.

### GAP 4: Database Has No Signals Table
- **OpenClaw**: Persists live_scores.json and signal_queue.json to disk
- **Embodier**: database.py has `orders` table, `config` table, `alert_rules` table. No `signals` table.
- **Impact**: No historical signal tracking, no performance measurement, no learning loop.

### GAP 5: Bridge is Gist-Polling (15-min stale)
- **Current**: openclaw_bridge_service.py fetches from GitHub Gist with 15-min cache
- **OpenClaw publishes**: api_data_bridge.py writes scan results to Gist (triggered by daily_scanner)
- **Impact**: Data is from DAILY scan, not real-time streaming. The bridge reads yesterday's analysis.

### GAP 6: WebSocket Broadcasts Log Strings, Not Structured Events
- **OpenClaw**: signal_queue is asyncio.Queue of typed SIGNAL_READY dicts
- **Embodier**: websocket_manager.py broadcasts {"channel": str, "data": dict} but signal_engine
  returns List[Tuple[str, str]] (message, level) -- just log text
- **Impact**: Frontend cannot render real-time signal cards, order buttons, or live score tables.

### GAP 7: No Composite Scorer Integration
- **OpenClaw**: CompositeScorer with 5 pillars, regime-adaptive thresholds, confidence scoring,
  ScoreBreakdown dataclass with tier classification (SLAM/HIGH/TRADEABLE/WATCH)
- **Embodier**: _compute_composite_score() is a ~30-line function doing basic momentum math
- **Impact**: Scores are not comparable. OpenClaw scores are battle-tested with real backtests.

---

## 4. ACTION PLAN: Make Embodier Trader Real-Time

### Phase 1: Real-Time Streaming (Oleh - Priority 1)
Create `backend/app/services/streaming_service.py`:
- Port OpenClaw's RollingIndicators class into Embodier
- Connect to Alpaca WebSocket (StockDataStream) for 1-min bars
- Feed bars into indicators -> compute RSI, Williams %R, VWAP, volume ratio, ATR, SMA
- On each bar: score ticker -> check triggers -> emit SIGNAL_READY via WebSocket
- Use symbol_universe watchlist (from Finviz screener) as subscription list
- Persist live_scores to database (new signals table)

### Phase 2: Signals Database Table
Add to `database.py`:
```sql
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  score REAL NOT NULL,
  tier TEXT,
  entry_price REAL,
  stop_loss REAL,
  take_profit REAL,
  atr REAL,
  regime TEXT,
  indicators_json TEXT,
  status TEXT DEFAULT 'pending',
  created_at TEXT NOT NULL,
  executed_at TEXT,
  order_id TEXT
)
```

### Phase 3: Signal-to-Order Pipeline
Create `backend/app/services/execution_service.py`:
- Consume SIGNAL_READY events from streaming_service
- Risk governor checks (daily limit, market hours, regime, portfolio heat)
- Position sizing (Kelly or fixed-fraction based on score + regime)
- Place bracket orders via existing alpaca_service.py
- Log execution to signals table + WebSocket broadcast

### Phase 4: WebSocket Structured Events
Update websocket_manager.py to broadcast typed events:
```python
# Signal events
await broadcast_ws("signals", {"type": "signal_ready", "ticker": "AAPL", "score": 87, ...})
await broadcast_ws("signals", {"type": "signal_executed", "order_id": "...", ...})
# Live scores
await broadcast_ws("scores", {"type": "score_update", "scores": {...}})
```

### Phase 5: Replace Gist Bridge with Direct Integration
Instead of polling Gist every 15 minutes:
- Option A: Run OpenClaw streaming_engine as a subprocess, read its signal_queue.json
- Option B: Import OpenClaw modules directly (CompositeScorer, RollingIndicators)
- Option C: OpenClaw publishes to a shared Redis/SQLite that Embodier reads in real-time
- Recommended: Option B -- import the proven scorer into Embodier's streaming_service

---

## 5. FILE CHANGES NEEDED

| File | Action | Description |
|------|--------|-------------|
| `services/streaming_service.py` | CREATE | Real-time Alpaca WebSocket + indicators + scoring |
| `services/execution_service.py` | CREATE | Signal -> risk check -> bracket order pipeline |
| `services/database.py` | MODIFY | Add signals table + CRUD methods |
| `services/signal_engine.py` | MODIFY | Replace simple scorer with OpenClaw CompositeScorer |
| `api/v1/signals.py` | MODIFY | Add endpoints for live signals, signal history |
| `api/v1/execution.py` | CREATE | Endpoints for execution status, trade log |
| `websocket_manager.py` | MODIFY | Add typed signal/score event broadcasting |
| `main.py` | MODIFY | Start streaming_service on lifespan, add execution router |
| `core/config.py` | MODIFY | Add STREAMING_ENABLED, MAX_DAILY_TRADES, etc. |
| `requirements.txt` | MODIFY | Add alpaca-py (for WebSocket StockDataStream) |

---

## 6. PRIORITY ORDER

1. **streaming_service.py** + signals DB table (this unlocks everything)
2. **execution_service.py** (turns signals into orders)
3. **WebSocket structured events** (frontend can show live data)
4. **Replace Gist bridge** with direct CompositeScorer import
5. **Frontend signal cards** (Oleh's React UI work)

---

## 7. WHAT THE CURRENT BRIDGE IS GOOD FOR

The Gist bridge is NOT useless. It serves as:
- Daily regime overlay (market macro context)
- Candidate pre-filter (top 50 from daily scan)
- Whale flow alerts (unusual options activity)

Keep it as a supplementary data source, but it cannot be the primary signal pipeline.
The primary pipeline must be: **WebSocket bars -> indicators -> scorer -> triggers -> execution**
