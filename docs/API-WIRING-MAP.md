# API Wiring Map — Frontend ↔ Backend

**Generated:** March 13, 2026  
**Purpose:** Cross-reference all frontend endpoint definitions (`frontend-v2/src/config/api.js`) against backend routers; page-by-page verification of API/WebSocket usage; auth, CORS, and response-shape notes.

---

## 1. Summary

| Item | Count |
|------|--------|
| **Frontend endpoint keys** (api.js) | **~120** unique keys (project CLAUDE.md cites 189 including logical/alias usage; all resolve via getApiUrl) |
| **Backend API routers** (main.py) | **44** (include_router) |
| **Frontend pages** (under Layout) | **15** (14 sidebar pages + TradingViewBridge) |
| **WebSocket channels** (frontend WS_CHANNELS) | **16** |
| **Backend WS_ALLOWED_CHANNELS** | **18** (includes `datasources`, `market_data`, etc.) |

- **Base URL:** `VITE_API_URL` or `""` (same-origin; Vite proxy to backend).
- **API prefix:** `/api/v1`.
- **WebSocket:** Single endpoint `/ws?token=...`; client subscribes via `{ type: 'subscribe', channel }`.

---

## 2. Frontend api.js → Backend Path Mapping

Every key in `API_CONFIG.endpoints` resolves to `BASE_URL + API_PREFIX + path`. Backend mounts routers at `/api/v1/<prefix>`.

