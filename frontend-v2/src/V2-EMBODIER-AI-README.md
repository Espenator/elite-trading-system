# 🤖 V2-EMBODIER AI README
## Elite Trader v2 — Living Architecture Document
**Purpose:** This document is the single source of truth for AI agents (Claude, Perplexity) and Oleh (developer) to understand the current state, file structure, and next steps for Elite Trader v2.

---

## 🏗️ ACTUAL V2 REPOSITORY STRUCTURE (as of Feb 23, 2026)

Branch: `v2` — 84 commits ahead of main. All Oleh's work is here.

### Backend: `backend/`

```
backend/
├── app/
│   ├── api/
│   │   └── v1/                          # All API routes (FastAPI)
│   │       ├── agents.py                # Agent management & task tracking
│   │       ├── alerts.py                # Email/SMS alert endpoints
│   │       ├── backtest_routes.py       # Backtesting API with WebSocket
│   │       ├── data_sources.py          # Data source status & WebSocket
│   │       ├── flywheel.py              # Flywheel strategy endpoints
│   │       ├── logs.py                  # Detailed log entries API
│   │       ├── orders.py                # Alpaca order execution
│   │       ├── patterns.py              # Pattern detection & settings
│   │       ├── performance.py           # Performance analytics
│   │       ├── portfolio.py             # Portfolio management
│   │       ├── quotes.py                # Real-time quotes (Finviz/Alpaca)
│   │       ├── risk.py                  # Risk management & alerts
│   │       ├── sentiment.py             # Sentiment analysis
│   │       ├── settings_routes.py       # App settings
│   │       ├── signals.py               # Signal generation & WebSocket
│   │       ├── status.py                # System status
│   │       ├── stocks.py                # Stock data & asset exchange
│   │       ├── strategy.py              # Strategy management
│   │       ├── system.py                # System architecture status
│   │       ├── training.py              # ML model training
│   │       └── youtube_knowledge.py     # YouTube Knowledge agent API
│   ├── core/
│   │   └── config.py                   # All env vars & configuration
│   ├── models/                          # Pydantic models/schemas
│   ├── modules/                         # AI/ML engine modules
│   │   ├── chart_patterns/              # Chart pattern detection
│   │   ├── execution_engine/            # Trade execution logic
│   │   ├── ml_engine/                   # XGBoost/LightGBM ML models
│   │   ├── social_news_engine/          # News + social sentiment
│   │   ├── symbol_universe/             # Dynamic symbol catalog
│   │   └── youtube_agent/               # YouTube transcript analysis
│   ├── schemas/                         # DB schemas
│   ├── services/                        # External data service integrations
│   │   ├── alpaca_service.py            # Alpaca Markets API (orders, bars)
│   │   ├── database.py                  # DuckDB database layer
│   │   ├── finviz_service.py            # Finviz scanner + asset exchange
│   │   ├── fred_service.py              # FRED macro data
│   │   ├── market_data_agent.py         # Market data orchestration agent
│   │   ├── sec_edgar_service.py         # SEC EDGAR filings
│   │   ├── signal_engine.py             # Signal generation tick engine
│   │   └── unusual_whales_service.py    # Unusual Whales flow data
│   ├── strategy/
│   │   └── backtest.py                  # Backtesting engine
│   ├── main.py                          # FastAPI app entry point
│   └── websocket_manager.py             # WebSocket broadcast manager
├── .env.example                         # Environment variable template
├── requirements.txt                     # Python dependencies
├── start.bat                            # Windows start script
├── start_server.py                      # Server startup
└── README.md                            # Backend docs
```

### Frontend: `frontend-v2/`

