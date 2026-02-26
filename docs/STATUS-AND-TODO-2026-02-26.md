# Embodier Trader - Status & TODO Update
## Date: February 26, 2026
## Source: Intelligence Council Analysis (GPT-5.2 + Claude Opus 4.6 + Gemini 3.1 Pro)

---

## CURRENT PROJECT STATUS

### Completed Items
- [x] ML Brain & Flywheel page - 4K mockup approved and coded (MLBrainAndFlywheel.jsx + ml_api.py)
- [x] Intelligence Dashboard - 4K mockup approved
- [x] Frontend foundation files committed:
  - `frontend/src/lib/types/index.ts` - TypeScript data models
  - `frontend/src/lib/api/websocket.ts` - WebSocket manager with reconnection
- [x] Backend legacy cleanup: agent_relative_weakness.py - removed dead yfinance import (commit fb55bb4)
- [x] macro_context.py - Yahoo Finance VIX fallback identified for Alpaca replacement

### In Progress
- [ ] macro_context.py refactor - Replace Yahoo Finance VIX fallback with Alpaca market data
- [ ] 14-page UI production build pipeline established

---

## UI PAGE PRODUCTION PLAN

### Design System (Locked)
- Resolution: 3840x2160 (4K ultra-wide)
- Format: Flat 2D UI screen (no monitor photos)
- Brand: Embodier Trader
- Theme: Background #0A0E1A, Cards #1A1F2E with #2A3444 borders
- Primary accent: #00D9FF (cyan)
- Success: #10B981 (green) | Danger: #EF4444 (red) | Warning: #F59E08 (orange)
- Typography: White #F9FAFB primary, #9CA3AF secondary
- Cards: Glassmorphism, 8px rounded corners, subtle shadows
- Data density: 100x normal (Bloomberg-terminal level)

### Charting Libraries (Locked)
1. **TradingView Lightweight Charts** - Raw financial data (candlesticks, volume, equity curves)
2. **Recharts** - AI transparency (SHAP bars, Agent Consensus Donut, heatmaps)
3. **React Flow** - Node-based diagrams (Swarm Brain Map, data pipeline visualization)

### 14-Page Status Matrix

| # | Page | Status | Priority |
|---|------|--------|----------|
| 1 | Intelligence Dashboard | MOCKUP DONE | Next to code |
| 2 | ML Brain & Flywheel | DONE (coded + committed) | Complete |
| 3 | Agent Command Center | READY TO BUILD | High |
| 4 | Signal Intelligence | PENDING | High |
| 5 | Market Regime | PENDING | High |
| 6 | Active Trades | PENDING | High |
| 7 | Trade Execution | PENDING | High |
| 8 | Risk Intelligence | PENDING | Medium |
| 9 | Screener & Patterns | PENDING | Medium |
| 10 | Performance Analytics | PENDING | Medium |
| 11 | Backtesting Lab | PENDING | Medium |
| 12 | Sentiment Intelligence | PENDING | Low |
| 13 | Data Sources Monitor | PENDING | Low |
| 14 | Settings | PENDING | Low |

### Left Sidebar Navigation (14 Pages - Locked)
1. Intelligence Dashboard
2. Agent Command Center
3. Signal Intelligence
4. Sentiment Intelligence
5. Data Sources Monitor
6. ML Brain & Flywheel
7. Screener & Patterns
8. Backtesting Lab
9. Performance Analytics
10. Market Regime
11. Active Trades
12. Risk Intelligence
13. Trade Execution
14. Settings

---

## UI PAGE GENERATION WORKFLOW

### Step 1: Generate 3 Versions per page
Using multi-model pipeline:
- Version A (Comet/Claude) - Data density and information architecture
- Version B (Gemini 2.5 Pro) - Visual fidelity and chart aesthetics
- Version C (Perplexity/Max) - Interaction patterns and innovative layouts

### Step 2: Synthesize Final Page
- Take best elements from all 3 versions
- Ensure consistency with design system above
- Output as flat 2D widescreen page

### Step 3: Code to Git (one file at a time)
- React/JSX component with Tailwind CSS
- Wire to FastAPI backend endpoints
- Commit each file individually to main