| Frontend key (api.js) | Path in api.js | Full backend path | Backend router |
|------------------------|----------------|-------------------|----------------|
| stocks | /stocks/ | /api/v1/stocks/ | stocks |
| quotes | /quotes/ | /api/v1/quotes/ | quotes |
| orders | /orders/ | /api/v1/orders | orders |
| system | /system | /api/v1/system | system |
| system/event-bus/status | /system/event-bus/status | /api/v1/system/event-bus/status | system |
| signals | /signals/ | /api/v1/signals/ | signals |
| signalsHeatmap | /signals/heatmap | /api/v1/signals/heatmap | signals |
| backtest | /backtest/ | /api/v1/backtest/ | backtest_routes |
| backtestRuns | /backtest/runs | /api/v1/backtest/runs | backtest_routes |
| backtestResults | /backtest/results | /api/v1/backtest/results | backtest_routes |
| backtestOptimization | /backtest/optimization | /api/v1/backtest/optimization | backtest_routes |
| backtestWalkforward | /backtest/walkforward | /api/v1/backtest/walkforward | backtest_routes |
| backtestMontecarlo | /backtest/montecarlo | /api/v1/backtest/montecarlo | backtest_routes |
| backtestRegime | /backtest/regime | /api/v1/backtest/regime | backtest_routes |
| backtestRollingSharpe | /backtest/rolling-sharpe | /api/v1/backtest/rolling-sharpe | backtest_routes |
| backtestTradeDistribution | /backtest/trade-distribution | /api/v1/backtest/trade-distribution | backtest_routes |
| backtestKellyComparison | /backtest/kelly-comparison | /api/v1/backtest/kelly-comparison | backtest_routes |
| backtestCorrelation | /backtest/correlation | /api/v1/backtest/correlation | backtest_routes |
| backtestSectorExposure | /backtest/sector-exposure | /api/v1/backtest/sector-exposure | backtest_routes |
| backtestDrawdownAnalysis | /backtest/drawdown-analysis | /api/v1/backtest/drawdown-analysis | backtest_routes |
| openclawSwarmStatus | /openclaw/swarm-status | /api/v1/openclaw/swarm-status | openclaw |
| openclawAgents | /openclaw/candidates | /api/v1/openclaw/candidates | openclaw |
| status | /status | /api/v1/status | status |
| agents | /agents | /api/v1/agents | agents |
| dataSources | /data-sources/ | /api/v1/data-sources/ | data_sources |
| sentiment | /sentiment | /api/v1/sentiment | sentiment |
| sentiment/discover | /sentiment/discover | /api/v1/sentiment/discover | sentiment |
| youtubeKnowledge | /youtube-knowledge | /api/v1/youtube-knowledge | youtube_knowledge |
| flywheel | /flywheel | /api/v1/flywheel | flywheel |
| portfolio | /portfolio | /api/v1/portfolio | portfolio |
| risk | /risk | /api/v1/risk | risk |
| strategy | /strategy | /api/v1/strategy | strategy |
| performance | /performance | /api/v1/performance | performance |
| performanceEquity | /performance/equity | /api/v1/performance/equity | performance |
| performanceTrades | /performance/trades | /api/v1/performance/trades | performance |
| logs | /logs | /api/v1/logs | logs |
| alerts | /alerts | /api/v1/alerts | alerts |
| patterns | /patterns | /api/v1/patterns | patterns |
| settings | /settings | /api/v1/settings | settings_routes |
| openclaw | /openclaw | /api/v1/openclaw | openclaw |
| market | /market | /api/v1/market | market |
| marketIndices | /market/indices | /api/v1/market/indices | market |
| marketOrderBook | /market/order-book | /api/v1/market/order-book | market |
| openclawRegime | /openclaw/regime | /api/v1/openclaw/regime | openclaw |
| mlBrain | /ml-brain/ | /api/v1/ml-brain/ | ml_brain |
| ml-brain/models | /ml-brain/registry/status | /api/v1/ml-brain/registry/status | ml_brain |
| riskShield | /risk-shield | /api/v1/risk-shield | risk_shield_api |
| kellySizer | /risk/kelly-sizer | /api/v1/risk/kelly-sizer | risk |
| positionSizing | /risk/position-sizing | /api/v1/risk/position-sizing | risk |
| drawdownCheck | /risk/drawdown-check | /api/v1/risk/drawdown-check | risk (GET) |
| dynamicStopLoss | /risk/dynamic-stop-loss | /api/v1/risk/dynamic-stop-loss | risk |
| riskScore | /risk/risk-score | /api/v1/risk/risk-score | risk |
| kellyRanked | /signals/kelly-ranked | /api/v1/signals/kelly-ranked | signals |
| preTradeCheck | /strategy/pre-trade-check | /api/v1/strategy/pre-trade-check | strategy |
| swarmTopology | /agents/swarm-topology | /api/v1/agents/swarm-topology | agents |
| agents/spawn | /agents/spawn | /api/v1/agents/spawn | agents |
| agents/clone | /agents/clone | /api/v1/agents/clone | agents |
| agents/swarm/spawn | /agents/swarm/spawn | /api/v1/agents/swarm/spawn | agents |
| agents/swarm/templates | /agents/swarm/templates | /api/v1/agents/swarm/templates | agents |
| agents/kill-all | /agents/kill-all | /api/v1/agents/kill-all | agents |
| agentConsensus | /agents/consensus | /api/v1/agents/consensus | agents |
| conference | /agents/conference | /api/v1/agents/conference | agents |
| teams | /agents/teams | /api/v1/agents/teams | agents |
| drift | /agents/drift | /api/v1/agents/drift | agents |
| systemAlerts | /agents/alerts | /api/v1/agents/alerts | agents |
| agentResources | /agents/resources | /api/v1/agents/resources | agents |
| blackboard | /cns/blackboard/current | /api/v1/cns/blackboard/current | cns |
| cnsBlackboard | /cns/blackboard/current | /api/v1/cns/blackboard/current | cns |
| openclaw/regime | /openclaw/regime | /api/v1/openclaw/regime | openclaw |
| openclaw/macro | /openclaw/macro | /api/v1/openclaw/macro | openclaw |
| strategy/regime-params | /strategy/regime-params | /api/v1/strategy/regime-params | strategy |
| backtest/regime | /backtest/regime | /api/v1/backtest/regime | backtest_routes |
| openclaw/sectors | /openclaw/sectors | /api/v1/openclaw/sectors | openclaw |
| openclaw/scan | /openclaw/scan | /api/v1/openclaw/scan | openclaw |
| openclaw/memory | /openclaw/memory | /api/v1/openclaw/memory | openclaw |
| risk/config | /risk/config | /api/v1/risk/config | risk |
| risk/risk-gauges | /risk/risk-gauges | /api/v1/risk/risk-gauges | risk |
| risk/stress-test | /risk/stress-test | /api/v1/risk/stress-test | risk |
| openclaw/macro/override | /openclaw/macro/override | /api/v1/openclaw/macro/override | openclaw |
| openclaw/health | /openclaw/health | /api/v1/openclaw/health | openclaw |
| risk/risk-score | /risk/risk-score | /api/v1/risk/risk-score | risk |
| openclaw/whale-flow | /openclaw/whale-flow | /api/v1/openclaw/whale-flow | openclaw |
| openclaw/regime/transitions | /openclaw/regime/transitions | /api/v1/openclaw/regime/transitions | openclaw |
| alpaca | /alpaca | /api/v1/alpaca | alpaca |
| alpaca/account | /alpaca/account | /api/v1/alpaca/account | alpaca |
| alpaca/positions | /alpaca/positions | /api/v1/alpaca/positions | alpaca |
| alpaca/orders | /alpaca/orders | /api/v1/alpaca/orders | alpaca |
| alpaca/activities | /alpaca/activities | /api/v1/alpaca/activities | alpaca |
| orders/advanced | /orders/advanced | /api/v1/orders/advanced | orders |
| orders/emergency-stop | /orders/emergency-stop | /api/v1/orders/emergency-stop | orders |
| orders/recent | /orders/recent | /api/v1/orders/recent | orders |
| riskShield/emergency-action | /risk-shield/emergency-action | /api/v1/risk-shield/emergency-action | risk_shield_api |
| alignment/settings | /alignment/settings | /api/v1/alignment/settings | alignment |
| alignment/evaluate | /alignment/evaluate | /api/v1/alignment/evaluate | alignment |
| alignment/verdicts | /alignment/verdicts | /api/v1/alignment/verdicts | alignment |
| alignment/stats | /alignment/stats | /api/v1/alignment/stats | alignment |
| alignment/bright-lines | /alignment/bright-lines | /api/v1/alignment/bright-lines | alignment |
| alignment/constellation | /alignment/constellation | /api/v1/alignment/constellation | alignment |
| alignment/metacognition | /alignment/metacognition | /api/v1/alignment/metacognition | alignment |
| alignment/critique | /alignment/critique | /api/v1/alignment/critique | alignment |
| councilEvaluate | /council/evaluate | /api/v1/council/evaluate | council |
| councilLatest | /council/latest | /api/v1/council/latest | council |
| council/status | /council/status | /api/v1/council/status | council |
| councilWeights | /council/weights | /api/v1/council/weights | council |
| morningBriefing | /briefing/morning | /api/v1/briefing/morning | briefing |
| briefingPositions | /briefing/positions | /api/v1/briefing/positions | briefing |
| weeklyReview | /briefing/weekly | /api/v1/briefing/weekly | briefing |
| briefingWebhookTest | /briefing/webhook/test | /api/v1/briefing/webhook/test | briefing |
| briefingStatus | /briefing/status | /api/v1/briefing/status | briefing |
| tradingviewPushSignals | /tradingview/push-signals | /api/v1/tradingview/push-signals | tradingview |
| tradingviewConfig | /tradingview/config | /api/v1/tradingview/config | tradingview |
| tradingviewPineScript | /tradingview/pine-script | /api/v1/tradingview/pine-script | tradingview |
| featuresLatest | /features/latest | /api/v1/features/latest | features |
| featuresCompute | /features/compute | /api/v1/features/compute | features |
| training | /training/ | /api/v1/training/ | training |
| metrics | /metrics | /api/v1/metrics | metrics_api |
| metricsSetAutoExecute | /metrics/auto-execute | /api/v1/metrics/auto-execute | metrics_api |
| metricsEmergencyFlatten | /metrics/emergency-flatten | /api/v1/metrics/emergency-flatten | metrics_api |
| system/health | /system | /api/v1/system | system |
| deviceInfo | /system/device | /api/v1/system/device | system |
| cnsHomeostasis | /cns/homeostasis/vitals | /api/v1/cns/homeostasis/vitals | cns |
| cnsCircuitBreaker | /cns/circuit-breaker/status | /api/v1/cns/circuit-breaker/status | cns |
| cnsAgentsHealth | /cns/agents/health | /api/v1/cns/agents/health | cns |
| cnsPostmortems | /cns/postmortems | /api/v1/cns/postmortems | cns |
| cnsPostmortemsAttribution | /cns/postmortems/attribution | /api/v1/cns/postmortems/attribution | cns |
| cnsDirectives | /cns/directives | /api/v1/cns/directives | cns |
| cnsLastVerdict | /cns/council/last-verdict | /api/v1/cns/council/last-verdict | cns |
| cnsProfitBrain | /cns/profit-brain | /api/v1/cns/profit-brain | cns |
| cognitiveDashboard | /cognitive/dashboard | /api/v1/cognitive/dashboard | cognitive |
| cognitiveSnapshots | /cognitive/snapshots | /api/v1/cognitive/snapshots | cognitive |
| cognitiveCalibration | /cognitive/calibration | /api/v1/cognitive/calibration | cognitive |
| logs/system | /logs | /api/v1/logs | logs |
| swarmTurboStatus | /swarm/turbo/status | /api/v1/swarm/turbo/status | swarm |
| swarmHyperStatus | /swarm/hyper/status | /api/v1/swarm/hyper/status | swarm |
| swarmNewsStatus | /swarm/news/status | /api/v1/swarm/news/status | swarm |
| swarmSweepStatus | /swarm/sweep/status | /api/v1/swarm/sweep/status | swarm |
| swarmUnifiedStatus | /swarm/unified/status | /api/v1/swarm/unified/status | swarm |
| swarmOutcomesStatus | /swarm/outcomes/status | /api/v1/swarm/outcomes/status | swarm |
| swarmOutcomesKelly | /swarm/outcomes/kelly | /api/v1/swarm/outcomes/kelly | swarm |
| swarmPositionsManaged | /swarm/positions/managed | /api/v1/swarm/positions/managed | swarm |
| swarmMlScorerStatus | /swarm/ml-scorer/status | /api/v1/swarm/ml-scorer/status | swarm |
| agentAllConfig | /agents/all-config | /api/v1/agents/all-config | agents |
| agentHitlBuffer | /agents/hitl/buffer | /api/v1/agents/hitl/buffer | agents |
| agentHitlStats | /agents/hitl/stats | /api/v1/agents/hitl/stats | agents |
| agentAttribution | /agents/attribution | /api/v1/agents/attribution | agents |
| agentEloLeaderboard | /agents/elo-leaderboard | /api/v1/agents/elo-leaderboard | agents |
| agentWsChannels | /agents/ws-channels | /api/v1/agents/ws-channels | agents |
| agentFlowAnomalies | /agents/flow-anomalies | /api/v1/agents/flow-anomalies | agents |
| scanners | /agents | /api/v1/agents | agents |
| intels | /agents | /api/v1/agents | agents |
| flywheelScheduler | /flywheel/scheduler | /api/v1/flywheel/scheduler | flywheel |
| flywheelKpis | /flywheel/kpis | /api/v1/flywheel/kpis | flywheel |
| flywheelPerformance | /flywheel/performance | /api/v1/flywheel/performance | flywheel |
| flywheelSignals | /flywheel/signals/staged | /api/v1/flywheel/signals/staged | flywheel |
| flywheelModels | /flywheel/models | /api/v1/flywheel/models | flywheel |
| flywheelLogs | /flywheel/logs | /api/v1/flywheel/logs | flywheel |
| flywheelFeatures | /flywheel/features | /api/v1/flywheel/features | flywheel |
| briefingMorning | /briefing/morning | /api/v1/briefing/morning | briefing |
| briefingTradingview | /briefing/tradingview | /api/v1/briefing/tradingview | briefing |
| briefingWatchlistExport | /briefing/watchlist-export | /api/v1/briefing/watchlist-export | briefing |
| briefingPushWebhook | /briefing/push-webhook | /api/v1/briefing/push-webhook | briefing |

