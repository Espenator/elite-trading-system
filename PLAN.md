# Production Readiness Plan — Embodier Trader v4.1.0 → v5.0.0
# Goal: 100% shippable, autonomous 24/7 trading with real data firehose
# Generated: March 11, 2026

---

## Executive Summary

After auditing ALL 1,500+ lines of main.py startup, 189 frontend API endpoints,
34 backend route files, 35 council agents, and the full event pipeline, here is the
phase-by-phase plan to make Embodier Trader production-ready.

**Current state**: The architecture is MASSIVE and well-structured. 25+ services
start automatically. The pipeline (Stream → Signal → Council → Order) is wired.
The gap is: many UI controls are cosmetic, many endpoints return skeleton/mock data,
and the system needs tuning to run autonomously 24/7.

---

## Phase 1: Backend Health Audit — Verify Every Service Actually Works
**Priority: P0 | Estimated: 2-3 sessions | STATUS: COMPLETE**

### 1.1 Start the backend and capture ALL startup logs — DONE (March 11)
- **Fixed**: DiscordSwarmBridge init crash (unexpected kwargs)
- **Fixed**: SourceCategory enum missing 'llm' → pydantic 500 on /data-sources/
- **Fixed**: TurboScanner blocking event loop (10 sync DuckDB scans as async def)
  - Renamed to _sync methods, wrapped in asyncio.to_thread()
- **Fixed**: uvloop CPU spin (35-90%) — added loop='asyncio' to both server entry points
- **Fixed**: UnboundLocalError for _turbo_scanner/_market_sweep when env-gated
- **Fixed**: float('inf') in swarm/turbo/status JSON — added _sanitize_floats()
- **Added**: Env-var gates for heavy services (SCOUTS_ENABLED, TURBO_SCANNER_ENABLED, etc.)
- All 25+ services now start without errors

### 1.2 Test critical API endpoints return real data (not skeleton) — DONE (March 11)
Tested 63 endpoints: 60x 200 OK, 2x 422 (expected query params), 1x 405 (POST-only).
For each of these core endpoints, hit them and verify real data:

| Endpoint | Expected Data | What to check |
|----------|---------------|---------------|
| GET /api/v1/alpaca/account | Real Alpaca account balance | Uses ALPACA_API_KEY |
| GET /api/v1/alpaca/positions | Real open positions | From Alpaca API |
| GET /api/v1/alpaca/orders | Real order history | From Alpaca API |
| GET /api/v1/market/indices | SPY, QQQ, DIA prices | From Alpaca data API |
| GET /api/v1/portfolio | Portfolio P&L summary | From Alpaca + DuckDB |
| GET /api/v1/signals/ | Generated signals | From SignalEngine |
| GET /api/v1/council/latest | Latest council verdict | From CouncilGate |
| GET /api/v1/council/weights | Agent Bayesian weights | From WeightLearner |
| GET /api/v1/risk/risk-score | Composite risk 0-100 | From risk calcs |
| GET /api/v1/data-sources/ | All data feed health | 10+ sources |
| GET /api/v1/flywheel | ML flywheel metrics | From ML engine |
| GET /api/v1/sentiment | Aggregated sentiment | From 4 sources |
| GET /api/v1/openclaw/regime | Market regime state | From HMM model |
| GET /api/v1/openclaw/macro | Macro indicators | VIX, HY, F&G |
| GET /api/v1/cns/homeostasis/vitals | System vitals | From Homeostasis |
| GET /api/v1/swarm/turbo/status | TurboScanner status | From scanner |
| GET /api/v1/swarm/hyper/status | HyperSwarm status | From swarm |
| GET /health | Full system health | Pipeline + DuckDB |

### 1.3 Identify and fix endpoints returning mock/skeleton data — DONE (March 11)
- **Fixed**: logs.py — replaced 8 hardcoded fake log entries with real Python logging
  ring buffer (RingBufferHandler in logging_config.py captures last 500 records)
- **Fixed**: backtest_routes.py /runs — replaced fake R001-R004 with real DB query
- **Fixed**: agents.py — removed _DEFAULT_LOGS mock activity entries and fake
  lastAction/currentTask strings; now shows honest "Awaiting first tick" until real ticks run
- **Kept**: agents.py template structure (5 agent definitions) — valid, overlaid with
  real psutil metrics and persisted DB status. Not mock data, just agent registry.