---

## BACKEND HARDENING TODO

### Critical (P0/P1)
- [ ] Wire OpenClaw 5-pillar scores into signal_engine.py
- [ ] Fix LSTM input_size mismatch in ml_training.py (currently 4, needs 25+)
- [ ] Wire risk_governor into alpaca_service.py execution path
- [ ] Replace Yahoo Finance fallback in macro_context.py with Alpaca
- [ ] Add test suite foundation (backend/tests/ with pytest)

### High Priority (P1/P2)
- [ ] Split openclaw_bridge_service.py (976 lines) into 4 modules
- [ ] Add missing DB tables: trades journal, daily journal, audit_trail, model_versions
- [ ] Implement WebSocket endpoint in main.py

### Medium Priority (P2)
- [ ] Migrate last 4 Recharts pages to LW Charts
- [ ] Wire all mock endpoints to real data
- [ ] Build meta_learner.py (flywheel brain)
- [ ] Wire swarm_manager.py (agent tournament)

---

## LEGACY CODE CLEANUP STATUS

### Completed
- [x] agent_relative_weakness.py - Removed dead yfinance import
- [x] mockData.js - Deleted

### In Progress
- [ ] macro_context.py - Yahoo Finance URL removal (Alpaca replacement)

### Pending (yfinance/legacy removal sequence)
- [ ] hmm_regime.py - Yahoo Finance SPY OHLCV for HMM regime detector
- [ ] Other intelligence/ files with legacy dependencies
- [ ] Full openclaw/ legacy directory audit

---

## ACTIVE TECH STACK (Verified)

| Layer | File(s) | Technology |
|-------|---------|------------|
| Market Data | alpaca_service.py, finviz_service.py | Alpaca API + Finviz |
| Options Flow | unusual_whales_service.py | Unusual Whales API |
| Database | database.py, openclaw_db.py | SQLite (WAL mode) |
| Trade Journal | training_store.py | SQLite training_store table |
| Signal Engine | signal_engine.py | Bull/bear scoring (needs upgrade) |
| ML Training | ml_training.py | PyTorch LSTM (GPU/CPU + AMP) |
| ML Ensemble | xgboost_trainer.py | XGBoost GPU |
| Backtester | backtest_engine.py | Sharpe/PnL/MaxDD/Calmar |
| OpenClaw Bridge | openclaw_bridge_service.py | 976-line module (needs split) |
| Macro Data | fred_service.py, sec_edgar_service.py | FRED + SEC EDGAR |
| Frontend | frontend-v2/ (React + Vite) | 15 pages, V3 widescreen |
| Backend | main.py -> FastAPI :8000 | /api/v1/* versioned routes |

**NOT in active stack:** No yfinance, No Google Sheets, No DuckDB, No TimescaleDB, No Next.js, No Streamlit

---

## API WIRING REQUIREMENTS

Endpoints needed for frontend:
- `/api/v1/prices` - Real-time price data
- `/api/v1/signals` - Trading signals from OpenClaw pipeline
- `/api/v1/predictions` - ML model predictions
- `/api/v1/ohlcv` - Historical OHLCV data
- `/api/v1/indicators` - Technical indicators
- `/api/v1/orderbook` - Level 2 order book
- `ws://localhost:8000/ws` - WebSocket for real-time streaming

---

## NEXT IMMEDIATE ACTIONS

1. Complete macro_context.py refactor (Yahoo -> Alpaca VIX fallback)
2. Continue legacy yfinance removal in hmm_regime.py
3. Begin coding Agent Command Center page (Page 3)
4. Wire WebSocket endpoint for real-time data streaming

---

## PERPLEXITY THREAD REFERENCES
- Council Analysis Thread: Active in Embodier Trader space
- UI Design Thread: 14-page production plan with 3-version workflow
- Legacy Cleanup Thread: File-by-file yfinance removal sequence

---

*Generated by Intelligence Council (GPT-5.2 Thinking + Claude Opus 4.6 Thinking + Gemini 3.1 Pro)*
*Last Updated: February 26, 2026*
