# Signal Pipeline End-to-End Audit

**Date**: March 13, 2026  
**Scope**: Full chain from AlpacaStream → MessageBus → SignalEngine → CouncilGate → 35-agent DAG → Arbiter → OrderExecutor → WebSocket → Frontend  
**Version**: v5.0.0 (Embodier Trader)

---

## 1. Executive Summary

The signal pipeline is **wired end-to-end** and operates as designed. All critical links are present: market data is published to the MessageBus, the EventDrivenSignalEngine subscribes and emits `signal.generated`, CouncilGate invokes the full 35-agent council and publishes `council.verdict`, and OrderExecutor submits orders and publishes `order.submitted`. WebSocket bridges forward events to the frontend.

**Findings**:
- **Verified**: Topic strings, subscriptions, and pipeline order are correct.
- **Verified**: Regime-adaptive thresholds are implemented in CouncilGate (55/65/75 by regime).
- **Gap**: SignalEngine uses a **fixed** threshold (65); CouncilGate’s lower BULLISH threshold (55) never sees signals in the 55–64 range because they are filtered out earlier.
- **Gap**: Council verdicts are broadcast on WebSocket channel `"council"` while the frontend TradeExecution page subscribes to `"council_verdict"` — channel name mismatch (fixed in this audit).
- **Alignment**: Feature keys used by the council (via `feature_aggregator`) and by ML scoring (via `ml_scorer` / `get_feature_cols()`) are aligned where they overlap; ML inference uses a subset that is derived consistently from bar data.

---

## 2. Pipeline Chain (Link-by-Link)

### 2.1 AlpacaStream → MessageBus `market_data.bar`

| Item | Detail |
|------|--------|
| **Publisher** | `AlpacaStreamService` (used by `AlpacaStreamManager`) |
| **Location** | `backend/app/services/alpaca_stream_service.py` (lines 286, 423), `alpaca_stream_manager.py` |
| **Topic** | `market_data.bar` |
| **Payload** | `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`; optional `_source` (e.g. `"snapshot"`) |

**Flow**:
- `AlpacaStreamManager` starts one `AlpacaStreamService` per PC role (primary/secondary).
- Bars from the Alpaca WebSocket (or snapshot fallback) are converted to a bar dict and published with `await self.message_bus.publish("market_data.bar", bar_data)`.
- Snapshot-seeded bars use `_source: "snapshot"`; the SignalEngine explicitly skips these for signal generation (price cache only).

**Status**: ✅ Verified — single canonical topic `market_data.bar`, same on both PCs.

---

### 2.2 Subscribers to `market_data.bar`

| Subscriber | Location | Purpose |
|------------|----------|---------|
| EventDrivenSignalEngine | `signal_engine.py:523` | Signal generation (bars only; skips `_source==snapshot`) |
| main.py | `main.py:675, 695` | DuckDB batched persistence; bridge to WebSocket `"market"` |
| PriceCacheService | `price_cache_service.py:27` | Price cache |
| PositionManager | `position_manager.py:89` | Position / P&amp;L updates |
| AlpacaChannelAgent | `channels/alpaca_channel_agent.py:30` | SensoryEvent normalization |
| StreamingDiscovery | `streaming_discovery.py:262` | Anomaly detection → `swarm.idea` |
| OffHoursMonitor | `off_hours_monitor.py:61` | Session / gap detection |
| Firehose AlpacaStreamingAgent | `firehose/agents/alpaca_streaming_agent.py:26` | Firehose ingest |

**Status**: ✅ Verified — EventDrivenSignalEngine is the only component that turns bars into trading signals for the council pipeline.

---

### 2.3 EventDrivenSignalEngine → `signal.generated`

| Item | Detail |
|------|--------|
| **Subscribes to** | `market_data.bar` |
| **Publishes to** | `signal.generated` |
| **Location** | `backend/app/services/signal_engine.py` |
| **Threshold** | **Fixed** `SIGNAL_THRESHOLD = 65` (class constant). No regime-adaptive logic here. |