- **Kept**: backtest analysis endpoints (results, optimization, etc.) — return empty
  structures when no backtests have been run. Honest empty, not fake data.
- **Verified clean**: portfolio.py, risk endpoints, market endpoints, alpaca endpoints
  all return real data from actual services

---

## Phase 2: Frontend ↔ Backend Wiring — Every Page Shows Real Data
**Priority: P0 | Estimated: 3-5 sessions | STATUS: IN PROGRESS**

### 2.0 Endpoint Wiring Audit — DONE (March 11)
- Tested all 63 backend endpoints: 60x 200, 2x 422 (expected), 1x 405 (expected)
- Frontend build: SUCCESS (all 14 pages compile, no errors)
- Vite proxy: correctly routes /api → backend:8000, /ws → WebSocket
- useApi hook: solid with dedup, concurrency limiting, stale-while-revalidate
- **Added 5 missing endpoints** that frontend expected but backend lacked:
  - PUT /strategy/regime-params (Market Regime page save)
  - POST /training/retrain (Signal Intelligence retrain button)
  - POST /openclaw/scan (manual scan trigger)
  - PUT /agents/{id}/weight (agent/scanner/intel weight slider)
  - POST /agents/{id}/toggle (agent/scanner/intel on/off toggle)
- Added `scanners` and `intels` aliases in api.js → agents router
- Set API_AUTH_TOKEN in .env (required for POST/PUT/DELETE endpoints)


### 2.1 Dashboard (Dashboard.jsx → /dashboard)
API calls: market/indices, portfolio, signals, performance/equity, performance/trades, signals/heatmap
- [ ] Verify market indices ticker bar shows real SPY/QQQ/DIA/VIX prices
- [ ] Verify portfolio summary (balance, P&L, positions) is from Alpaca
- [ ] Verify equity curve sparkline uses real DuckDB trade data
- [ ] Verify signal feed shows real-time signals from SignalEngine
- [ ] Verify WebSocket "market" channel pushes live price updates

### 2.2 Agent Command Center (AgentCommandCenter.jsx → /agents)
API calls: agents, agents/swarm-topology, agents/consensus, agents/conference,
agents/teams, agents/drift, agents/alerts, agents/resources, agents/hitl/buffer,
agents/hitl/stats, agents/attribution, agents/elo-leaderboard, agents/ws-channels,
agents/flow-anomalies, agents/all-config, system/event-bus/status
- [ ] Tab 1 (Swarm Overview): 35 agents with real status, health, vote history
- [ ] Tab 2 (Registry): Real agent config from agent_config.py
- [ ] Tab 3 (Spawn & Scale): Real task spawner status
- [ ] Tab 4 (Live Wiring): Real WebSocket channel subscription counts
- [ ] Tab 5 (Blackboard): Real blackboard state from BlackboardState
- [ ] Tab 9 (Brain Map): Real agent DAG visualization
- [ ] Tab 10 (Node Control): Real HITL gate buffer, override history
- [ ] All "Start/Stop/Pause" buttons → wire to real agent lifecycle
- [ ] ELO leaderboard → wire to real WeightLearner Bayesian scores

### 2.3 Signal Intelligence (SignalIntelligenceV3.jsx → /signal-intelligence-v3)
API calls: signals, signals/heatmap, signals/kelly-ranked, council/latest
- [ ] Signal table shows real signals from EventDrivenSignalEngine
- [ ] Kelly-ranked opportunities use real DuckDB trade stats
- [ ] Council verdict panel shows real 35-agent vote breakdown
- [ ] "Send to Council" button triggers real POST /council/evaluate

### 2.4 Sentiment Intelligence (SentimentIntelligence.jsx → /sentiment)
API calls: sentiment, openclaw/whale-flow
- [ ] Social sentiment from real sources (News, UW, social)
- [ ] Whale flow alerts from Unusual Whales API
- [ ] Heatmap/scanner matrix with real data

### 2.5 Data Sources Monitor (DataSourcesMonitor.jsx → /data-sources)
API calls: data-sources/
- [ ] Each of 10+ data sources shows real health (connected/degraded/failed)
- [ ] Last update timestamps are real
- [ ] Refresh buttons actually trigger re-checks

