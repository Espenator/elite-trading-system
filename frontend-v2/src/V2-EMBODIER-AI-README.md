# Embodier.ai (Trading) - V2 Intelligence System
## Branch: v2-15-feb-espen-embodier-ai
## Date: February 15, 2026
## Author: Espen (System Design) | Oleh (Implementation)

---

## CRITICAL DESIGN PHILOSOPHY

This is NOT a trading app. This is a **pure AI intelligence system** that happens to generate trading signals. Think of it as a brain you can see inside of.

### Core Principles:
1. **Transparency (not Black Box)** - the operator (Espen) sees EVERYTHING the AI sees, in real time
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
| Operator Console | /api/v1/system | Master overview - system logs, all agent activity |
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
      Layout.jsx              -- REWRITE: Trading Intelligence wrapper
      Sidebar.jsx             -- REWRITE: Embodier.ai branding + 16 nav items
      Header.jsx              -- REWRITE: Agent health ticker bar
    shared/
      AgentStatusPill.jsx     -- Reusable agent status indicator
      DataSourceBadge.jsx     -- Reusable source health badge
      TradingIntelligenceBar.jsx       -- Top-level system health strip
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
    OperatorConsole.jsx       -- NEW: Master Trading Intelligence view
    Settings.jsx              -- REWRITE: 10 API keys + configs
  App.jsx                     -- REWRITE: 16 routes
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
6. Then: Agent Command Center (core Trading Intelligence feature)
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
2. Embodier Trader - Trading Intelligence Overview (Dashboard v1)
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
- Sidebar logo: Embodier.ai with "Trading Intelligence" subtitle
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
4. | | Update all Visily sidebar menus to match code Sidebar.jsx (5 sections: COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM)
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
5. 5. | | Remove all "Trading Intelligence" text from all screens
6. | | Fix sidebar menus on screens 11-21 to match Sidebar.jsx 16-page structure

Lets build the worlds smartest trading intelligence system.

---

## 🚨 CRITICAL HANDOFF FOR OLEH - FEBRUARY 16, 2026

### Status: Espen going to bed (Sunday 10 PM EST) - Oleh taking over Monday morning

---

## 📍 CURRENT PROJECT STATE

### What's Working ✅
- Frontend-v2 React app structure (Vite + Tailwind)
- Sidebar.jsx with 16-page navigation (updated 1 hour ago)
- Basic page components exist: Dashboard, Signals, Trades, MLInsights, Patterns, Settings
- Backend FastAPI skeleton in place
- Finviz + Alpaca services operational
- DuckDB database service working

### What's Broken/Missing ❌
- **6 Visily screens** have OLD sidebar (Elite Terminal branding, wrong menu)
- **3 critical pages** don't exist yet: DataSourcesMonitor.jsx, YouTubeKnowledge.jsx, OperatorConsole.jsx  
- **10 backend services** need building (FRED, SEC EDGAR, Unusual Whales, etc.)
- **ML Engine** (80 features, XGBoost/LightGBM)
- **3 AI Agents** (Market Data, ML Inference, Signal Generator)
- **WebSocket** real-time updates
- **API endpoints** - only skeleton exists

---

## 🎨 VISILY UI/UX STATUS

### Visily Project Link
**URL:** https://app.visily.ai/projects/b8aeaef9-c6a5-4386-bf1c-f1d3aaed51f7

### Screen Status (15 screens total)

| # | Screen Name | Sidebar Status | Branding | Action Needed |
|---|-------------|----------------|----------|---------------|
| 1 | Intelligence Dashboard | ✅ CORRECT | Embodier Trader | None |
| 2 | ML Brain & Flywheel | ❌ OLD | Elite Terminal | Fix sidebar |
| 3 | Screener & Patterns | ❌ OLD | Elite Terminal | Fix sidebar |
| 4 | Signal Intelligence | ❌ OLD | Elite Terminal | Fix sidebar |
| 5 | Settings | ❌ OLD | Elite Terminal | Fix sidebar |
| 6 | Risk Intelligence | ✅ CORRECT | Embodier.ai | None |
| 7 | Strategy Intelligence | ❌ OLD | Elite Terminal | Fix sidebar |
| 8 | Performance Analytics | ❌ OLD | Elite Terminal | Fix sidebar |
| 9 | Sentiment Intelligence | ⚠️ PARTIAL | - | Content only |
| 10 | Signal Heatmap | ⚠️ PARTIAL | - | Technical panel |
| 11 | Trade Execution | ✅ CORRECT | Embodier Trader | None |
| 12 | Backtesting Lab | ⚠️ PARTIAL | - | Needs review |
| 13 | Data Sources Monitor | ❌ MISSING | - | CREATE NEW |
| 14 | YouTube Knowledge | ❌ MISSING | - | CREATE NEW |
| 15 | Operator Console | ❌ MISSING | - | CREATE NEW |

