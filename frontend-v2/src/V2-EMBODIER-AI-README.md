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
