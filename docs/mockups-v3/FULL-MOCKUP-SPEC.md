# Embodier Trader - Full Mockup Specification V3
## All 17 Pages - ALL V3 COMPLETE - Institutional Glass-Box Command Center

### Design System
- BG: #0B0E14 (deep slate), Accents: Cyan/Amber/Red neon
- Fonts: Monospace data, Inter UI, 2560px+ widescreen, scrollable
- Every element CLICKABLE and HOTLINKED to deeper data
- Recursive self-improving indicators visible on every page
- V3 = Ultra-dense (2560x4000px), maximum data density, every element hotlinked

---

## CORE 3 (V3 Complete)

### 1. Agent Command Center (V3)
- 15 agent cards with DAG brain map, SHAP bars
- Node Control Panel, HITL ring buffer
- Blackboard feed, Macro Brain state, Agent leaderboard
- Agent Performance Leaderboard (sortable 7-day stats)
- Real-time Blackboard pub/sub feed with INSPECT hotlinks
- Macro Brain State panel with HMM regime, sector rotation
- Wires: agent_manager.py, brain.py, consensus_engine.py

### 2. EV Opportunity Matrix (V3)
- Full sortable EV table with ALL columns (18+ columns)
- SHAP waterfall chart per signal expandable
- Multi-timeframe EV comparison (1H/4H/1D/1W)
- Sector breakdown heatmap showing EV by sector
- Position sizing calculator with Kelly/Half-Kelly/Quarter
- Agent Veto Panel per row, Historical EV accuracy chart
- EV Decay Curve, Correlation analysis between top signals
- Real-time scan progress, Export controls (CSV/JSON/API)
- Wires: ev_calculator.py, signal_aggregator.py

### 3. Flywheel Console (V3)
- 15 post-trade autopsy cards with full SHAP waterfalls
- Recursive Improvement DAG (full learning pipeline)
- Learning curve charts: loss, accuracy, validation per model
- Retraining scheduler with cron controls and countdown
- Model versioning timeline with rollback points
- DPO Pair Quality Matrix, Agent accuracy trends (50 cycles)
- HITL feedback analytics, Memory/GPU monitor
- LoRA weight diff viewer, Training data explorer
- Wires: flywheel.py, model_trainer.py, feedback_loop.py

---

## TRADING PAGES (V3 Complete)

### 4. Dashboard (V3)
- 20 KPI micro-cards (2 rows of 10)
- Real-time P&L ticker, multi-timeframe equity curves
- Sector rotation heatmap, agent consensus ring
- Market breadth, order flow, risk mini-panel
- News feed ticker, Flywheel status mini-ring
- Wires: dashboard_api.py, portfolio.py

