# Embodier.ai (Trading) - V2 Intelligence System
## Branch: v2-15-feb-espen-embodier-ai
## Date: February 15, 2026
## Author: Espen (System Design) | Oleh (Implementation)

---

## CRITICAL DESIGN PHILOSOPHY

This is NOT a trading app. This is a **pure AI intelligence system** that happens to generate trading signals. Think of it as a brain you can see inside of.

### Core Principles:
1. **Glass House (not Black Box)** - The operator (Espen) sees EVERYTHING the AI sees, in real-time
2. **Human as Final Oversight Layer** - The system does the heavy lifting, but the human adds intuitive pattern recognition, veto power, and confirmation
3. **Self-Learning Flywheel** - Gets smarter after every trade, every data ingestion, every Sunday retrain
4. **5 AI Agents Working as a Team** - Each visible, controllable, pausable, with every variable exposed
5. **10 Data Sources** - All with health monitoring, latency tracking, and manual override
6. **Transparency is Non-Negotiable** - Every decision the AI makes must show WHY it made it

---

## FOR OLEH - READ THIS FIRST

Oleh, this branch contains the complete v2 frontend redesign. Every file has detailed comments explaining:
- WHAT it does
- WHY it exists in our architecture
- HOW it connects to the backend API
- WHAT backend endpoint it needs (so you know what to build)

### The UI Must Mirror Our AI Agent Architecture 1:1

Every page in the UI corresponds to a backend module or agent:

| UI Page | Backend Module | Purpose |
|---------|---------------|----------|
| Intelligence Dashboard | All modules | System overview - Espen sees everything at a glance |
| Agent Command Center | /api/v1/agents | Start/stop/pause/configure each of the 5 agents |
| Signal Intelligence | /api/v1/signals | Live signals with 10-source evidence breakdown |
| Signal Heatmap | /api/v1/signals/heatmap | Visual heat grid of signal strength by sector/ticker |
| ML Brain & Flywheel | /api/v1/training + /api/v1/flywheel | See what ML is learning, feature importance, retrain |
| Sentiment Intelligence | /api/v1/sentiment | Combined sentiment from Stockgeist, News API, Discord, X |
| YouTube Knowledge | /api/v1/youtube-knowledge | Transcript ingestion, algo ideas extraction |
| Data Sources Monitor | /api/v1/data-sources | Health of all 10 feeds with latency and record counts |
| Trade Execution | /api/v1/orders | Live execution with operator veto/confirm buttons |
| Risk Intelligence | /api/v1/risk | Position sizing, drawdown limits, correlation matrix |
| Strategy Intelligence | /api/v1/strategy | Active strategies, parameter tuning, A/B testing |
| Backtest Lab | /api/v1/backtest | On-demand and scheduled backtesting |
| Performance Analytics | /api/v1/performance | Equity curve, win rate, Sharpe, by-strategy breakdown |
| Operator Console | /api/v1/system | Master Glass House view - system logs, all agent activity |
| Settings | /api/v1/system/config | All 10 API keys, model configs, schedule settings |

---

## THE 5 AI AGENTS

Each agent runs as an independent process. The UI must show:
- Status (running/paused/stopped/error)
- CPU/Memory usage
- Last action timestamp
- Current task description
- Every configurable variable with a slider/toggle
- Start/Stop/Pause/Restart buttons
- Activity log (scrollable, last 100 actions)

### Agent 1: Market Data Agent
- Scans Finviz Elite, Alpaca, Unusual Whales
- Pulls FRED economic data, SEC EDGAR filings
- Runs every 60s during market hours (configurable)
- Backend: `backend/app/modules/symbol_universe/`

### Agent 2: Signal Generation Agent  
- Takes raw data from Agent 1
- Applies technical analysis, chart patterns, momentum algos
- Generates composite signal scores (0-100)
- Backend: `backend/app/services/signal_engine.py`

