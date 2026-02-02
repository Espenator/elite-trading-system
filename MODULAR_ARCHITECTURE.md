# Modular Architecture — Elite Trading System

**Vision**: Local PC(s) running 24/7, crunching data and scanning social/news for signals. AI uses memory, learns from data, and improves over time. Automated algo execution (paper first, then live) with a **glass-box UI**: transparent, compartmentalized, with manual controls so you can see what’s happening and add tech/AI/ML over time.

---

## 1. Design Principles

| Principle | Meaning |
|-----------|--------|
| **Modular** | Each major capability is a separate component with clear inputs/outputs. You can replace or upgrade one without rewriting the rest. |
| **Glass box** | UI and APIs expose what each module is doing: status, last run, data flow, overrides. No black boxes. |
| **Paper first** | All execution goes through Alpaca paper trading until you explicitly enable live. No accidental real money. |
| **Extensible** | New data sources, ML models, or strategies plug in as new modules or sub-components. |
| **Local-first** | Heavy compute (scanning, ML, pattern matching) runs on your machine; only execution and market data hit external APIs. |

---

## 2. High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GLASS-BOX UI                                     │
│  Dashboard | Signals | Chart Patterns | Social/News | ML Insights | Execution │
│  Manual: Start/Stop Scanners, Override Signals, Paper/Live Toggle, Limits    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│  1. SYMBOL UNIVERSE   │ │  2. SOCIAL/NEWS       │ │  3. CHART PATTERNS     │
│  (Stock/Symbol DB)    │ │  ENGINE               │ │  (Pattern DB + Scan)  │
│                       │ │                       │ │                       │
│  • Watchlists         │ │  • Real-time search   │ │  • Pattern library     │
│  • Screener results   │ │  • Sentiment/compute  │ │  • Detection pipeline  │
│  • Metadata (sector,  │ │  • Correlations      │ │  • Visual/store        │
│    liquidity, etc.)   │ │  • Signal extraction  │ │    pattern DB          │
└───────────┬───────────┘ └───────────┬───────────┘ └───────────┬───────────┘
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      ▼
            ┌─────────────────────────────────────────────────┐
            │  4. ML / ALGORITHMS ENGINE                        │
            │                                                   │
            │  • Memory & learning (e.g. River, XGBoost, etc.)  │
            │  • Signal fusion from all sources                 │
            │  • Regime detection, risk scoring                 │
            │  • Improves over time from outcomes               │
            └─────────────────────────┬─────────────────────────┘
                                      ▼
            ┌─────────────────────────────────────────────────┐
            │  5. EXECUTION ENGINE                              │
            │                                                   │
            │  • Paper trading (Alpaca paper) by default       │
            │  • Live switch only when explicitly enabled       │
            │  • Order routing, risk checks, audit log          │
            └─────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Symbol Universe (Stock/Symbol Database)

**Role**: Single source of symbols the system cares about. Feeds screeners, ML, and execution.

**Responsibilities**:
- Store and refresh watchlists, screener results, and symbol metadata (sector, market cap, liquidity).
- Expose: “what symbols are we tracking?” and “metadata for symbol X”.
- Can be backed by SQLite/Postgres; initially can extend current DB or a dedicated `symbols` table.

**Data flow**:
- **In**: Screener runs (e.g. Finviz), manual watchlist edits, CSV/API imports.
- **Out**: Symbol lists and metadata to Social/News engine, Chart Patterns, and ML.

**UI**: Screener results, watchlist editor, “Symbol Universe” panel showing count and last refresh.

**Code**: `backend/app/modules/symbol_universe/`

---

### 3.2 Social / News Engine

**Role**: Real-time search and compute over social media and news for signals and correlations.

**Responsibilities**:
- Ingest/search: Twitter/X, Reddit, news APIs (e.g. NewsAPI, Benzinga), RSS, etc.
- Compute: sentiment, keyword hits, correlation with price/volume, simple signal scores.
- Store raw or aggregated results and expose “recent signals by symbol” and “trending themes”.

**Data flow**:
- **In**: Symbol list from Symbol Universe; config (keywords, sources, schedule).
- **Out**: Time-stamped signals/scores per symbol or theme → ML Engine.

**UI**: “Social/News” panel: status (running/paused), last run, top signals, manual “Run scan now”.

**Code**: `backend/app/modules/social_news_engine/`

---

### 3.3 Chart Patterns (Visual / Pattern Database)

**Role**: Define, store, and detect chart patterns; feed pattern-based signals into ML.

**Responsibilities**:
- **Pattern library**: Definitions (e.g. head & shoulders, flags, support/resistance).
- **Detection**: Pipeline that runs on OHLCV (from Alpaca/Finviz/etc.) and outputs “pattern X on symbol Y at time T”.
- **Storage**: Optional visual or structured DB of detected patterns for backtest and learning.

**Data flow**:
- **In**: Symbol list, OHLCV data, pattern definitions.
- **Out**: Detected patterns (symbol, pattern type, timeframe, confidence) → ML Engine.

**UI**: “Chart Patterns” panel: pattern list, detection on/off, last run, recent detections.