### Visily Task: Fix 6 Pages with OLD Sidebar

**Pages needing sidebar updates:** 2, 3, 4, 5, 7, 8

**Correct Sidebar Structure (from Sidebar.jsx):**
```
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
```

**How to fix in Visily:**
1. Use "Trade Execution" or "Intelligence Dashboard" page as template (both have correct sidebar)
2. Copy sidebar container from correct page
3. Navigate to page with old sidebar (e.g., "ML Brain & Flywheel")
4. Delete old sidebar
5. Paste correct sidebar
6. Test in Presenter mode (▶️ button)
7. Repeat for all 6 pages

---

## 🛠️ UI IMPROVEMENTS OLEH CAN MAKE

### 1. Agent Command Center (CRITICAL - Missing Page)
**Why it matters:** Core feature - operator needs to control all 5 AI agents

**What to build:**
- 5 agent status cards showing: Market Data Agent, ML Inference Agent, Signal Generator Agent, Sentiment Agent, YouTube Knowledge Agent
- Each card shows: Status (running/paused/stopped), CPU%, RAM%, Last Activity timestamp
- Start/Stop/Pause/Resume buttons per agent  
- Live activity log (scrollable, last 100 actions)
- Configuration sliders (e.g., "fetch_interval: 60s")

**Claude Code Prompt:**
```
Create frontend-v2/src/pages/AgentCommandCenter.jsx following the pattern in Dashboard.jsx.
Show 5 agent cards in a grid. Each card needs real-time status from GET /api/v1/agents.
Add Start/Stop/Pause buttons that POST to /api/v1/agents/:id/start, /stop, /pause.
Include a live activity feed scrollable container showing agent.last_actions array.
Use WebSocket channel 'agents' for real-time updates.
Styling: glassmorphism cards, cyan accents, dark theme matching existing pages.
```

### 2. Data Sources Monitor (CRITICAL - Missing Page)
**Why it matters:** Operator needs to see health of all 10 data feeds

**What to build:**
- 10 source status cards in 3 tiers:
  - TIER 1: Finviz, Unusual Whales, Alpaca, Polymarket, Kalshi
  - TIER 2: FRED, SEC EDGAR
  - TIER 3: Stockgeist, News API, Discord, X/Twitter
- Each shows: Status (green/yellow/red dot), Last Fetch time, Latency ms, Record count
- "Refresh Now" button per source
- FRED Macro Dashboard section showing: Fed Rate, CPI, Yield Curve, Unemployment, Regime
- SEC Filings section showing recent 8-K and Form 4 filings

**Claude Code Prompt:**
```
Create frontend-v2/src/pages/DataSourcesMonitor.jsx.
Fetch GET /api/v1/data-sources for all 10 source statuses.
Display 3-tier layout: TIER 1 (5 sources), TIER 2 (2 sources), TIER 3 (4 sources).
Each source card shows: name, status dot (green=online, red=offline), latency_ms, last_fetch timestamp, record_count.
Add FRED Macro Dashboard section with GET /api/v1/data-sources/fred/regime.
Add SEC Filings section with GET /api/v1/data-sources/edgar/filings.
WebSocket channel 'datasources' for live status updates.
```

### 3. YouTube Knowledge (NEW Feature - Missing Page)
**Why it matters:** Self-learning AI that extracts trading ideas from YouTube

**What to build:**
- Transcript ingestion status
- List of extracted trading ideas/concepts
- "Add Video" form (paste YouTube URL)
- Show new ML features added from YouTube content

**Claude Code Prompt:**
```
Create frontend-v2/src/pages/YouTubeKnowledge.jsx.
Fetch GET /api/v1/youtube-knowledge for transcript data.
Show: video_title, channel, transcript_status (processing/completed), extracted_ideas array.
Add form with input field + "Add Video" button that POSTs to /api/v1/youtube-knowledge.
Display new_features_added array showing ML features created from video content.
```

### 4. ML Brain & Flywheel (NEEDS ENHANCEMENT)
**What's missing:**
- 80-feature importance chart (bar chart showing which features matter most)
- Flywheel visualization (accuracy improving over time graph)
- Regime detection display (risk-on/risk-off/transition indicator)
- Retrain trigger button with progress bar