**Note:** Backend `swarm` router uses paths like `/turbo/status`, `/hyper/status`, etc. under prefix `/api/v1/swarm`, so `/api/v1/swarm/turbo/status` etc. are correct. `ml-brain/models` in api.js points to `/ml-brain/registry/status` (backend: `ml_brain` router has `GET /registry/status`).

---

## 3. Backend Routers (44)

| Router module | Prefix (in main.py) | Key routes |
|---------------|---------------------|------------|
| stocks | /api/v1/stocks | GET /, /tracked, /list |
| quotes | /api/v1/quotes | GET /, /{ticker}, /{ticker}/candles, /{ticker}/book, /{ticker}/options-chain |
| orders | /api/v1/orders | GET /, /recent; POST /advanced, /emergency-stop, /close, /flatten-all; PATCH/DELETE /{id} |
| system | /api/v1/system | GET "" (health), /event-bus/status, /device |
| training | /api/v1/training | (varies) |
| signals | /api/v1/signals | GET /, /heatmap, /kelly-ranked, /{symbol}/technicals, /active/{symbol}; POST / |
| backtest_routes | /api/v1/backtest | GET /, /runs, /results, /optimization, /walkforward, /montecarlo, /regime, /rolling-sharpe, /trade-distribution, /kelly-comparison, /correlation, /sector-exposure, /drawdown-analysis |
| status | /api/v1/status | GET "", /data |
| data_sources | /api/v1/data-sources | GET /, /{id}; POST/PUT/DELETE /, /{id}, /{id}/test, /ai-detect, /off-hours/* |
| portfolio | /api/v1/portfolio | GET "" |
| risk | /api/v1/risk | GET /, /kelly-sizer, /position-sizing, /risk-score, /risk-gauges, /config, /stress-test, /drawdown-check, /history, /correlation-matrix, /monte-carlo; POST /drawdown-check, /dynamic-stop-loss, /emergency/{action} |
| strategy | /api/v1/strategy | GET "", /regime-params, /pre-trade-check (and POST /pre-trade-check/{symbol}), /adaptive-strategy, /strategy-matrix |
| performance | /api/v1/performance | GET "", /health, /summary, /equity, /trades, /risk-metrics |
| flywheel | /api/v1/flywheel | GET "", /logs, /kpis, /performance, /signals/staged, /models, /features, /scheduler, /engine, /registry, /drift |
| logs | /api/v1/logs | GET "" |
| patterns | /api/v1/patterns | (screener/DB-backed) |
| openclaw | /api/v1/openclaw | GET "", /regime, /macro, /sectors, /scan, /memory, /health, /whale-flow, /swarm-status, /candidates, /regime/transitions, /macro/override; POST /macro/override |
| ml_brain | /api/v1/ml-brain | GET /, /performance, /signals/staged, /flywheel-logs, /registry/status, /drift/status, /lstm/predict/{symbol}, /status |
| market | /api/v1/market | GET "", /indices, /order-book, /price-ladder |
| agents | /api/v1/agents | GET "", /swarm-topology, /conference, /consensus, /teams, /drift, /alerts, /resources, /hitl/buffer, /hitl/stats, /all-config, /attribution, /elo-leaderboard, /ws-channels, /flow-anomalies; POST /spawn, /clone, /swarm/spawn, /kill-all, /{id}/start|stop|restart|config, /batch/*, /hitl/{id}/approve|reject|defer |
| sentiment | /api/v1/sentiment | GET "", /summary, /history; POST "", /source-health, /discover; DELETE /{ticker} |
| alerts | /api/v1/alerts | GET "", /recent; POST /test-email, /test-sms, /evaluate; PATCH /{rule_id} |
| settings_routes | /api/v1/settings | GET "", /categories, /audit-log, /export, /{category}; POST /reset/{category}, /validate, /test-connection, /import |
| alpaca | /api/v1/alpaca | GET "", /account, /positions, /orders, /activities, /clock, /snapshots, /latest-trades, /latest-quotes; DELETE /positions, /positions/{symbol} |
| alignment | /api/v1/alignment | GET /settings, /verdicts, /stats, /bright-lines, /constellation, /metacognition, /critique; POST /evaluate |
| risk_shield_api | /api/v1/risk-shield | GET "", /status, /freeze-status, /history; POST /emergency-action |
| features | /api/v1/features | GET /latest, /versions, /compatibility; POST /compute |
| council | /api/v1/council | GET /latest, /status, /weights; POST /evaluate, /weights/reset |
| cns | /api/v1/cns | GET /homeostasis/vitals, /circuit-breaker/status, /agents/health, /blackboard/current, /postmortems, /postmortems/attribution, /directives, /profit-brain, /council/last-verdict; POST /agents/{name}/override-status, /agents/{name}/override-weight; PUT /directives/{filename} |
| swarm | /api/v1/swarm | GET /turbo/status, /hyper/status, /news/status, /sweep/status, /outcomes/status, /outcomes/kelly, /positions/managed, /ml-scorer/status, /unified/status, /ingest/feed, /scout/status, many more |
| cognitive | /api/v1/cognitive | GET /dashboard, /snapshots, /calibration |
| youtube_knowledge | /api/v1/youtube-knowledge | GET "", / |
| ingestion_firehose | (router has prefix /api/v1/ingestion) | GET /status, /metrics |
| cluster | /api/v1/cluster | GET /status, /telemetry, /dispatcher, /pinning |
| llm_health | /api/v1/llm/health | GET "" |
| mobile_api | /api/v1/mobile | (mobile endpoints) |
| brain | /api/v1/brain | (LLM proxy) |
| awareness | /api/v1 | POST /enrich |
| blackboard_routes | /api/v1/blackboard | GET "", /{symbol} |
| triage | /api/v1/triage | (idea triage) |
| webhooks | /api/v1/webhooks | POST /tradingview, /signal |
| briefing | /api/v1/briefing | GET /morning, /positions, /weekly, /status, /tradingview, /watchlist-export; POST /webhook/test, /push-webhook |
| tradingview | /api/v1/tradingview | GET /config, /pine-script; POST /push-signals |
| metrics_api | (router defines prefix /api/v1/metrics) | GET "", /prometheus, /pipeline; POST /auto-execute, /emergency-flatten, /ws-circuit-breaker/reset |
| health_api | (no prefix in main) | GET "" (root health) |

---

## 4. Page-by-Page API & WebSocket Usage

### 4.1 Layout & shared components

| Component | Endpoints used | WebSocket |
|-----------|----------------|----------|
| **Layout.jsx** | system, marketIndices | — |
| **Sidebar.jsx** | system | — |
| **CNSVitals.jsx** | (useCircuitBreakerStatus, useCnsAgentsHealth → cnsCircuitBreaker, cnsAgentsHealth) | — |
| **ProfitBrainBar.jsx** | (useProfitBrain → cnsProfitBrain) | — |
| **TradeExecutionWidgets.jsx** | getApiUrl('councilLatest') | — |

### 4.2 Dashboard (Dashboard.jsx)

- **useApi:** metrics, status, signals, kellyRanked, portfolio, marketIndices, openclaw, performance, agents, agentConsensus, performanceEquity, riskScore, systemAlerts, flywheel, sentiment, cognitiveDashboard, techsData (signals), swarmTopology, dataSources, risk, quotes.
- **getApiUrl + fetch:** orders/advanced, signals (POST), orders (flatten-all), orders/emergency-stop, metricsSetAutoExecute.
- **WebSocket:** (none in snippet; optional real-time can be added via WS_CHANNELS).

### 4.3 Agent Command Center (AgentCommandCenter.jsx + tabs)

- **useApi:** agents, system/health, teams, systemAlerts, conference, drift, cnsBlackboard, cnsAgentsHealth.
- **getApiUrl + fetch:** orders/emergency-stop; agents + `/${id}/start|stop|restart|config`, /batch/start|stop|restart.
- **AgentRegistryTab:** agents + `/${agentId}/start|stop|restart`, agents + `/${agentId}/config`, agents + /batch/start|stop|restart.
- **RemainingTabs:** cnsBlackboard, council/status, conference, councilWeights, ml-brain/models, training, drift, logs/system, system/health; agents + /hitl/{id}/{action}.

### 4.4 Signal Intelligence V3 (SignalIntelligenceV3.jsx)

- **useApi:** signals, agents, openclaw, dataSources, sentiment, youtubeKnowledge, training, mlBrain, flywheelModels, patterns, risk, alerts, status, performance, market, portfolio, strategy, councilLatest, openclawRegime, flywheel.
- **getApiUrl:** quotes (with symbol), `${category}s` + `/${id}/weight` (agents), training + /retrain, settings, orders.
- **WebSocket:** ws.on("signals"), ws.on("*").

### 4.5 Sentiment Intelligence (SentimentIntelligence.jsx)

- **useApi:** signals, systemAlerts.
- **getApiUrl:** sentiment/discover (POST).

### 4.6 Data Sources Monitor (DataSourcesMonitor.jsx)

- **useApi:** dataSources.
- **getApiUrl:** dataSources (base for CRUD).

### 4.7 ML Brain Flywheel (MLBrainFlywheel.jsx)

- **useApi:** flywheelKpis, flywheelPerformance, flywheelSignals, flywheelModels, flywheelLogs, flywheelFeatures.
- **getApiUrl:** training (retrain, deploy, models/compare).

### 4.8 Patterns (Patterns.jsx)

- (Uses useApi/patterns or similar; not fully enumerated in grep.)

### 4.9 Backtesting (Backtesting.jsx)

- **useApi:** backtestResults, backtestOptimization, backtestWalkforward, backtestMontecarlo, backtestRollingSharpe, backtestTradeDistribution, backtestRegime, backtestRuns, backtestCorrelation, backtestSectorExposure, backtestDrawdownAnalysis, agents, teams, system/health.
- **getApiUrl:** backtest (POST for run).

### 4.10 Performance Analytics (PerformanceAnalytics.jsx)

- **useApi:** performance, performanceEquity, performanceTrades, flywheel, riskScore, agents.

### 4.11 Market Regime (MarketRegime.jsx)

- **useApi:** openclaw/scan, market, risk/risk-score, (regime/macro/params via hooks).
- **getApiUrl:** strategy/regime-params (PUT), risk/config (PUT).
- **WebSocket:** WS_CHANNELS.macro, WS_CHANNELS.market.

### 4.12 Trades (Trades.jsx)

- **useApi:** alpaca/positions, alpaca/orders, alpaca/account, portfolio, system.
- **getApiUrl:** orders (DELETE /{orderId}, POST).

### 4.13 Risk Intelligence (RiskIntelligence.jsx)

- **useApi:** risk, riskShield, risk (endpoint /risk/risk-gauges), kellySizer, risk (endpoint /risk/monte-carlo), risk (endpoint /risk/history), portfolio, swarmSweepStatus.
- **getApiUrl:** orders/emergency-stop, risk + `/emergency/${action}`, swarmSweepStatus, risk/stress-test.
- **WebSocket:** WS_CHANNELS.risk.

### 4.14 Trade Execution (TradeExecution.jsx)

- **useApi:** stocks, quotes (chain + candles).
- **getApiUrl:** (order submission via trade execution service).
- **WebSocket:** WS_CHANNELS.trades, WS_CHANNELS.market, WS_CHANNELS.council_verdict.

### 4.15 TradingView Bridge (TradingViewBridge.jsx)

- **useApi:** morningBriefing, briefingPositions, tradingviewConfig.
- **getApiUrl:** tradingviewPushSignals (POST), tradingviewPineScript (GET, copy script).

### 4.16 Settings (Settings.jsx)

- **useApi:** settings with endpoint override `/settings/audit-log`.

---

## 5. WebSocket Channels

### 5.1 Frontend (WS_CHANNELS in api.js)

| Channel | Usage |
|---------|--------|
| agents | Agent updates |
| datasources | Data source events |
| signals | Signal stream |
| trades | Trade/order updates |
| logs | Log stream |
| sentiment | Sentiment updates |
| risk | Risk updates |
| kelly | Kelly sizing |
| alignment | Alignment engine |
| council | Council events |
| council_verdict | Verdict stream |
| homeostasis | CNS homeostasis |
| circuit_breaker | Circuit breaker status |
| market | Market data |
| swarm | Swarm intelligence |
| macro | Macro/regime |

### 5.2 Backend (WS_ALLOWED_CHANNELS in websocket_manager.py)

- order, risk, kelly, signals, council, health, market_data, alerts, outcomes, system  
- agents, data_sources, datasources, trades, logs, sentiment, alignment, council_verdict  
- homeostasis, circuit_breaker, swarm, macro, market  

**Alignment:** Frontend uses `datasources`; backend allows both `data_sources` and `datasources`. All other frontend channel names appear in the backend allow list. Single WS endpoint: `/ws?token=...`; client sends `{ type: 'subscribe', channel }` after connect.

---

## 6. Auth & CORS

### 6.1 Auth

- **Frontend:** `getAuthHeaders()` from api.js returns `{ Authorization: 'Bearer <token>' }`; token from `localStorage.auth_token` or `VITE_API_AUTH_TOKEN`.
- **Backend:** `require_auth` dependency on sensitive routes (orders, council evaluate, strategy pre-trade-check, risk emergency, briefing, tradingview push, etc.). WebSocket: `?token=<API_AUTH_TOKEN>`.
- **useApi:** All fetch calls in useApi use `getAuthHeaders()`; no separate auth for GET vs POST in the hook.

### 6.2 CORS

- **Backend:** `CORSMiddleware` with `allow_origins=settings.effective_cors_origins`, `allow_credentials=True`, `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`, `allow_headers=["Content-Type", "Authorization", "X-Requested-With"]`.
- **effective_cors_origins** (config.py): Always includes localhost (5173, 5174, 3000, 3002, 8501) and 127.0.0.1 variants, plus `"null"` for Electron file://. Custom origins from env `CORS_ORIGINS` (comma-separated).

---

## 7. Response Shapes & Notes

- **Council:** `/council/latest` returns DecisionPacket-like object (verdict, votes, symbol, confidence).
- **Signals:** List of signal objects (symbol, score, label, etc.).
- **Portfolio:** Positions and equity summary.
- **Risk:** risk-score, risk-gauges, drawdown-check return structured JSON; stress-test and Monte Carlo have specific shapes (see risk router).
- **Metrics:** Nested object (core, message_bus, order_executor, etc.); pipeline at `/metrics/pipeline`.
- **Briefing/TradingView:** morning briefing and positions return structured objects; pine-script is `text/plain`.

---

## 8. Gaps & Mismatches

| Item | Status |
|------|--------|
| system/event-bus/status | api.js has it; backend system router exposes GET /event-bus/status. **OK.** |
| briefing/watchlist-export | api.js has briefingWatchlistExport → /briefing/watchlist-export; briefing router has GET /watchlist-export. **OK.** |
| flywheel/scheduler | api.js flywheelScheduler → /flywheel/scheduler; flywheel router has GET /scheduler. **OK.** |
| useApi with endpoint override | Some pages use `useApi('risk', { endpoint: '/risk/risk-gauges' })` etc.; useApi builds URL as base + endpoint override. Backend paths match. **OK.** |
| preTradeCheck | Frontend uses POST to `/strategy/pre-trade-check/${symbol}`; backend has POST /pre-trade-check/{symbol}. **OK.** |

**Recommendation:** Run a quick smoke test for each page (or E2E) to confirm response shapes and auth where applicable. No structural wiring gaps were found between the 120+ api.js keys and the 44 backend routers.