### 5. Signals Intelligence (V3)
- 20 signal cards with SHAP waterfall charts
- Signal correlation matrix, historical accuracy table
- Signal decay curve, composite score breakdown
- Volume profile, options flow, dark pool prints
- 15 filter controls, recursive improvement chart
- Wires: signal_engine.py, agents/*.py

### 6. Trade Execution (V3)
- Level 3 order book (30 levels), time & sales
- Full options chain with Greeks, algo execution panel
- Smart routing, slippage analysis, risk pre-trade check
- Position builder with P&L graph, margin calculator
- TWAP/VWAP/Iceberg execution with progress bars
- Historical execution log (30 rows)
- Wires: order_manager.py, execution_engine.py, alpaca_api.py

---

## ANALYTICS PAGES (V3 Complete)

### 7. Performance Analytics (V3)
- 10 KPI cards (P&L, Win Rate, Sharpe, Sortino, Calmar, Max DD, Recovery Factor, Info Ratio, Expectancy, Alpha)
- Multi-timeframe equity curve (1H/4H/1D/1W stacked)
- Underwater chart, Trade log table (30 rows)
- Agent performance comparison, Monthly returns heatmap
- Drawdown analysis, Regime performance breakdown
- Rolling Sharpe, Win/Loss streak, P&L attribution
- Wires: performance_tracker.py, trade_logger.py

### 8. Risk Intelligence (V3)
- 12 risk gauges (VaR, CVaR, Tail Risk, Portfolio Heat, Delta, Gamma, Vega, Theta, Liquidity, Leverage, Beta-Adj, Concentration)
- Position risk table (25 rows with Greeks)
- 10x10 correlation matrix with numeric heatmap
- HMM regime full probability distribution, 90-day chart
- Risk Governor log (50 entries), Stress test Monte Carlo
- Circuit breakers (10 toggles), VaR backtest chart
- Risk contribution waterfall, Sector exposure, Overnight risk
- Wires: risk_manager.py, regime_detector.py

### 9. ML Insights (V3)
- 12 model cards with sparklines, confusion matrices
- ROC curve overlay for all models simultaneously
- 20x20 feature correlation matrix heatmap
- Hyperparameter tuning with Bayesian optimization
- Prediction vs actual scatter, Model drift detection
- A/B test results with statistical significance
- Ensemble weight optimizer, Inference latency monitor
- Feature engineering pipeline, SHAP beeswarm plot
- Partial dependence plots for top features
- Wires: ml_models.py, feature_engineering.py

### 10. Backtesting Engine (V3)
- 30+ parameter strategy builder with visual node editor
- Optimization heatmap (parameter sweep grid)
- Rolling Sharpe chart, Trade distribution histogram
- Sector performance per strategy, Regime-aware results
- Position sizing simulator (Kelly/Half-Kelly/Fixed)
- Benchmark comparison (SPY/QQQ/BTC)
- Walk-forward analysis, Monte Carlo fan chart (1000 paths)
- Slippage model, Drawdown analysis, Transaction cost sensitivity
- Wires: backtester.py, walk_forward.py, monte_carlo.py

### 11. Pattern Recognition (V3)
- 40 pattern scanner with mini-chart thumbnails
- Pattern reliability matrix (type x timeframe heatmap)
- Multi-timeframe pattern overlay (1m/5m/1H/4H/1D)
- Fibonacci auto-levels with extension targets
- Elliott Wave counter with degree labeling
- Pattern clustering analysis, Alert builder
- Backtest per pattern, ML vs classic detection comparison
- Pattern frequency distribution, Volume confirmation
- Harmonic scanner (ABCD/Butterfly/Gartley)
- Wires: pattern_scanner.py, chart_patterns.py

---

## INFRASTRUCTURE PAGES (V3 Complete)

### 12. Signal Heatmap (V3)
- S&P 500 full treemap with EV color gradient
- Sector rotation wheel (11 GICS sectors with momentum)
- Signal distribution histogram with normal curve overlay
- Correlation cluster map (50+ node force-directed graph)
- Global markets heatmap (US/EU/Asia/LatAm/Crypto)
- EV threshold slider, Breadth indicators panel
- Top 30 signals ranked, Signal generation rate time-series
- Sector correlation 11x11 matrix, Signal decay visualization

### 13. Strategy Intelligence (V3)
- 15-row active strategies table with all metrics + Sortino/Calmar
- Strategy comparison equity curves overlaid with benchmark
- Allocation pie, Risk contribution waterfall per strategy
- Parameter tuner (20 sliders with real-time preview)
- Strategy evolution timeline (50 flywheel cycles)
- Strategy correlation 15x15 matrix, Regime performance
- Portfolio optimization with efficient frontier
- Strategy builder drag-and-drop, Recursive improvement metrics

### 14. Data Sources Monitor (V3)
- 12 data source cards with real-time sparkline latency
- Auto-reconnect toggles, circuit breaker status per source
- Data pipeline flow diagram (full interactive DAG)
- API rate limits as real-time progress bars per provider
- Data quality metrics table (all sources)
- 30-day uptime history chart, Error log (50+ entries)
- Cost analysis (monthly breakdown), Latency distributions
- Data freshness timeline, Throughput monitor
- Source dependency graph, Backup failover configuration

### 15. Operator Console (V3)
- CPU/GPU/Memory/Disk/Network/API latency with 24h sparklines
- Process manager (20 rows with dependencies, health check)
- Log viewer (multi-source, regex, severity colors, tail -f)
- Cron job scheduler (15 tasks with history)
- System configuration (30 key-value pairs with toggles)
- Deployment panel (CI/CD, version history, rollback)
- Docker container status (10 containers)
- Network monitor (WebSocket, API endpoint health matrix)
- Alert rules configuration, Resource forecasting

### 16. Settings & Configuration (V3)
- 7 expanded sections with every possible control
- Trading: 15 controls (algo selection, smart entry, brackets)
- Agent Config: Full 15-agent grid (ON/OFF, weights, confidence, model, temp, context)
- Risk: 15 parameter controls with circuit breakers
- Notifications: 8 events x 5 channels matrix
- API Keys: 10 providers (masked, test, rotate, usage stats)
- Theme: Color, font, density, animation, layout presets
- Flywheel: Learning rate, retraining, DPO thresholds
- Configuration diff viewer, Import/Export, Preset profiles
- Audit log of setting changes

### 17. YouTube Knowledge Base (V3)
- 12 video cards with AI-extracted insights and sentiment
- AI summary panel with full transcript analysis
- Sentiment timeline (30-day vs SPY price with correlation)
- Knowledge graph (topics to strategies to agents)
- Channel reliability tracker (20 channels ranked)
- Topic clustering force-directed graph
- Auto-process queue, Full-text search
- Ticker mention frequency heatmap
- Video quality scoring, Contrarian indicator
- Watchlist integration (videos mentioning held positions)

---

## Mockup Generation Details

All 17 pages generated through 3-phase iteration:
- **V1**: Initial widescreen layout (2560x1440)
- **V2**: 10x data density, tall scrollable (2560x3000)
- **V3**: Ultra-dense maximum density (2560x4000), every element hotlinked

Generated with **Gemini 3.1 Pro** via Perplexity.ai
Stored in active browser tabs for review and download

---

## STATUS: ALL 17 PAGES AT V3 - COMPLETE

Awaiting approval to proceed with **Phase 2: React Component Code Generation**