**Claude Code Prompt:**
```
Enhance frontend-v2/src/pages/MLInsights.jsx.
Add GET /api/v1/ml/feature-importance endpoint call.
Create horizontal bar chart showing top 20 features by importance score.
Add line chart for flywheel showing prediction_accuracy over last 30 days.
Add regime indicator card showing current macro_regime from FRED.
Add "Retrain Model" button that POSTs to /api/v1/ml/retrain with loading state.
```

### 5. Signal Intelligence (NEEDS 10-SOURCE EVIDENCE)
**What's missing:**
- Evidence breakdown panel for each signal showing contribution from ALL 10 sources
- Claude thesis display in plain English
- ML confidence meter with probability

**Claude Code Prompt:**
```
Enhance frontend-v2/src/pages/Signals.jsx (rename from current basic version).
For each signal, add expandable Evidence Panel showing:
  - finviz_score, unusual_whales_flow, fred_macro_regime
  - sec_insider_activity, stockgeist_sentiment, news_velocity
  - discord_consensus, twitter_spike, prediction_market_odds, ml_confidence
Add "Claude Thesis" section showing signal.thesis_text in a card.
Add confidence meter visual (0-100) showing signal.confidence.
```

### 6. Sentiment Intelligence (NEW COMBINED VIEW)
**What to build:**
- Combined sentiment gauge (0-100) merging Stockgeist + News + Discord + X
- Per-source breakdown cards
- Trending tickers by social velocity
- Latest headlines from News API

**Claude Code Prompt:**
```
Create frontend-v2/src/pages/SentimentIntelligence.jsx.
Fetch GET /api/v1/sentiment/:ticker.
Show combined_score gauge (0-100) at top.
Display 4 source cards:
  - Stockgeist: score, volume, bull_bear_ratio
  - News API: count_24h, velocity, sentiment
  - Discord: analyst_consensus, mention_count
  - X/Twitter: mentions, velocity, influencer_count
Add Trending Tickers section showing top 10 by social velocity.
```

### 7. Operator Console (MASTER VIEW - Missing Page)
**Why it matters:** Espen's "god mode" dashboard to see EVERYTHING

**What to build:**
- All 5 agents status in mini-cards (top row)
- All 10 data sources health (middle row)
- Live signal feed (scrolling, last 10 signals)
- System logs (scrolling, last 50 actions)
- "PAUSE ALL" emergency button

**Claude Code Prompt:**
```
Create frontend-v2/src/pages/OperatorConsole.jsx.
This is the master overview page combining:
  - GET /api/v1/agents (5 agent mini-cards)
  - GET /api/v1/data-sources (10 source status indicators)
  - GET /api/v1/signals?latest=10 (live feed)
  - GET /api/v1/system/logs (scrolling log viewer)
Add "PAUSE ALL AGENTS" button that POSTs to /api/v1/agents/pause-all.
WebSocket channels: 'agents', 'datasources', 'signals', 'logs' for live updates.
Layout: 3 rows (agents, sources, signals+logs side by side).
```

### 8. Trade Execution (NEEDS VETO/CONFIRM BUTTONS)
**What's missing:**
- Before trade execution: CONFIRM ✓ / VETO ✗ buttons
- Show all supporting evidence before operator decides

**Claude Code Prompt:**
```
Enhance frontend-v2/src/pages/Trades.jsx.
When signal.action = 'BUY' or 'SELL', before executing:
  - Show modal with full signal evidence
  - Add CONFIRM button (green) → POST /api/v1/orders {action: 'confirm'}
  - Add VETO button (red) → POST /api/v1/orders {action: 'veto'}
  - Show position sizing from Risk Intelligence
```

### 9. WebSocket Service (CRITICAL INFRASTRUCTURE)
**Create:** `frontend-v2/src/services/websocket.js`

**Claude Code Prompt:**
```
Create frontend-v2/src/services/websocket.js WebSocket client.
Connect to ws://localhost:8000/ws.
Channels: 'agents', 'datasources', 'signals', 'trades', 'logs'.
Auto-reconnect on disconnect (3 second delay).
Export: ws.on(channel, handler), ws.emit(channel, data), ws.disconnect().
```

### 10. Real-Time Indicators Throughout UI
**Add to all pages:**
- Pulsing dot when WebSocket connected (top right)
- "Last updated: 3s ago" timestamps on data cards
- Loading skeletons while fetching

---

## 🔧 BACKEND BUILD ORDER FOR OLEH

### Phase 1: Services (build each as a standalone file)