```
frontend-v2/src/
├── components/
│   ├── charts/                          # Chart components
│   ├── dashboard/                       # Dashboard widgets
│   ├── layout/                          # Layout components
│   ├── ui/                              # UI primitives
│   └── ErrorBoundary.jsx
├── config/                              # Frontend config
├── data/                                # Static data
├── hooks/                               # React custom hooks
├── pages/                               # 18 pages (ALL BUILT by Oleh)
│   ├── AgentCommandCenter.jsx           # AI agent control panel
│   ├── Backtesting.jsx                  # Strategy backtesting UI
│   ├── Dashboard.jsx                    # Main trading dashboard
│   ├── DataSourcesMonitor.jsx           # Live data source health
│   ├── MLInsights.jsx                   # ML model insights
│   ├── OperatorConsole.jsx              # System operator console
│   ├── Patterns.jsx                     # Pattern detection display
│   ├── PerformanceAnalytics.jsx         # Trade performance metrics
│   ├── RiskIntelligence.jsx             # Risk monitoring
│   ├── SentimentIntelligence.jsx        # Market sentiment
│   ├── Settings.jsx                     # App settings
│   ├── SignalHeatmap.jsx                # Signal heatmap visualization
│   ├── Signals.jsx                      # Live trading signals
│   ├── StrategyIntelligence.jsx         # Strategy analysis
│   ├── TradeExecution.jsx               # Order placement UI
│   ├── Trades.jsx                       # Trade history
│   └── YouTubeKnowledge.jsx             # YouTube content analysis
├── services/
│   └── websocket.js                     # WebSocket client
├── App.jsx
└── main.jsx
```

---

## ✅ WHAT OLEH HAS BUILT (v2 branch — verified Feb 23, 2026)

| Area | Status | Details |
|------|--------|---------|
| All 17 frontend pages | ✅ DONE | All pages functional with real API connections |
| WebSocket real-time | ✅ DONE | `websocket_manager.py` + `websocket.js` frontend client |
| 22 API routes (v1/) | ✅ DONE | Full REST API coverage for all features |
| Alpaca integration | ✅ DONE | `alpaca_service.py` — orders, bars, streaming |
| Finviz scanner | ✅ DONE | `finviz_service.py` with asset exchange mapping |
| FRED macro data | ✅ DONE | `fred_service.py` |
| SEC EDGAR | ✅ DONE | `sec_edgar_service.py` |
| Unusual Whales | ✅ DONE | `unusual_whales_service.py` |
| Signal engine | ✅ DONE | `signal_engine.py` with tick-based generation |
| ML engine | ✅ DONE | `modules/ml_engine/` — XGBoost/LightGBM |
| YouTube agent | ✅ DONE | `modules/youtube_agent/` + `youtube_knowledge.py` API |
| Execution engine | ✅ DONE | `modules/execution_engine/` with bracket orders |
| Symbol universe | ✅ DONE | `modules/symbol_universe/` dynamic catalog |
| Backtesting | ✅ DONE | `strategy/backtest.py` + `backtest_routes.py` |
| Email/SMS alerts | ✅ DONE | `alerts.py` API route |
| Risk management | ✅ DONE | `risk.py` API route |
| DuckDB database | ✅ DONE | `database.py` service |
| Chart patterns | ✅ DONE | `modules/chart_patterns/` |

---

## 🔴 WHAT IS MISSING / NEXT TASKS FOR OLEH

### Priority 1: OpenClaw Bridge (MOST CRITICAL)
These services do NOT yet exist in v2 — they need to be created:

**1. `backend/app/services/openclaw_bridge_service.py`** ← DOES NOT EXIST YET
```
Create backend/app/services/openclaw_bridge_service.py.
Fetch JSON from GitHub Gist API using OPENCLAW_GIST_ID and OPENCLAW_GIST_TOKEN env vars.
Parse the OpenClaw scan output: scored_candidates (ticker, composite_score, tier, regime,
whale_flow, technical_data), regime_status (GREEN/YELLOW/RED), macro_context, scan_timestamp.
Cache results for 15 minutes.
Expose: get_scan_results(), get_regime(), get_top_candidates(n=10).
Add new API route: backend/app/api/v1/openclaw.py
```

**2. `backend/app/config.py` — Add missing env vars:**
```
OPENCLAW_GIST_ID=
OPENCLAW_GIST_TOKEN=
```

**3. Frontend updates needed:**
- `Dashboard.jsx` — add OpenClaw regime status widget (GREEN/YELLOW/RED)
- `Signals.jsx` — add OpenClaw composite score column
- `DataSourcesMonitor.jsx` — add OpenClaw bridge health/last sync row

### Priority 2: Replace yfinance (CRITICAL — DO NOT USE yfinance)
- Search codebase for any remaining `import yfinance` or `yf.download` calls
- Replace ALL with `alpaca_service.py` — `get_bars(symbol, timeframe, limit)` already exists
- `alpaca_service.py` already handles real-time data — use it everywhere