**Code**: `backend/app/modules/chart_patterns/`

---

### 3.4 ML / Algorithms Engine

**Role**: Learn from memory and data; fuse signals; produce tradeable signals and risk view.

**Responsibilities**:
- Ingest: Symbol Universe, Social/News signals, Chart Pattern detections, price/volume, outcomes (from Execution).
- Model(s): Online learning (e.g. River), offline models (e.g. XGBoost), regime detection, risk scoring.
- Output: Signal scores per symbol, regime, “sit out” flags (e.g. earnings, FOMC), and optional position sizing.

**Data flow**:
- **In**: All other modules + execution history (fills, PnL).
- **Out**: Signals and risk state → Execution Engine; human-readable insights → UI (ML Insights panel).

**UI**: ML Insights panel, model status, feature importance, recent predictions, manual “Retrain” or “Reset”.

**Code**: `backend/app/modules/ml_engine/`

---

### 3.5 Execution Engine

**Role**: Execute algo orders in real time with strict paper-first default and full audit.

**Responsibilities**:
- **Paper by default**: Use Alpaca paper API; no real money until you explicitly enable live.
- **Live switch**: Single setting (e.g. `TRADING_MODE=live` + live Alpaca keys); clearly visible in UI.
- Order placement, cancellation, risk checks (size, exposure, daily loss), and audit log (every order + reason).

**Data flow**:
- **In**: Signals and risk from ML Engine; symbol list; user overrides (disable symbol, reduce size).
- **Out**: Orders to Alpaca (paper or live); fill/status updates back to DB and ML (for learning).

**UI**: Execution panel, order history, “Paper / Live” indicator, manual override controls.

**Code**: Wraps current `alpaca_service` and order API; lives under `backend/app/modules/execution_engine/` or remains in `services/` with a thin execution-orchestration layer that respects TRADING_MODE.

---

## 4. Paper vs Live Trading

- **Default**: `TRADING_MODE=paper` and Alpaca base URL = `https://paper-api.alpaca.markets`.
- **Live**: Set `TRADING_MODE=live` and use live Alpaca base URL (and live keys). Only change when you’re ready.
- **UI**: Always show “PAPER” or “LIVE” prominently; optional confirmation when switching to live.

Config and Alpaca client already support paper; we make mode explicit in config and UI.

---

## 5. Glass-Box UI Guidelines

- **One panel per module** (or logical group): Symbol Universe, Social/News, Chart Patterns, ML Insights, Execution.
- **Status per module**: Running / Paused / Last run / Error; manual Start / Stop / “Run once” where applicable.
- **Manual controls**: Override or disable signals, set max size, pause auto-execution, switch paper/live (with guardrails).
- **Visibility**: Show recent signals, last few orders, and why something was blocked (risk, sit-out, etc.).

Existing pieces (Dashboard, Signals, Risk Shield, ML Insights, Execution) map onto these modules; new panels can be added as you add modules.

---

## 6. Adding New Tech / AI / ML

- **New data source**: Implement as a sub-component (e.g. under `social_news_engine` or new module); expose a small interface (e.g. “list of (symbol, score, metadata)”) and feed into ML Engine.
- **New model**: Add under `ml_engine` (new model class or config); fuse its output with existing signals in one place before Execution.
- **New pattern**: Add to Chart Patterns library and detection pipeline; output format stays the same so ML doesn’t need to change.

Keep **interfaces between modules stable** (e.g. “signals with symbol, score, source”) so you can swap implementations without rewriting the rest.

---

## 7. Current Codebase Mapping

| Component        | Current location / note                          | Target module              |
|-----------------|----------------------------------------------------|----------------------------|
| Symbol list     | Finviz screener, stocks API                        | `modules/symbol_universe`  |
| Social/News     | Not yet                                             | `modules/social_news_engine` |
| Chart patterns  | Not yet                                             | `modules/chart_patterns`   |
| ML              | Referenced in docs (River, etc.); no code yet      | `modules/ml_engine`        |
| Execution       | `services/alpaca_service`, `api/v1/orders`, DB     | `modules/execution_engine` or keep services + mode |

---

## 8. Next Steps (Suggested Order)

1. **Make paper/live explicit**: Add `TRADING_MODE` to config; wire Alpaca base URL to it; show mode in API and UI.
2. **Create module skeletons**: Add `backend/app/modules/` with `symbol_universe`, `social_news_engine`, `chart_patterns`, `ml_engine`, `execution_engine` (stubs + README per module).
3. **System status API**: e.g. `GET /api/v1/system/status` returning mode, module statuses, last runs — for glass-box UI.
4. **Move/refactor incrementally**: e.g. symbol list and screener behind Symbol Universe; Alpaca + orders behind Execution Engine; then add Social/News and Chart Patterns when you’re ready.
5. **Add one pipeline end-to-end**: e.g. Screener → Symbol Universe → ML (stub) → Execution (paper) so one signal flows through; then add real ML and more modules.

This gives you a clear modular system design, paper-first execution, and a path to 24/7 local crunching with a glass-box UI you can extend with more AI and ML over time.