### Agent 3: ML Learning Agent
- XGBoost/LightGBM on RTX 4080 GPU via CUDA
- Trains on historical outcomes
- Sunday full retrain (schedulable)
- Flywheel: outcome resolver feeds accuracy back
- Backend: `backend/app/modules/ml_engine/`

### Agent 4: Sentiment Agent
- Aggregates from Stockgeist, News API, Discord, X (Twitter)
- NLP sentiment scoring per ticker
- Unusual sentiment spike detection
- Backend: `backend/app/modules/social_news_engine/`

### Agent 5: YouTube Knowledge Agent
- Ingests transcripts from financial YouTube videos
- Extracts trading ideas, technical analysis concepts
- Feeds into ML feature engineering
- 24/7 self-learning flywheel
- Backend: NEW - `backend/app/modules/youtube_agent/`

---

## 10 DATA SOURCES

| # | Source | Type | API Key Needed | Status |
|---|--------|------|---------------|--------|
| 1 | Finviz Elite | Market Data/Screening | Yes (FINVIZ_API_KEY) | Existing |
| 2 | Alpaca Markets | Execution/Quotes | Yes (ALPACA_API_KEY + SECRET) | Existing |
| 3 | Unusual Whales | Options Flow | Yes (UW_API_KEY) | Existing |
| 4 | FRED API | Economic Indicators | Yes (FRED_API_KEY) | NEW |
| 5 | SEC EDGAR | Company Filings | Free (rate-limited) | NEW |
| 6 | Stockgeist | Sentiment | Yes (STOCKGEIST_API_KEY) | NEW |
| 7 | News API | Headlines/Articles | Yes (NEWS_API_KEY) | NEW |
| 8 | Discord | Social/Community | Yes (DISCORD_BOT_TOKEN) | NEW |
| 9 | X (Twitter) | Social Sentiment | Yes (X_BEARER_TOKEN) | NEW |
| 10 | YouTube | Knowledge/Transcripts | Yes (YOUTUBE_API_KEY) | NEW |

---

## FILE STRUCTURE - WHAT OLEH NEEDS TO BUILD

```
frontend-v2/src/
  config/
    api.js                    -- API base URLs and endpoint map
  hooks/
    useApi.js                 -- Generic fetch hook with polling
    useWebSocket.js           -- Real-time WebSocket connection
    useAgents.js              -- Agent status and control
    useDataSources.js         -- Data source health monitoring
  components/
    layout/
      Layout.jsx              -- REWRITE: Glass House wrapper
      Sidebar.jsx             -- REWRITE: Embodier.ai branding + 15 nav items
      Header.jsx              -- REWRITE: Agent health ticker bar
    shared/
      AgentStatusPill.jsx     -- Reusable agent status indicator
      DataSourceBadge.jsx     -- Reusable source health badge
      GlassHouseBar.jsx       -- Top-level system health strip
      MicroControlSlider.jsx  -- Reusable variable control widget
      OperatorVetoButton.jsx  -- Confirm/Veto action button
  pages/
    Dashboard.jsx             -- REWRITE: Intelligence overview
    AgentCommandCenter.jsx    -- NEW: Micro-control all 5 agents
    SignalIntelligence.jsx    -- REWRITE: 10-source signal feed
    SignalHeatmap.jsx         -- NEW: Replaces Portfolio Heatmap
    MLBrain.jsx               -- REWRITE: Flywheel visualization
    SentimentIntelligence.jsx -- NEW: Multi-source sentiment
    YouTubeKnowledge.jsx      -- NEW: Transcript agent
    DataSourcesMonitor.jsx    -- NEW: 10-feed health dashboard
    TradeExecution.jsx        -- REWRITE: With veto/confirm
    RiskIntelligence.jsx      -- REWRITE: Dynamic risk controls
    StrategyIntelligence.jsx  -- REWRITE: Strategy A/B testing
    BacktestLab.jsx           -- REWRITE: On-demand + scheduled
    PerformanceAnalytics.jsx  -- REWRITE: Deep analytics
    OperatorConsole.jsx       -- NEW: Master Glass House view
    Settings.jsx              -- REWRITE: 10 API keys + configs
  App.jsx                     -- REWRITE: 15 routes
```