### 2.6 ML Brain & Flywheel (MLBrainFlywheel.jsx → /ml-brain)
API calls: ml-brain/, ml-brain/models, flywheel, flywheel/scheduler,
flywheel/kpis, flywheel/performance, flywheel/signals/staged,
flywheel/models, flywheel/logs, flywheel/features
- [ ] Model registry shows real XGBoost models with accuracy
- [ ] Flywheel metrics (accuracy over time) from real DuckDB data
- [ ] Feature importance chart from real feature pipeline
- [ ] "Retrain" button triggers real ML training job

### 2.7 Screener & Patterns (Patterns.jsx → /patterns)
API calls: patterns, stocks
- [ ] Pattern detections from real DuckDB queries
- [ ] Stock screener from real Finviz/TurboScanner results
- [ ] Filter controls actually modify queries

### 2.8 Backtesting Lab (Backtesting.jsx → /backtest)
API calls: backtest/, backtest/runs, backtest/results, backtest/optimization,
backtest/walkforward, backtest/montecarlo, backtest/regime,
backtest/rolling-sharpe, backtest/trade-distribution, backtest/kelly-comparison,
backtest/correlation, backtest/sector-exposure, backtest/drawdown-analysis
- [ ] "Run Backtest" button triggers real backtesting engine
- [ ] Results show real equity curves, drawdown analysis
- [ ] Monte Carlo uses real simulation (not mock)
- [ ] Walk-forward validation actually runs

### 2.9 Performance Analytics (PerformanceAnalytics.jsx → /performance)
API calls: performance, performance/equity, performance/trades
- [ ] Equity curve from real trade history in DuckDB
- [ ] Win rate, Sharpe, Sortino from real calculations
- [ ] Monthly P&L heatmap from real data
- [ ] Trade distribution histogram from real trades

### 2.10 Market Regime (MarketRegime.jsx → /market-regime)
API calls: openclaw/regime, openclaw/macro, strategy/regime-params,
backtest/regime, openclaw/sectors, openclaw/scan, openclaw/memory,
risk/risk-gauges, openclaw/health, openclaw/whale-flow,
openclaw/regime/transitions
- [ ] Regime state (GREEN/YELLOW/RED) from real HMM model
- [ ] VIX, HY spread, Fear & Greed from real data
- [ ] Sector rotation from real Finviz data
- [ ] Override controls actually modify regime behavior

### 2.11 Active Trades (Trades.jsx → /trades)
API calls: alpaca/positions, alpaca/orders, alpaca/activities
- [ ] Open positions from real Alpaca account
- [ ] Order history from real Alpaca orders
- [ ] P&L calculations are real-time

### 2.12 Risk Intelligence (RiskIntelligence.jsx → /risk)
API calls: risk, risk/risk-score, risk/kelly-sizer, risk/position-sizing,
risk/drawdown-check, risk/dynamic-stop-loss, risk/risk-gauges,
risk-shield, strategy/pre-trade-check
- [ ] Risk score 0-100 from real portfolio analysis
- [ ] Kelly sizer uses real DuckDB trade statistics
- [ ] Drawdown check uses real Alpaca equity history
- [ ] Risk shield emergency controls actually work
- [ ] Pre-trade check runs real 6-point validation

### 2.13 Trade Execution (TradeExecution.jsx → /trade-execution)
API calls: alpaca/account, alpaca/positions, alpaca/orders,
orders/advanced, council/latest, strategy/pre-trade-check
- [ ] Account balance/buying power from real Alpaca
- [ ] Order submission creates real Alpaca paper orders
- [ ] Bracket/OCO/OTO order types work
- [ ] Pre-trade checks gate real orders
- [ ] Council verdict shown before execution

### 2.14 Settings (Settings.jsx → /settings)
API calls: settings
- [ ] Settings load from backend storage
- [ ] Settings save persists to backend
- [ ] Toggle controls actually change system behavior

---

## Phase 3: Council Agents — Real Data, No Fallbacks
**Priority: P1 | Estimated: 2-3 sessions**

### 3.1 Audit each of 35 agents for real data usage
Most agents have try/except blocks that return neutral AgentVote on any error.
This means they silently fail and vote HOLD with 0.5 confidence. Need to verify
each agent actually gets data from its source:

| Agent | Data Source | What to verify |
|-------|------------|----------------|
| market_perception | Alpaca bars | Gets real OHLCV from DuckDB |
| flow_perception | Unusual Whales | Gets real options flow |
| regime | DuckDB features | Gets real regime classification |
| social_perception | News/Social APIs | Gets real sentiment scores |
| news_catalyst | NewsAPI | Gets real headlines |
| youtube_knowledge | YouTube API | Not configured — needs decision |
| hypothesis | Brain gRPC/Ollama | Gets real LLM hypothesis |
| strategy | DuckDB features | Gets real strategy signals |
| risk | Alpaca + DuckDB | Gets real portfolio risk |
| execution | Alpaca | Gets real liquidity data |
| critic | DuckDB outcomes | Gets real trade history |
| gex_agent | UW/CBOE | Gets real GEX data |
| insider_agent | SEC EDGAR | Gets real Form 4 filings |
| earnings_tone_agent | Earnings calls | May need data source |
| finbert_sentiment | News text | Gets real news for NLP |
| supply_chain_agent | Graph data | May use static mapping |
| institutional_flow | 13F filings | May need data source |
| congressional_agent | Congressional data | Gets from UW |
| dark_pool_agent | DIX data | Gets from UW |
| portfolio_optimizer | DuckDB positions | Gets real portfolio |
| layered_memory | MemoryBank | Gets real memory |
| alt_data_agent | Alt data sources | May be stubbed |
| macro_regime_agent | FRED + VIX | Gets real macro data |
| 6 supplemental | DuckDB features | Verify real feature data |
| 3 debate agents | Other agent votes | Get real stage 1-5 votes |

