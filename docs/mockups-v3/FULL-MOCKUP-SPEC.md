# Embodier Trader - Full Mockup Specification V3
## All 17 Pages - Institutional Glass-Box Command Center

### Design System
- BG: #0B0E14 (deep slate), Accents: Cyan/Amber/Red neon
- Fonts: Monospace data, Inter UI, 2560px+ widescreen, scrollable
- Every element CLICKABLE and HOTLINKED to deeper data
- Recursive self-improving indicators visible on every page

---

## CORE 3 (V3 Complete)

### 1. Agent Command Center (V3)
- 15 agent cards with DAG brain map, SHAP bars
- Node Control Panel, HITL ring buffer
- Blackboard feed, Macro Brain state, Agent leaderboard
- Wires: agent_manager.py, brain.py, consensus_engine.py

### 2. EV Opportunity Matrix (V2)
- Sortable EV table with all columns, SHAP waterfall per signal
- Multi-timeframe comparison, sector breakdown
- Wires: ev_calculator.py, signal_aggregator.py

### 3. Flywheel Console (V2)
- Recursive improvement DAG, learning curve charts
- Retraining scheduler, model versioning timeline
- Wires: flywheel.py, model_trainer.py, feedback_loop.py

---

## TRADING PAGES (V3 Complete)

### 4. Dashboard (V3)
- 20 KPI micro-cards (2 rows of 10)
- Real-time P&L ticker, multi-timeframe equity curves
- Sector rotation heatmap, agent consensus ring
- Market breadth, order flow, risk mini-panel
- Wires: dashboard_api.py, portfolio.py

### 5. Signals Intelligence (V3)
- 20 signal cards with SHAP waterfalls
- Signal correlation matrix, historical accuracy table
- Signal decay curve, composite score breakdown
- Volume profile, options flow, dark pool prints
- Wires: signal_engine.py, agents/*.py

### 6. Trade Execution (V3)
- Level 3 order book (30 levels), time & sales
- Full options chain with Greeks, algo execution panel
- Smart routing, slippage analysis, risk pre-trade check
- Position builder with P&L graph, margin calculator
- Wires: order_manager.py, execution_engine.py, alpaca_api.py

---

## ANALYTICS PAGES (V2 Complete)

### 7. Performance Analytics (V2)
- 10 KPI cards (P&L, Win Rate, Sharpe, Sortino, Calmar...)
- Multi-timeframe equity curve + underwater chart
- Trade log table (30 rows), agent performance comparison
- Monthly returns heatmap, drawdown analysis
- Wires: performance_tracker.py, trade_logger.py

### 8. Risk Intelligence (V2)
- 12 risk gauges (VaR, CVaR, Tail Risk, Greeks...)
- Position risk table (25 rows), 10x10 correlation matrix
- HMM regime distribution, risk governor log
- Stress test (Monte Carlo), circuit breakers
- Wires: risk_manager.py, regime_detector.py

### 9. ML Insights (V2)
- 12 model cards with sparklines, confusion matrices
- ROC curve overlay, 20x20 feature correlation matrix
- Hyperparameter tuning, prediction vs actual scatter
- Model drift detection, A/B test results
- Wires: ml_models.py, feature_engineering.py

### 10. Backtesting Engine (V2)
- 30+ parameter strategy builder, optimization heatmap
- Rolling Sharpe, trade distribution histogram
- Sector performance, regime-aware results
- Position sizing simulator, benchmark comparison
- Wires: backtester.py, walk_forward.py, monte_carlo.py

### 11. Pattern Recognition (V2)
- 40 pattern scanner with mini-chart thumbnails
- Pattern reliability matrix, multi-timeframe overlay
- Fibonacci auto-levels, Elliott Wave counter
- Pattern clustering, alert builder, backtest per pattern
- Wires: pattern_scanner.py, chart_patterns.py

---

## INFRASTRUCTURE PAGES (V1 Complete)

### 12. Signal Heatmap (V1)
- S&P 500 treemap by signal strength, sector rotation wheel
- Signal distribution histogram, correlation cluster map
- Global markets heatmap, EV threshold slider

### 13. Strategy Intelligence (V1)
- 15-row active strategies table with ON/OFF toggle
- Strategy comparison equity curves, allocation pie chart
- Parameter tuner with sliders, evolution timeline

### 14. Data Sources Monitor (V1)
- 12 data source cards (Alpaca, TradingView, Yahoo...)
- Data pipeline flow diagram, API rate limits dashboard
- Data quality metrics table

### 15. Operator Console (V1)
- CPU/GPU/Memory/Disk bars, process manager (20 rows)
- Terminal-style log viewer, cron job scheduler
- System configuration with toggle controls

### 16. Settings & Configuration (V1)
- 7 collapsible sections: Trading, Agents, Risk, Notifications, API Keys, Theme, Flywheel
- 15 agent weight sliders, risk parameter controls
- Recursive improvement toggles, learning rate

### 17. YouTube Knowledge Base (V1)
- 12 video cards with AI-extracted insights
- AI summary panel, sentiment timeline
- Knowledge graph, channel reliability tracker

---

## Mockup Links (Perplexity/Gemini 3.1 Pro)
All mockups generated with Gemini 3.1 Pro via Perplexity.ai
Stored in active browser tabs for review and download

## Next Phase: React Component Code
Awaiting approval to proceed with Phase 2 (React code generation)