---

## OPERATOR OVERSIGHT DESIGN

Espen (the operator) needs to see at ALL times:

1. **Header Bar**: Which agents are running, system health %, active alerts count
2. **Every Signal**: Shows all 10 data sources that contributed + their individual scores
3. **Every Trade Decision**: Has CONFIRM and VETO buttons before execution
4. **ML Learning**: Visual graph of what features the model thinks are important and how they change over time
5. **Flywheel Progress**: A visual showing prediction accuracy improving over time
6. **YouTube Learning**: What concepts were extracted, what new features were added
7. **All Logs**: Scrollable activity feed showing exactly what each agent did and when

The human is the final intelligence layer. The system presents evidence. The human decides.

---

## BRANDING: Embodier.ai (Trading)

The sidebar shows:
- Logo: Embodier.ai with a small "Trading" badge
- Top nav: Link back to main Embodier.ai site
- The main Embodier.ai site will have tabs: Industries | Pricing | Knowledge | Contact | **Trading**
- This app IS the Trading tab content

---

## HOW TO START BUILDING

1. Read this README completely
2. Look at each page file - they have detailed OLEH comments
3. Start with: `config/api.js` and `hooks/useApi.js` (foundation)
4. Then: `Layout.jsx` + `Sidebar.jsx` + `Header.jsx` (shell)
5. Then: `Dashboard.jsx` (main page)
6. Then: Agent Command Center (core Glass House feature)
7. Then: All remaining pages in any order
8. Backend endpoints needed are documented in each page file

Every page has a header comment block like:
```
// OLEH: This page connects to GET /api/v1/agents
// OLEH: It needs WebSocket channel 'agents' for real-time updates  
// OLEH: Backend module: backend/app/modules/[module_name]/
// OLEH: See backend TODO at bottom of this file
```


Lets build the worlds smartest trading intelligence system.

---

## MASTER SYNC STATUS (Updated Feb 15 2026 9PM EST)

### CRITICAL MISMATCHES TO FIX

App.jsx imports files that DO NOT EXIST yet:
- `DataSourcesMonitor` from `./pages/DataSourcesMonitor` -- FILE MISSING, needs creation
- `YouTubeKnowledge` from `./pages/YouTubeKnowledge` -- FILE MISSING, needs creation
- `RiskIntelligence` from `./pages/RiskIntelligence` -- FILE MISSING (we have RiskConfiguration.jsx)
- `StrategyIntelligence` from `./pages/StrategyIntelligence` -- FILE MISSING (we have StrategySettings.jsx)

Files that EXIST but are NOT routed in App.jsx:
- `ScreenerResults.jsx` -- exists but no route in App.jsx
- `TradeExecution.jsx` -- exists but no route (Trades.jsx is routed instead)

### DECISION NEEDED: Rename vs Create

Option A (Rename existing to match App.jsx):
- `RiskConfiguration.jsx` -> rename to `RiskIntelligence.jsx`
- `StrategySettings.jsx` -> rename to `StrategyIntelligence.jsx`
- Create new: `DataSourcesMonitor.jsx` and `YouTubeKnowledge.jsx`

Option B (Update App.jsx to match existing files):
- Change App.jsx import from `RiskIntelligence` to `RiskConfiguration`
- Change App.jsx import from `StrategyIntelligence` to `StrategySettings`
- Still need: `DataSourcesMonitor.jsx` and `YouTubeKnowledge.jsx`

---

## COMPLETE FILE-TO-ROUTE-TO-SIDEBAR-TO-VISILY MAP