### 3.2 Fix agents returning neutral votes due to missing data
- Add fallback data fetching (direct API calls if MessageBus data is stale)
- Add logging when agents fall back to neutral (don't silently degrade)
- Set up health monitoring for agent data freshness

---

## Phase 4: Auto-Trade Loop — Autonomous 24/7 Operation
**Priority: P1 | Estimated: 2-3 sessions**

### 4.1 Enable AUTO_EXECUTE_TRADES=true path
Currently `AUTO_EXECUTE_TRADES=false` (shadow mode). Need to:
- [ ] Verify OrderExecutor creates real Alpaca paper orders when enabled
- [ ] Verify bracket orders (stop-loss + take-profit) are placed correctly
- [ ] Verify position sizing uses real Kelly criterion from DuckDB
- [ ] Verify mock-source guard prevents trades from non-real data
- [ ] Test the full loop: bar → signal → council → order → fill → outcome → weight update

### 4.2 PositionManager automated exits
- [ ] Verify trailing stops track real positions
- [ ] Verify time-based exits close stale positions
- [ ] Verify partial profit-taking works
- [ ] Test with paper trading account

### 4.3 OutcomeTracker feedback loop
- [ ] Verify trade outcomes resolve correctly (win/loss/scratch)
- [ ] Verify WeightLearner.update_from_outcome adjusts Bayesian weights
- [ ] Verify SelfAwareness tracks per-agent accuracy
- [ ] Verify censored outcomes are properly excluded

### 4.4 Risk guardrails for autonomous mode
- [ ] Circuit breaker: halt trading on -3% daily drawdown
- [ ] Max portfolio heat: 6% total risk
- [ ] Max single position: 2% of portfolio
- [ ] Max daily trades: 10
- [ ] Max sector concentration: 30%
- [ ] Verify all these limits are enforced end-to-end

---

## Phase 5: Data Firehose — 24/7 Data Ingestion (Including Off-Hours)
**Priority: P1 | Estimated: 2-3 sessions**

### 5.1 Market hours data (real-time)
Already wired in main.py startup:
- AlpacaStreamManager: WebSocket bars for tracked symbols ✓
- EventDrivenSignalEngine: bars → signals ✓
- TurboScanner: 60s parallel DuckDB screens ✓
- MarketWideSweep: full universe batch scan ✓
- NewsAggregator: 8+ RSS feeds every 60s ✓ (needs LLM)
- StreamingDiscoveryEngine: real-time anomaly detection ✓
- ScoutRegistry: 12 continuous scout agents ✓

### 5.2 Off-hours data (pre-market, after-hours, overnight)
Need to add/verify:
- [ ] Pre-market scanning (4:00 AM - 9:30 AM ET): earnings, gaps, news
- [ ] After-hours scanning (4:00 PM - 8:00 PM ET): earnings reactions
- [ ] Overnight analysis: macro events, international markets, FRED data
- [ ] Weekend analysis: SEC filings, 13F deadlines, strategy evolution
- [ ] Scheduler jobs in backend/app/jobs/scheduler.py — verify they run

### 5.3 Data source health monitoring
- [ ] Each data source has health check endpoint
- [ ] Automatic retry on failure with exponential backoff
- [ ] Slack alerts when a data source goes down
- [ ] Dashboard shows real-time source health

---

## Phase 6: UI Buttons & Controls — Make Everything Clickable
**Priority: P2 | Estimated: 3-4 sessions**

### 6.1 Buttons that must trigger real actions

| Page | Button/Control | Expected Action |
|------|---------------|----------------|
| Dashboard | Refresh | Re-fetch all data |
| Agents | Start/Stop/Pause agent | Change agent lifecycle |
| Agents | HITL Approve/Reject | Approve/reject pending trade |
| Agents | Override bias | Set manual bias multiplier |
| Signal Intelligence | Send to Council | POST /council/evaluate |
| Signal Intelligence | Quick Trade | Open trade execution modal |
| ML Brain | Retrain Model | POST /training/ |
| ML Brain | Reset Drift | Reset drift detector |
| Backtest | Run Backtest | POST /backtest/ |
| Market Regime | Override Bias | POST /openclaw/macro/override |
| Trade Execution | Place Order | POST /orders/ or /orders/advanced |
| Trade Execution | Cancel Order | DELETE /alpaca/orders/{id} |
| Risk | Emergency Stop | POST /risk-shield (kill switch) |
| Risk | Pause Trading | Toggle AUTO_EXECUTE |
| Settings | Save Settings | PUT /settings |
| Data Sources | Refresh Source | Re-check individual source |

### 6.2 Toggle controls that must persist
- Auto-execute toggle (shadow vs live)
- Council enabled/disabled
- Individual data source enable/disable
- Risk limits adjustment
- Signal threshold adjustment

---

## Phase 7: Monitoring, Alerts & Resilience
**Priority: P2 | Estimated: 1-2 sessions**

### 7.1 Slack integration
- [ ] Wire OpenClaw bot to send trade notifications
- [ ] Wire TradingView Alerts bot to receive webhook signals
- [ ] Alert on: new trade, position close, drawdown breach, data source failure
- [ ] Alert on: council veto, risk shield activation, system errors

### 7.2 Health monitoring
- [ ] /health endpoint returns comprehensive status
- [ ] /readyz endpoint used for readiness probes
- [ ] WebSocket heartbeat detects stale connections
- [ ] Service registry tracks all 25+ service health

### 7.3 Auto-restart & recovery
- [ ] start-embodier.ps1 handles backend crash recovery
- [ ] Electron app handles process management (Phase 8)
- [ ] Peer resilience: PC2 down → fall back to local Ollama
- [ ] DuckDB corruption recovery (WAL mode helps)

---

## Phase 8: Desktop App & Deployment
**Priority: P3 | Estimated: 2-3 sessions**

### 8.1 Electron packaging
- desktop/ directory is BUILD-READY
- Package backend with PyInstaller
- Single-click install for Windows
- Role-aware: ESPENMAIN vs ProfitTrader behavior

### 8.2 Production deployment checklist
- [ ] Generate API_AUTH_TOKEN and set on both PCs
- [ ] Generate FERNET_KEY for credential encryption
- [ ] Set AUTO_EXECUTE_TRADES=true (after paper trading validation)
- [ ] Enable Slack notifications
- [ ] Set up Windows Task Scheduler for auto-start on boot
- [ ] Configure firewall rules for LAN gRPC (port 50051)

---

## Execution Order

```
Phase 1 (Backend Health)     ← START HERE
  ↓
Phase 2 (UI Wiring)          ← Parallel with Phase 3
Phase 3 (Council Agents)     ← Parallel with Phase 2
  ↓
Phase 4 (Auto-Trade Loop)    ← Requires Phase 1-3
  ↓
Phase 5 (Data Firehose 24/7) ← Can start during Phase 4
Phase 6 (UI Controls)        ← Can start during Phase 4
  ↓
Phase 7 (Monitoring)         ← After Phase 4-6
Phase 8 (Desktop)            ← Final
```

**Total estimated effort: 15-23 focused sessions**

Each session = one Claude Code conversation focused on 2-3 specific tasks.
We work page-by-page, endpoint-by-endpoint, fixing real issues as we find them.