| # | File | Service | API Used | Time Est |
|---|------|---------|----------|----------|
| 1 | services/fredservice.py | FRED API | https://api.stlouisfed.org | 1.5 hrs |
| 2 | services/secedgarservice.py | SEC EDGAR | https://efts.sec.gov | 1.5 hrs |
| 3 | services/unusualwhalesservice.py | Unusual Whales | https://api.unusualwhales.com | 1.5 hrs |
| 4 | services/newsapiservice.py | News API | https://newsapi.org/v2 | 1.5 hrs |
| 5 | services/stockgeistservice.py | Stockgeist | https://api.stockgeist.ai | 1.5 hrs |
| 6 | services/twitterservice.py | X/Twitter | Twitter API v2 | 1.5 hrs |
| 7 | services/discordservice.py | Discord | discord.py | 1.5 hrs |
| 8 | services/polymarketservice.py | Polymarket | https://data-api.polymarket.com | 1.5 hrs |
| 9 | services/kalshiservice.py | Kalshi | https://trading-api.kalshi.com | 1 hr |

### Phase 2: ML Engine

| # | File | Purpose | Time Est |
|---|------|---------|----------|
| 10 | modules/mlengine/features.py | 80-feature extraction from all 10 sources | 2 hrs |
| 11 | modules/mlengine/models.py | XGBoost + LightGBM with GPU/CUDA | 2 hrs |
| 12 | modules/mlengine/trainer.py | Training pipeline | 2 hrs |
| 13 | modules/mlengine/inference.py | Prediction engine | 1.5 hrs |

### Phase 3: Agents

| # | File | Purpose | Time Est |
|---|------|---------|----------|
| 14 | agents/base.py | BaseAgent ABC class | 1.5 hrs |
| 15 | agents/marketdataagent.py | Fetches from all 10 sources | 2 hrs |
| 16 | agents/mlagent.py | ML inference via GPU | 1.5 hrs |
| 17 | agents/signalagent.py | Claude thesis generation | 2 hrs |
| 18 | agents/manager.py | Agent orchestration + API | 1 hr |
| 19 | agents/outcomeresolveragent.py | Trade outcome learning loop | 2 hrs |

### Phase 4: API + Frontend

| # | File | Purpose | Time Est |
|---|------|---------|----------|
| 20 | api/agents.py | Agent control endpoints | 1 hr |
| 21 | api/datasources.py | Data source health endpoints | 1 hr |
| 22 | api/signals.py + ml.py | Signal + ML endpoints | 2 hrs |
| 23 | frontend services/api.js + websocket.js | API client + WebSocket | 1 hr |
| 24 | 3 new pages + 5 enhanced pages | UI pages from section above | 8 hrs |

**Total estimate: ~40 hours backend, ~10 hours frontend**

---

## 🎯 OLEH PRIORITY ORDER (Do This First)

### Monday Morning (Day 1):
1. **Read this entire README** (15 min)
2. **Fix App.jsx** - rename files to match imports OR update imports to match files
3. **Create DataSourcesMonitor.jsx** (empty shell with mock data)
4. **Create YouTubeKnowledge.jsx** (empty shell with mock data)
5. **Create OperatorConsole.jsx** (empty shell with mock data)
6. **Create websocket.js** service
7. **Run `npm run dev`** - app should boot with all 16 routes working

### Monday Afternoon (Day 1):
8. **Start backend: fredservice.py** (copy pattern from finvizservice.py)
9. **Build secedgarservice.py**
10. **Build unusualwhalesservice.py**
11. **Update config.py** with all API key environment variables

### Tuesday-Wednesday (Days 2-3):
12. Build remaining 6 data services
13. Build ML engine (features.py, models.py, trainer.py, inference.py)
14. Build 3 agents (base, market data, ml inference)

### Thursday-Friday (Days 4-5):
15. Build signal generator agent with Claude integration
16. Build all API endpoints
17. Enhance frontend pages with real data
18. Fix 6 Visily sidebar screens

---

## 💻 TECH STACK REFERENCE

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

## 🔑 ENVIRONMENT VARIABLES NEEDED

Create `backend/.env` with:
```
# TIER 1: Price & Flow
FINVIZ_EMAIL=
FINVIZ_PASSWORD=
UNUSUAL_WHALES_API_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# TIER 2: Macro & Fundamentals  
FRED_API_KEY=
SEC_EDGAR_USER_AGENT=EliteTrader espen@embodier.ai

# TIER 3: Sentiment & Social
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
```

---

Last updated: February 15, 2026 at 10:00 PM EST by Espen
Next handoff: Oleh picks up Monday February 16, 2026 morning