| # | JSX File (exists) | App.jsx Route | Sidebar Label | Sidebar Section | Visily Screen | Backend API |
|---|---|---|---|---|---|---|
| 1 | Dashboard.jsx | /dashboard | Intelligence Dashboard | COMMAND | Dashboard | All modules |
| 2 | AgentCommandCenter.jsx | /agents | Agent Command Center | COMMAND | (needs screen) | /api/v1/agents |
| 3 | OperatorConsole.jsx | /operator | Operator Console | COMMAND | (needs screen) | /api/v1/system |
| 4 | Signals.jsx | /signals | Signal Intelligence | INTELLIGENCE | (needs screen) | /api/v1/signals |
| 5 | SignalHeatmap.jsx | /signal-heatmap | Signal Heatmap | INTELLIGENCE | (needs screen) | /api/v1/signals/heatmap |
| 6 | SentimentIntelligence.jsx | /sentiment | Sentiment Intelligence | INTELLIGENCE | (needs screen) | /api/v1/sentiment |
| 7 | DataSourcesMonitor.jsx (MISSING) | /data-sources | Data Sources Monitor | INTELLIGENCE | (needs screen) | /api/v1/data-sources |
| 8 | YouTubeKnowledge.jsx (MISSING) | /youtube | YouTube Knowledge | INTELLIGENCE | (needs screen) | /api/v1/youtube-knowledge |
| 9 | MLInsights.jsx | /ml-insights | ML Brain & Flywheel | ML & ANALYSIS | Model Training & Metrics | /api/v1/training |
| 10 | Patterns.jsx | /patterns | Screener & Patterns | ML & ANALYSIS | (needs screen) | /api/v1/patterns |
| 11 | Backtesting.jsx | /backtest | Backtesting Lab | ML & ANALYSIS | Backtesting Lab | /api/v1/backtest |
| 12 | PerformanceAnalytics.jsx | /performance | Performance Analytics | ML & ANALYSIS | Performance Analytics | /api/v1/performance |
| 13 | Trades.jsx | /trades | Trade Execution | EXECUTION | Trade Execution | /api/v1/orders |
| 14 | RiskConfiguration.jsx | /risk (as RiskIntelligence) | Risk Intelligence | EXECUTION | Risk Configuration | /api/v1/risk |
| 15 | StrategySettings.jsx | /strategy (as StrategyIntelligence) | Strategy Intelligence | EXECUTION | Strategy Settings | /api/v1/strategy |
| 16 | Settings.jsx | /settings | Settings | SYSTEM | Settings | /api/v1/system/config |

Extra files with no App.jsx route:
- `ScreenerResults.jsx` -- legacy, content merged into Patterns.jsx
- `TradeExecution.jsx` -- legacy, content merged into Trades.jsx

---

## VISILY UI/UX DESIGN LINK

Visily Project: https://app.visily.ai/projects/b8aeaef9-c6a5-4386-bf1c-f1d3aaed51f7/boards/2389672

### Current Visily Screens (23 screens on board):
1. Screen 29 (blank placeholder)
2. Embodier Trader - Glass House Intelligence Overview (Dashboard v1)
3. Dashboard (main dashboard)
4. Trade Execution
5. Model Training & Metrics (maps to MLInsights.jsx)
6. Screener Results (maps to Patterns.jsx / ScreenerResults.jsx)
7. Order History & Backtest (maps to Backtesting.jsx)
8. Settings
9. Risk Configuration
10-14. (Signal Fusion Weights, Quantify Analytics, ML Model Control, etc)
15. Backtesting Lab
16. Performance Analytics
17-23. (duplicates and older versions)

### Visily Screens Still Needed:
- Agent Command Center
- Operator Console
- Signal Intelligence
- Signal Heatmap
- Sentiment Intelligence
- Data Sources Monitor
- YouTube Knowledge
- Screener & Patterns (updated from Screener Results)

### Visily Sidebar Menu (must match on ALL screens):
Every screen in Visily must show this EXACT sidebar structure:

COMMAND:
- Intelligence Dashboard
- Agent Command Center
- Operator Console

INTELLIGENCE:
- Signal Intelligence
- Signal Heatmap
- Sentiment Intelligence
- Data Sources Monitor
- YouTube Knowledge