### Priority 3: Remove Hardcoded Tickers
- `modules/symbol_universe/` already exists — USE IT as the single source of tickers
- Remove any hardcoded ticker lists from API routes or frontend data files
- All symbol lookups should go through `symbol_universe` module

### Priority 4: Merge v2 → main
- Review open PR (currently 1 PR open)
- Test full pipeline: data fetch → signals → execution
- Merge v2 into main branch

---

## 🖥️ TWO-PC ARCHITECTURE (Feb 2026)

```
ESPENMAIN (Trading PC — Windows 11)          PROFITTRADER (Execution PC)
├── Elite Trader Backend (FastAPI :8000)      ├── Alpaca paper/live orders
├── Elite Trader Frontend (Vite :3000)        ├── Connected via Alpaca API
├── DuckDB (local: backend/data/elitetrader.db)
├── Redis (:6379)
├── OpenClaw bridge (reads from GitHub Gist)
└── start_all.bat → starts all services
```

**OpenClaw Data Flow:**
```
ESPENMAIN (OpenClaw scanner, runs daily 6PM via GitHub Actions)
    → Writes scan results to GitHub Gist JSON
    → Elite Trader openclaw_bridge_service.py reads Gist every 15 min
    → Serves to frontend via /api/v1/openclaw endpoint
    → Dashboard shows regime + top candidates
```

---

## ⚙️ ENVIRONMENT VARIABLES (backend/.env)

```bash
# Tier 1: Price & Flow
FINVIZ_EMAIL=
FINVIZ_PASSWORD=
UNUSUAL_WHALES_API_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Tier 2: Macro & Fundamentals
FRED_API_KEY=
SEC_EDGAR_USER_AGENT=EliteTrader espen@embodier.ai

# Tier 3: Sentiment & Social
STOCKGEIST_API_KEY=
NEWS_API_KEY=
DISCORD_BOT_TOKEN=
TWITTER_BEARER_TOKEN=

# Prediction Markets
KALSHI_API_KEY=
KALSHI_PRIVATE_KEY_PATH=

# AI
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# Infrastructure
REDIS_URL=redis://localhost:6379
DATABASE_URL=duckdb:///backend/data/elitetrader.db

# OpenClaw Bridge (ADD THESE)
OPENCLAW_GIST_ID=
OPENCLAW_GIST_TOKEN=
```

---

## 🚀 STARTUP

```bash
# Backend (ESPENMAIN)
cd backend
start.bat

# Frontend
cd frontend-v2
npm run dev

# Or use root start_all.bat to start everything
```

---

## 📊 OPENCLAW STATUS (for context)

OpenClaw repo: github.com/Espenator/openclaw (247+ commits, 98% Python)

### What OpenClaw Does (already built):
- 15-step daily scanner pipeline with GitHub Actions
- 100-point 5-pillar composite scoring (Regime + Trend + Pullback + Momentum + Pattern)
- 4-layer regime detection (VIX + HMM + Hurst exponent)
- Finviz Elite scanning, Unusual Whales flow, FRED macro context
- Multi-timeframe alignment, AMD pattern detection, sector rotation
- Streaming engine with real-time WebSocket (Alpaca 1-min bars)
- Auto-executor with bracket orders, FOM-based dual targets
- ML ensemble (XGBoost) with 25-feature prediction
- LLM hybrid analysis (local Ollama + Perplexity API)
- Slack bot with /oc commands
- Discord signal monitoring
- Google Sheets trade journal
- TradingView watchlist sync
- API data bridge to GitHub Gist JSON (for Elite Trader)