**Logic**:
- Maintains rolling bar history per symbol (`MAX_BAR_HISTORY = 50`).
- Requires at least 5 bars before scoring.
- Computes TA composite via `_compute_composite_score(quote_rows)`; optionally blends OpenClaw 5-pillar and MLScorer (XGBoost) when available.
- Applies regime multiplier (`_regime_mult`, `_bear_regime_mult`) to final score.
- **Long**: publishes `signal.generated` when `final_score >= 65` with `direction: "buy"`.
- **Short**: independent bear score via `_compute_short_composite_score`; publishes when `bear_score >= 65` with `direction: "sell"`.

**Payload** (representative): `symbol`, `score`, `label`, `direction`, `price`, `volume`, `regime`, `regime_mult`, `bar_count`, `timestamp`, `source: "event_driven_signal_engine"`.

**Status**: ✅ Wired. ⚠️ **Gap**: Regime-adaptive gate is only in CouncilGate; SignalEngine’s fixed 65 means scores in [55, 64] are never published, so CouncilGate’s BULLISH threshold of 55 has no effect. Consider making SignalEngine’s publish threshold regime-adaptive (e.g. 55/65/75) or lowering the fixed threshold and relying on CouncilGate for regime logic.

---

### 2.4 CouncilGate → Council → `council.verdict`

| Item | Detail |
|------|--------|
| **Subscribes to** | `signal.generated` |
| **Publishes to** | `council.verdict` (single canonical publish in `council_gate.py:374`) |
| **Location** | `backend/app/council/council_gate.py` |

**Gating (in order)**:
1. **Mock guard**: Drops signals with `source` containing `"mock"`.
2. **Regime-adaptive score threshold (B1)**:
   - BULLISH / GREEN: 55  
   - RISK_ON: 58  
   - NEUTRAL / YELLOW / UNKNOWN: 65  
   - RISK_OFF: 70  
   - BEARISH / RED / CRISIS: 75  
3. **Regime-adaptive cooldown (B3)**: Per-symbol per-direction (e.g. `SYMBOL:buy`, `SYMBOL:sell`); BULLISH 30s, NEUTRAL 120s, CRISIS 300s.
4. **Concurrency**: Semaphore (default 3, burst 8 in first 30 min after open); overflow goes to priority queue (by score, cap 20).

**Council invocation**:
- `run_council(symbol, timeframe="1d", context=context)` from `app.council.runner` (no precomputed `features`; runner calls `feature_aggregator.aggregate()`).
- Global timeout 90s (env `COUNCIL_GLOBAL_TIMEOUT`).
- Verdict converted to dict, `signal_data` and `price` attached; published as `council.verdict`.

**Status**: ✅ Verified — single path from `signal.generated` to council run to `council.verdict` publish.

---

### 2.5 Council Runner (35-Agent DAG)

| Item | Detail |
|------|--------|
| **Location** | `backend/app/council/runner.py` |
| **Entry** | `run_council(symbol, timeframe, features=None, context)` |

**Features**:
- If `features is None`, calls `feature_aggregator.aggregate(symbol, timeframe)` and uses `fv.to_dict()`.
- Agents receive a dict with top-level `"features"` (e.g. `f = features.get("features", features)`).
- Stages: 1 (13) → 2 (8) → 3 (2) → 4 (1) → 5 (3) → 5.5 (3) → 6 (1) → 7 (Arbiter).
- Pre-council: Homeostasis (HALTED → hold), Circuit breaker (halt → hold).
- Arbiter produces `DecisionPacket`; CouncilGate converts to verdict dict and publishes.

**Status**: ✅ Verified — full 35-agent DAG is invoked from CouncilGate with correct feature/context flow.

---

### 2.6 OrderExecutor → `order.submitted`

| Item | Detail |
|------|--------|
| **Subscribes to** | `council.verdict` |
| **Publishes to** | `order.submitted` (and order lifecycle: filled/cancelled as applicable) |
| **Location** | `backend/app/services/order_executor.py` (subscribe 186, publish 718, 803, 921) |

**Gates**: Decision TTL 30s, mock guard, daily trade limit, cooldown, drawdown, degraded/kill switch, Kelly sizing (DuckDB stats), portfolio heat, viability, risk governor (Gate 2b/2c). All must pass before submit.

**Status**: ✅ Verified — OrderExecutor is the only consumer of `council.verdict` for execution and the canonical publisher of `order.submitted`.