ML & ANALYSIS:
- ML Brain & Flywheel
- Screener & Patterns
- Backtesting Lab
- Performance Analytics

EXECUTION:
- Trade Execution
- Risk Intelligence
- Strategy Intelligence

SYSTEM:
- Settings

### Visily Branding Rules:
- Header: "Embodier Trader" (NOT "Elite Trading Terminal")
- Sidebar logo: Embodier.ai with "Glass House Intelligence" subtitle
- Footer: "(c) 2025 Embodier Trader. All rights reserved."
- Page subtitles: Use the code subtitle text, not "Elite Trading System"

---

## BACKEND API ENDPOINTS NEEDED

All endpoints live under `/api/v1/` prefix.

| Endpoint | Method | Page | Purpose |
|---|---|---|---|
| /api/v1/dashboard | GET | Dashboard | Aggregated overview data |
| /api/v1/agents | GET/POST | Agent Command Center | Agent status and control |
| /api/v1/agents/:id/start | POST | Agent Command Center | Start specific agent |
| /api/v1/agents/:id/stop | POST | Agent Command Center | Stop specific agent |
| /api/v1/system | GET | Operator Console | System logs, all agent activity |
| /api/v1/signals | GET | Signal Intelligence | Live signals with evidence |
| /api/v1/signals/heatmap | GET | Signal Heatmap | Heatmap data by sector/ticker |
| /api/v1/sentiment | GET | Sentiment Intelligence | Multi-source sentiment scores |
| /api/v1/data-sources | GET | Data Sources Monitor | Health of all 10 feeds |
| /api/v1/youtube-knowledge | GET | YouTube Knowledge | Transcript data and ideas |
| /api/v1/training | GET/POST | ML Brain & Flywheel | ML model data and retrain |
| /api/v1/flywheel | GET | ML Brain & Flywheel | Flywheel accuracy metrics |
| /api/v1/patterns | GET | Screener & Patterns | Pattern scan results |
| /api/v1/backtest | GET/POST | Backtesting Lab | Backtest configs and results |
| /api/v1/performance | GET | Performance Analytics | Equity curve, metrics |
| /api/v1/orders | GET/POST | Trade Execution | Order management |
| /api/v1/risk | GET | Risk Intelligence | Position sizing, drawdown |
| /api/v1/strategy | GET/PUT | Strategy Intelligence | Strategy configs, A/B tests |
| /api/v1/system/config | GET/PUT | Settings | All API keys, model configs |

---

## NEXT STEPS CHECKLIST

### Frontend (Priority Order):
1. [ ] Fix App.jsx imports to match actual filenames OR rename files
2. [ ] Create DataSourcesMonitor.jsx (new page)
3. [ ] Create YouTubeKnowledge.jsx (new page)
4. [ ] Update all Visily sidebar menus to match code Sidebar.jsx
5. [ ] Create missing Visily screens for new pages
6. [ ] Replace all "Elite Trading System" text with "Embodier Trader"
7. [ ] Verify all 16 page screens match their JSX code structure

### Backend (Priority Order):
1. [ ] Set up /api/v1/ route prefix
2. [ ] Implement /api/v1/agents endpoint (Agent Command Center)
3. [ ] Implement /api/v1/signals endpoint (Signal Intelligence)
4. [ ] Implement /api/v1/data-sources endpoint (Data Sources Monitor)
5. [ ] Implement /api/v1/youtube-knowledge endpoint (YouTube Knowledge)
6. [ ] Implement /api/v1/sentiment endpoint (Sentiment Intelligence)
7. [ ] Implement all remaining endpoints per table above

### Design (Visily):
1. [ ] Standardize sidebar across all 23 screens
2. [ ] Add 8 missing page screens
3. [ ] Remove duplicate/legacy screens
4. [ ] Ensure all branding is Embodier Trader

Lets build the worlds smartest trading intelligence system.