### OpenClaw Remaining Work (Prompt 8 - Master Integration):
- `risk_governor.py` (portfolio heat, correlation limits, circuit breaker)
- Update `main.py` to async orchestrator
- Live dashboard (Flask web app)
- Pipeline fix checklist (9 issues from Run #71 audit)

---

## 🏗️ TECH STACK

| Layer | Technology |
|-------|------------|
| AI Brain | Anthropic Claude Opus 4.6 via API |
| Local LLM | Ollama + Mistral 7B on RTX 4080 (CUDA) |
| ML Engine | Python 3.13, XGBoost (GPU), LightGBM (GPU), Optuna |
| Backend | FastAPI port 8000, WebSocket, Redis |
| Frontend | React (Vite) + Tailwind, port 3000 |
| Data Sources | Finviz, UW, Alpaca, FRED, SEC EDGAR, Stockgeist, News API, Discord, X, YouTube |
| Execution | Alpaca paper/live, stocks+options+crypto |
| Database | DuckDB + Redis for real-time cache |
| GPU | NVIDIA RTX 4080 16GB VRAM, CUDA 12.1 |

---

---

## 🔧 TOMORROW: .ENV SETUP (ESPENMAIN — NEW PC SETUP)

**Context:** ESPENMAIN-setup.ps1 clones both repos and installs all tools but does NOT create .env files.
The .env files contain all API keys and must be set up manually after cloning.

### Step 1: Elite Trader Backend .env

```powershell
# Navigate to backend
cd C:\Dev\elite-trading-system\backend

# Copy the example env file
copy .env.example .env

# Open in VS Code to fill in keys
code .env
```

**Keys to fill in (get from OneDrive/Trading-Sync/env-configs/ or existing machine):**
- `ALPACA_API_KEY` — from alpaca.markets dashboard
- `ALPACA_SECRET_KEY` — from alpaca.markets dashboard
- `ALPACA_BASE_URL` — https://paper-api.alpaca.markets (paper) or https://api.alpaca.markets (live)
- `FINVIZ_EMAIL` — your Finviz Elite login
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `PERPLEXITY_API_KEY` — from perplexity.ai settings
- `UNUSUAL_WHALES_API_KEY` — from unusualwhales.com
- `DISCORD_TOKEN` — from Discord developer portal
- `DISCORD_CHANNEL_ID` — your signals channel ID
- `SLACK_BOT_TOKEN` — from api.slack.com
- `REDIS_URL` — redis://localhost:6379
- `OLLAMA_BASE_URL` — http://localhost:11434
- `SECRET_KEY` — generate with: python -c "import secrets; print(secrets.token_hex(32))"
- `DATABASE_URL` — duckdb:///./trading.db

### Step 2: OpenClaw .env

```powershell
# Navigate to openclaw
cd C:\Dev\openclaw

# Copy the example env file
copy .env.example .env

# Open in VS Code to fill in keys
code .env
```

**Keys to fill in:**
- `ALPACA_API_KEY` — same as Elite Trader
- `ALPACA_SECRET_KEY` — same as Elite Trader
- `ALPACA_BASE_URL` — same as Elite Trader
- `ANTHROPIC_API_KEY` — same as Elite Trader
- `PERPLEXITY_API_KEY` — same as Elite Trader
- `OLLAMA_BASE_URL` — http://localhost:11434
- `FINVIZ_EMAIL` — same as Elite Trader
- `UNUSUAL_WHALES_API_KEY` — same as Elite Trader
- `DISCORD_TOKEN` — same as Elite Trader
- `DISCORD_CHANNEL_ID` — same as Elite Trader

### Step 3: One-liner to open both .env files at once

```powershell
code C:\Dev\elite-trading-system\backend\.env; code C:\Dev\openclaw\.env
```

### Step 4: Verify .env is loaded correctly

```powershell
# Test Elite Trader backend starts
cd C:\Dev\elite-trading-system\backend
.\venv\Scripts\activate
python -c "from app.core.config import settings; print('Config OK:', settings.ALPACA_API_KEY[:8])"

# Test OpenClaw
cd C:\Dev\openclaw
.\venv\Scripts\activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ALPACA:', os.getenv('ALPACA_API_KEY', 'NOT SET')[:8])"
```

### Notes:
- .env files are gitignored — they will NOT be in the repo, must be copied manually
- Source of truth for keys: OneDrive > Trading-Sync > env-configs > (elite-trader.env / openclaw.env)
- After filling .env, run ESPENMAIN-setup.ps1 again — it will skip already-done steps and just start services

Last updated: February 23, 2026 at 8:00 AM EST by Espen
Next handoff: Oleh picks up Monday February 23, 2026 morning
Focus: Create openclaw_bridge_service.py, add /api/v1/openclaw route, update Dashboard.jsx + Signals.jsx to show OpenClaw data