---

### 2.7 WebSocket Bridges → Frontend

| MessageBus Topic | Bridge Handler | WebSocket Channel | Frontend Use |
|------------------|----------------|-------------------|--------------|
| `signal.generated` | `_bridge_signal_to_ws` | `"signals"` (see note) | — |
| `council.verdict` | `_bridge_council_to_ws` | `"council_verdict"` (fixed) | TradeExecution.jsx subscribes to `WS_CHANNELS.council_verdict` |
| `order.submitted` / `order.filled` / `order.cancelled` | `_bridge_order_to_ws` | `"order"` | TradeExecution, trade lists |
| `market_data.bar` | `_bridge_market_data_to_ws` | `"market"` | MarketRegime, TradeExecution, price updates |

**Note**: In `main.py`, the signal bridge uses `broadcast_ws("signal", ...)` (channel name `"signal"`). Frontend `WS_CHANNELS.signals` is `"signals"` (plural). So signal bridge channel is `"signal"`; if the UI subscribes to `"signals"`, it will not receive these. Consider aligning to `"signals"` or document that live signals use channel `"signal"`.

**Council channel fix**: Backend was broadcasting verdicts to channel `"council"` while TradeExecution subscribes to `"council_verdict"`. The bridge now broadcasts to `"council_verdict"` so the Trade Execution page receives verdict updates.

**Status**: ✅ Order and market bridges correct. ✅ Council verdict channel fixed to `council_verdict`. ⚠️ Signal channel name `"signal"` vs frontend `"signals"` may need alignment.

---

## 3. Topic Strings Summary

| Topic | Publisher(s) | Subscriber(s) |
|-------|--------------|---------------|
| `market_data.bar` | AlpacaStreamService (via Manager) | EventDrivenSignalEngine, main (DuckDB + WS), PriceCache, PositionManager, AlpacaChannelAgent, StreamingDiscovery, OffHoursMonitor, Firehose agent |
| `signal.generated` | EventDrivenSignalEngine, (UnifiedProfitEngine), (NewsAggregator), (MarketWideSweep), (TurboScanner) | CouncilGate, main (WS bridge, Slack), UnifiedProfitEngine |
| `council.verdict` | CouncilGate (single canonical), (webhooks.py for HITL passthrough) | OrderExecutor, main (WS bridge, Slack) |
| `order.submitted` | OrderExecutor | main (WS bridge, Slack), PositionManager |

All above topic strings are in `MessageBus.VALID_TOPICS` and are consistent across the codebase.

---

## 4. Feature Alignment: SignalEngine vs Council vs ML Training

### 4.1 Council / Feature Aggregator

- **Source**: `app.features.feature_aggregator.aggregate(symbol, timeframe)`.
- **Output**: `FeatureVector` with nested dicts: `price_features`, `volume_features`, `volatility_features`, `regime_features`, `flow_features`, `indicator_features`, `intermarket_features`, `cycle_features` → merged into a single `"features"` dict in `to_dict()`.
- **Keys** (examples): `last_close`, `return_1d`, `return_5d`, `return_20d`, `high_20d`, `low_20d`, `pct_from_20d_high`, `pct_from_20d_low`, `last_volume`, `volume_sma_20`, `volume_surge_ratio`, `atr_14`, `atr_pct`, `volatility_20d`, `ema_5`–`ema_50`, `rsi_14`, `macd`, `regime`, `regime_confidence`, etc.

### 4.2 ML Scorer (Live Inference)

- **Source**: `app.services.ml_scorer.MLScorer`; feature columns from `app.modules.ml_engine.config.get_feature_cols()` (or manifest), fallback `LEGACY_FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]`.
- **Input**: List of bar dicts from SignalEngine’s rolling history; `_extract_features(bars)` builds a vector with the same names as training (returns, MA distances, vol_5/10/20/60, vol_rel, RSI, Bollinger, ATR, etc.) and orders it by `self._feature_cols`.
- **Usage**: SignalEngine calls `ml.score(symbol, list(history))` and blends ML score with TA composite when model is loaded.

### 4.3 Alignment

- **Council**: Uses whatever keys `feature_aggregator` produces (DuckDB + live data); agents use `features.get("features", features)` and key names from the aggregator (e.g. `regime`, `rsi_14`, `return_1d`).
- **ML training**: `FeaturePipeline.get_feature_cols()` / manifest define the column set; trainer and MLScorer use the same names.
- **MLScorer at runtime**: Builds features from the same bar shape (OHLCV) as the pipeline; names and order match `_feature_cols` from config/manifest. So **signal_engine and ml_training are aligned** for the subset of features used by XGBoost; council uses a broader set from the aggregator.

**Status**: ✅ No structural mismatch. Council and ML use consistent naming and data sources for the overlapping feature set.

---

## 5. Regime-Adaptive Thresholds

| Layer | Location | Behavior |
|-------|----------|----------|
| **CouncilGate** | `council_gate.py` | Gate threshold and cooldown are regime-adaptive (55/65/75 and 30s–300s). Regime taken from `signal_data.get("regime")`. |
| **SignalEngine** | `signal_engine.py` | Regime multipliers applied to score (`_regime_mult`, `_bear_regime_mult`). **Publish threshold is fixed at 65.** |

So:
- **CouncilGate**: Regime-adaptive thresholds and cooldowns are implemented and used.
- **SignalEngine**: Only regime scaling is applied; the 65 cutoff is fixed, so CouncilGate’s 55 for BULLISH never sees 55–64 signals. Optional improvement: regime-adaptive publish threshold in SignalEngine (e.g. 55/65/75) or a single lower threshold (e.g. 55) and rely on CouncilGate for tightening.

---

## 6. Full Council Run Verification

- CouncilGate calls `run_council(symbol, timeframe="1d", context=context)` with no precomputed `features`, so the runner always calls `feature_aggregator.aggregate(symbol, "1d")`.
- Runner runs all stages (1 → 7), including Arbiter; returns `DecisionPacket`; CouncilGate maps to verdict dict and publishes `council.verdict` only when not vetoed, not hold, and execution_ready.
- OrderExecutor receives only this published `council.verdict` for execution (no bypass except when CouncilGate is disabled, in which case a fallback converts `signal.generated` to a verdict-shaped message).

**Status**: ✅ Full council run is verified as the single path from signal to verdict to execution.

---

## 7. Recommendations

1. **Council WebSocket channel**: ✅ Fixed — backend bridge now broadcasts verdicts to `"council_verdict"` so TradeExecution’s subscription receives them.
2. **Signal WebSocket channel**: Align backend and frontend — either use `"signals"` in the bridge or have the frontend subscribe to `"signal"` and document it.
3. **SignalEngine threshold**: Consider making the publish threshold regime-adaptive (e.g. 55/65/75) so CouncilGate’s BULLISH 55 threshold can receive signals in the 55–64 range; or lower the fixed threshold and keep CouncilGate as the only regime filter.
4. **E2E test**: Existing `test_e2e_pipeline.py` and `test_e2e_audit_enhancements.py` already cover signal → council → order flow; keep them and run as part of CI.

---

## 8. File Reference

| Component | File(s) |
|-----------|---------|
| MessageBus | `backend/app/core/message_bus.py` |
| AlpacaStream | `backend/app/services/alpaca_stream_service.py`, `alpaca_stream_manager.py` |
| EventDrivenSignalEngine | `backend/app/services/signal_engine.py` |
| CouncilGate | `backend/app/council/council_gate.py` |
| Council runner | `backend/app/council/runner.py` |
| Arbiter | `backend/app/council/arbiter.py` |
| OrderExecutor | `backend/app/services/order_executor.py` |
| Feature aggregator | `backend/app/features/feature_aggregator.py` |
| ML scorer | `backend/app/services/ml_scorer.py` |
| ML feature config | `backend/app/modules/ml_engine/config.py`, `feature_pipeline.py` |
| WebSocket bridges | `backend/app/main.py` (lifespan) |
| WS channel allowlist | `backend/app/websocket_manager.py` |
| Frontend WS channels | `frontend-v2/src/config/api.js` (WS_CHANNELS) |
| TradeExecution page | `frontend-v2/src/pages/TradeExecution.jsx` |

---

*End of Signal Pipeline Audit.*
