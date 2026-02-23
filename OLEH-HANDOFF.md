# OLEH HANDOFF - Agent Command Center + Full Wiring Instructions

**From:** Espen (via AI architecture review)  
**Date:** Monday Feb 23, 2026  
**Priority:** 🚨 Read this FIRST before starting any work

---

## 🎯 TL;DR: Build the Agent Command Center

The OpenClaw backend bridge is **COMPLETE** (11 endpoints, Gist polling, 15min cache). Your mission this week: **transform the Embodier Trader frontend into an Agent Command Center** - a glass-box dashboard where Espen sees EVERYTHING the OpenClaw agents see in real-time.

---

## ✅ BACKEND STATUS: COMPLETE

### Files Already Committed to v2

| File | Status | Description |
|------|--------|-------------|
| `services/openclaw_bridge_service.py` | ✅ DONE | Gist polling, 15min cache, typed accessors |
| `api/v1/openclaw.py` | ✅ DONE | 11 endpoints: /scan, /regime, /top, /health, /whale-flow, /fom, /llm, /sectors, /memory, /memory/recall, /refresh |
| `core/config.py` | ✅ DONE | OPENCLAW_GIST_ID + OPENCLAW_GIST_TOKEN |
| `main.py` | ✅ DONE | Router registered at /api/v1/openclaw |
| `services/market_data_agent.py` | ✅ DONE | OpenClaw as 6th data source |
| `services/signal_engine.py` | ✅ DONE | 60/40 blending + regime multipliers |

### Test the Bridge (Monday First Thing)

```bash
# 1. Pull latest v2
git checkout v2 && git pull

# 2. Add to .env
OPENCLAW_GIST_ID=your_gist_id_here
OPENCLAW_GIST_TOKEN=ghp_your_token_here

# 3. Start backend
cd backend && python -m uvicorn app.main:app --port 8001 --reload

# 4. Test endpoints
curl http://localhost:8001/api/v1/openclaw/health
curl http://localhost:8001/api/v1/openclaw/regime
curl http://localhost:8001/api/v1/openclaw/top?n=5
```

---

## 🏗️ AGENT COMMAND CENTER: Frontend Components

### Component Architecture

```
App.jsx
├── Header.jsx
│   └── RegimeBanner.jsx (NEW - always visible regime status)
├── Sidebar.jsx
├── Dashboard.jsx
│   ├── RegimeCard.jsx (NEW - detailed regime info)
│   ├── TopCandidatesCard.jsx (NEW - top 5 from OpenClaw)
│   └── BridgeHealthCard.jsx (NEW - OpenClaw connection status)
├── ClawBotPanel.jsx (NEW PAGE - main command center)
│   ├── LiveScoresTable.jsx (NEW - all candidates sortable)
│   ├── WhaleFlowPanel.jsx (NEW - unusual options)
│   ├── LLMSummaryCard.jsx (NEW - AI analysis)
│   └── FOMExpectedMoves.jsx (NEW - options levels)
├── AgentCommandCenter.jsx (ENHANCE - agent status)
│   ├── AgentSwarmPanel.jsx (NEW - heartbeat status)
│   └── BlackboardViewer.jsx (NEW - message feed)
└── Signals.jsx (ENHANCE - add OpenClaw columns)
```

---

## 🤖 CLAUDE CODE 1-DAY BLITZ — Tuesday Feb 24

> **Tools:** Claude Code (CLI) + Claude Opus 4.6 Thinking model
> **Repo:** `elite-trading-system` on `v2` branch
> **Method:** Each session = one Claude Code prompt. Paste it in, let Claude run autonomously, review + commit.
> **Goal:** Entire ClawBot Control Panel designed, built, coded, and wired to live API by end of day.

---

### SESSION 1 — Morning (9–11am): Dashboard Foundation + Regime Banner

**Paste this into Claude Code:**

```
You are working in the elite-trading-system repo on the v2 branch. The frontend lives in frontend-v2/ and uses React + Tailwind CSS. The backend is already running at localhost:8001 with 11 OpenClaw endpoints wired.

Do ALL of the following:

1. Create frontend-v2/src/components/layout/RegimeBanner.jsx
   - Fetches GET /api/v1/openclaw/regime every 60s
   - Colored banner: GREEN=bg-green-500, YELLOW=bg-yellow-500, RED=bg-red-500, fallback=bg-gray-700
   - Shows: regime state label, VIX, HMM confidence %, Hurst exponent, scan date
   - Graceful error/loading states

2. Wire RegimeBanner into the existing Header component (Header.jsx or equivalent)
   - Import and render <RegimeBanner /> at the top

3. Create frontend-v2/src/components/dashboard/RegimeCard.jsx
   - Props: { regime } — shows state, VIX, hmm_confidence (as %), hurst, regime.readme
   - bg-slate-800 card, grid layout

4. Create frontend-v2/src/components/dashboard/TopCandidatesCard.jsx
   - Props: { candidates } — table of top 5: symbol, composite_score, tier (SLAM=yellow-400, HIGH=green-400, TRADEABLE=blue-400, WATCH=gray-400), suggested_entry price

5. Create frontend-v2/src/components/dashboard/SectorRotationCard.jsx
   - Fetches GET /api/v1/openclaw/sectors on mount
   - Ranked list of sectors: name, ETF, pct_change (green if positive, red if negative), status badge (HOT/COLD/NEUTRAL)

6. Update Dashboard.jsx (or wherever the main dashboard lives)
   - useEffect fetches /regime, /top?n=5, /health in parallel via Promise.all, refreshes every 60s
   - Renders: RegimeCard, TopCandidatesCard, SectorRotationCard, and inline BridgeHealthCard (connected bool, candidate_count, cache_age, last_scan_timestamp)
   - Page heading: "Agent Command Center"

Use the existing api service import pattern from other components. Tailwind CSS. No TypeScript.
```

---

### SESSION 2 — Late Morning (11am–1pm): ClawBot Command Center Page

**Paste this into Claude Code:**

```
Continuing in elite-trading-system/frontend-v2 on v2 branch. Do ALL of the following:

1. Create frontend-v2/src/pages/ClawBotPanel.jsx — this is the MAIN command center page
   - On mount + every 60s, fetch all 5 in parallel:
     GET /api/v1/openclaw/regime
     GET /api/v1/openclaw/top?n=20
     GET /api/v1/openclaw/whale-flow
     GET /api/v1/openclaw/llm
     GET /api/v1/openclaw/fom
   - "Force Refresh" button: POST /api/v1/openclaw/refresh then re-fetch all data
   - Layout:
     * Full-width regime banner at top (state, VIX, HMM%, Hurst, scan date, regime.readme)
     * Below: 3-column grid (lg:grid-cols-3)
     * LEFT (col-span-2): "Scored Candidates" table with columns:
       Symbol | Score | Tier (badge) | Entry $ | Stop $ (red text) | Whale (bull/bear emoji) | Trend | Pullback | Momentum
     * RIGHT (col-span-1): Whale Flow alerts (top 10: ticker, sentiment colored, premium in $M) + LLM AI Summary card
   - tierBadge helper: SLAM=bg-yellow-500 text-black, HIGH=bg-green-500, TRADEABLE=bg-blue-500, WATCH=bg-gray-500
   - Loading spinner while fetching, error state on failure

2. Create frontend-v2/src/pages/SectorRotationPage.jsx
   - Fetches GET /api/v1/openclaw/sectors
   - Full-page table: Rank, Sector, ETF, % Change (colored), Status badge (HOT=red, COLD=blue, NEUTRAL=gray), Volume Ratio

3. Add routes in App.jsx:
   path="/clawbot" -> <ClawBotPanel />
   path="/sectors" -> <SectorRotationPage />

4. Add nav items to Sidebar.jsx (place near top, prominently):
   { path: '/clawbot', label: '🦖 ClawBot', icon: 'claw' }
   { path: '/sectors', label: '🏦 Sectors', icon: 'chart' }
```

---

### SESSION 3 — Afternoon (1–3pm): Memory Intelligence + Agent Status

**Paste this into Claude Code:**

```
Continuing in elite-trading-system/frontend-v2 on v2 branch. Do ALL of the following:

1. Create frontend-v2/src/pages/MemoryIntelligencePage.jsx
   - Fetches GET /api/v1/openclaw/memory on mount
   - Top section: Memory IQ score (large number 0-100, colored: >70 green, 40-70 yellow, <40 red)
   - Quality metrics: freshness, coverage, confidence as progress bars or colored values
   - Agent Leaderboard: top 5 agents table (source, win_rate %, trade count)
   - Expectancy Overview: decay_weighted_wr, expectancy value
   - Ticker Recall Lookup: text input + "Recall" button
     Calls GET /api/v1/openclaw/memory/recall?ticker={input}&score=50&regime=UNKNOWN
     Shows: recent_context table (source, setup, score, regime, won, pnl_pct), learned_rules list, structured_facts (signals, total_pnl_pct, avg_score)

2. Create frontend-v2/src/components/agents/AgentSwarmPanel.jsx
   - Fetches GET /api/v1/openclaw/health every 30s
   - Shows: Bridge connected (green/red dot + label), Gist configured (check/x), candidate count, cache age (Xs / TTLs), last scan timestamp
   - Find the existing AgentCommandCenter page and import this component there

3. Add route: path="/memory" -> <MemoryIntelligencePage />
   Add sidebar nav: { path: '/memory', label: '🧠 Memory IQ', icon: 'brain' }
```

---

### SESSION 4 — Late Afternoon (3–5pm): Signals Enhancement + App Rename + Polish

**Paste this into Claude Code:**

```
Continuing in elite-trading-system/frontend-v2 on v2 branch. Do ALL of the following:

1. SIGNALS ENHANCEMENT: Find the Signals page/component (Signals.jsx or similar)
   - Add useEffect: fetch GET /api/v1/openclaw/scan on mount
   - Build scoreMap: { [symbol]: { composite_score, tier, trend_score, pullback_score, momentum_score } }
   - Add 2 new columns to signals table: "Claw Score" and "Tier"
   - Look up each signal's symbol in scoreMap, use same tier badge colors

2. APP RENAME to "Embodier Trader":
   - Search all .jsx, .tsx, .html, .json files in frontend-v2/ for any old app name
   - Replace with "Embodier Trader" everywhere: package.json name, index.html <title>, any headings

3. CONNECTION STATUS INDICATOR:
   - Add a green/red dot to Header or Sidebar showing OpenClaw bridge connection status
   - Polls GET /api/v1/openclaw/health every 30s, shows dot based on .connected field

4. FULL AUDIT of all new components:
   - Missing imports (useEffect, useState, api service)
   - Null/undefined guards (use optional chaining ?.)
   - Loading states ("Loading..." while fetching)
   - Error states (catch blocks that set error state)
   - Fix anything broken

5. CORS CHECK: In backend/app/main.py, confirm CORS middleware allows frontend origin (localhost:3000 or localhost:5173). Add if missing.

6. Verify ALL routes exist in App.jsx:
   / -> Dashboard (Agent Command Center)
   /clawbot -> ClawBotPanel
   /sectors -> SectorRotationPage
   /memory -> MemoryIntelligencePage

7. Search frontend-v2/src for any TODO or placeholder text in new components, replace with real wired values.
```

---

## ✅ END-OF-DAY CHECKLIST (Feb 24)

| # | Component | Session | What to verify |
|---|-----------|---------|----------------|
| 1 | `RegimeBanner.jsx` | S1 | GREEN/YELLOW/RED banner visible in header |
| 2 | `RegimeCard.jsx` | S1 | Dashboard shows regime state + VIX + HMM |
| 3 | `TopCandidatesCard.jsx` | S1 | Dashboard shows top 5 candidates |
| 4 | `SectorRotationCard.jsx` | S1 | Dashboard shows sector rankings |
| 5 | `Dashboard.jsx` wired | S1 | "Agent Command Center" heading, 3 cards |
| 6 | `ClawBotPanel.jsx` | S2 | Full command center: candidates table + whale flow + LLM |
| 7 | `SectorRotationPage.jsx` | S2 | Full-page sector table with status badges |
| 8 | Sidebar nav (ClawBot, Sectors) | S2 | Links work, pages render |
| 9 | `MemoryIntelligencePage.jsx` | S3 | Memory IQ score + ticker recall lookup works |
| 10 | `AgentSwarmPanel.jsx` | S3 | Health/connection status on agent page |
| 11 | Sidebar nav (Memory IQ) | S3 | Link works, page renders |
| 12 | Signals.jsx + Claw Score cols | S4 | Two new columns show scores from OpenClaw |
| 13 | App rename → "Embodier Trader" | S4 | Title, package.json, headings updated |
| 14 | Connection status dot | S4 | Green/red dot in header or sidebar |
| 15 | CORS + audit + polish | S4 | No console errors, all data loading |

---

## 🔗 API ENDPOINT REFERENCE

| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | `/api/v1/openclaw/scan` | Full scan payload |
| GET | `/api/v1/openclaw/regime` | Market regime + details |
| GET | `/api/v1/openclaw/top?n=10` | Top N candidates |
| GET | `/api/v1/openclaw/health` | Bridge connection status |
| GET | `/api/v1/openclaw/whale-flow` | Whale flow alerts |
| GET | `/api/v1/openclaw/fom` | FOM expected moves |
| GET | `/api/v1/openclaw/llm` | LLM analysis summary |
| GET | `/api/v1/openclaw/sectors` | Sector rankings |
| GET | `/api/v1/openclaw/memory` | Memory IQ, agent rankings, expectancy |
| GET | `/api/v1/openclaw/memory/recall?ticker=AAPL` | 3-stage recall for ticker |
| POST | `/api/v1/openclaw/refresh` | Force cache refresh |

---

## 📊 TIER COLOR CODING

| Tier | Score | Color | Meaning |
|------|-------|-------|---------|
| SLAM | 90+ | 🟡 Gold | Highest conviction |
| HIGH | 80-89 | 🟢 Green | Strong setup |
| TRADEABLE | 70-79 | 🟦 Blue | Valid entry |
| WATCH | 50-69 | ⚪ Gray | Monitor only |
| NO_DATA | <50 | ⚫ Dark | Insufficient data |

---

## 🔧 ENV SETUP

```bash
# Add to backend/.env
OPENCLAW_GIST_ID=abc123def456...   # GitHub Gist ID
OPENCLAW_GIST_TOKEN=ghp_xxxxx...  # GitHub PAT with gist scope
```

---

Questions? Slack Espen or email espen@embodier.ai

Last updated: Feb 23, 2026 — 1-day Claude Code + Opus 4.6 Thinking sprint (all Feb 24)

---

## OPENCLAW CODE AUDIT (Feb 23, 2026)

**Audited by:** Perplexity AI Architecture Review
**Repo:** `Espenator/openclaw` (main branch, 291 commits)
**Total Python files:** 42+ files, 4 folders, 2 GitHub Actions workflows
**Total LOC:** ~15,000+ lines of Python across all modules

### REPOSITORY STRUCTURE

```
openclaw/
  .github/workflows/          # CI/CD
    daily-scanner.yml          # Scheduled daily scan pipeline
    discord-monitor.yml        # Discord channel monitoring
  clawbots/                    # NEW: Tier 5 Apex Predator agents
    meta_agent_alchemist/      # ToT reasoning + DPO fine-tuning
      SOUL.md                  # Agent soul/personality config
      skills.py                # Alchemist skill definitions
    __init__.py
    agent_apex_orchestrator.py # Master swarm orchestrator
    agent_relative_weakness.py # Hunter-Killer weakness scanner
    agent_short_basket_compiler.py # Short basket execution formatter
    meta_agent_architect.py    # Meta-agent architect
    risk_governor.py           # Risk governance layer
  pine/                        # Pine Script indicators
    fom_expected_moves_indicator.pine
  world_intel/                 # NEW: World Intelligence Sensorium
    __init__.py
    sensorium.py               # v1.0 world intelligence layer
```

### FILE-BY-FILE AUDIT

| File | Version | Lines | Status | Notes |
|------|---------|-------|--------|-------|
| `config.py` | v6.0 | 501 | DONE | Apex Predator Swarm config, .env hierarchy, Issue #2 fixed |
| `main.py` | v2.0 | 383 | DONE | Pipeline orchestrator, preflight checks, bridge integration |
| `daily_scanner.py` | v3.1 | 723 | DONE | 21-step pipeline with LLM hybrid, Issue #7 fix committed |
| `app.py` | v2.0 | - | DONE | Slack bot + Flask API + /oc commands |
| `composite_scorer.py` | v5.0 | 855 | DONE | Tier 2 Blackboard scoring, 5-pillar + ML + FOM |
| `ensemble_scorer.py` | v5.1 | 1104 | DONE | XGBoost Tier 2 agent, Issue #6 fixed (data leakage, drift) |
| `streaming_engine.py` | v6.0 | 1587 | DONE | 4-Agent Options Flow Pipeline, Pub/Sub Blackboard |
| `auto_executor.py` | v2.0 | 503 | DONE | Tier 3 Execution Agent, Issue #1 closed |
| `memory.py` | - | - | DONE | Adaptive feedback loop, Issue #3 fixed (recency, sync) |
| `memory_v3.py` | v3.0 | 1773 | DONE | SQLite+ChromaDB hybrid, causal graph, alpha decay |
| `llm_client.py` | v1.1 | 649 | DONE | Ollama+Perplexity hybrid, Issue #5 fixed (rate limit, cache) |
| `api_data_bridge.py` | v1.4 | 385 | DONE | Gist JSON bridge, memory+recalls+sectors to Gist |
| `whale_flow.py` | v5.0 | - | DONE | Tier 1 Blackboard publisher |
| `uw_agents.py` | v1.0 | 679 | DONE | 6-agent UW auto-spawning swarm |
| `alpaca_client.py` | v2.1 | - | DONE | LLM pre-trade risk check |
| `position_manager.py` | v2.0 | - | DONE | Regime-aware stops, partial exits, circuit breaker |
| `position_sizer.py` | v2.0 | - | DONE | Real Alpaca equity, Kelly criterion, regime scaling |
| `smart_entry.py` | v1.0 | - | DONE | VWAP limit orders, session timing, entry scoring |
| `performance_tracker.py` | - | - | DONE | Issue #7 fixed (atomic writes, UUID IDs, memory sync) |
| `technical_checker.py` | v2.2 | - | DONE | VWAP, RSI divergence, Issue #4 referenced |
| `hmm_regime.py` | v2.0 | - | DONE | Joblib cache, multi-seed, regime smoothing |
| `regime.py` | - | - | DONE | VIX+VELEZ regime detection |
| `macro_context.py` | - | - | DONE | FRED API macro indicators |
| `sector_rotation.py` | - | - | DONE | IEX feed for free tier Alpaca |
| `mtf_alignment.py` | - | - | DONE | Weekly/Daily/4H/1H structure scoring |
| `dynamic_weights.py` | - | - | DONE | Bayesian weight optimization (Optuna) |
| `lora_trainer.py` | - | 68 | DONE | DPO fine-tuning, Llama-3-8B, 4-bit quant |
| `lstm_bridge_service.py` | - | 412 | DONE | Elite LSTM -> OpenClaw Redis bridge |
| `finviz_scanner.py` | - | - | DONE | PAS v8 Gate presets |
| `fom_expected_moves.py` | - | - | DONE | FOM expected move levels + cache |
| `discord_listener.py` | - | - | DONE | UW/FOM/Maverick Discord channels |
| `amd_detector.py` | - | - | DONE | AMD pattern detection, IEX feed |
| `pullback_detector.py` | - | - | DONE | Fibonacci retracement + volume |
| `rebound_detector.py` | - | - | DONE | Capitulation volume + reversal |
| `short_detector.py` | - | - | DONE | Bearish pattern detection |
| `earnings_calendar.py` | - | - | DONE | Earnings date safety filter |
| `session_monitor.py` | - | - | DONE | 1H intraday candle monitoring |
| `signal_parser.py` | - | - | DONE | Multi-format trade signal parser |
| `sheets_logger.py` | - | - | DONE | Google Sheets trade journal |
| `tradingview_watchlist.py` | - | - | DONE | TV watchlist sync |

### GITHUB ISSUES STATUS

| Issue | Title | Status | Fix Committed |
|-------|-------|--------|---------------|
| #1 | auto_executor.py - Import Error & Missing Memory | CLOSED | Yes |
| #2 | config.py - Type Safety, Validation & Missing Defaults | OPEN | Yes (2h ago) |
| #3 | memory.py - Close Flywheel Loop & Recency Weighting | OPEN | Yes (2h ago) |
| #4 | pullback_detector.py & technical_checker.py - Error Handling | OPEN | Partial |
| #5 | llm_client.py - Rate Limiting, Response Caching | OPEN | Yes (1h ago) |
| #6 | ensemble_scorer.py - Data Leakage, Feature Drift | OPEN | Yes (1h ago) |
| #7 | daily_scanner.py & performance_tracker.py - Robustness | OPEN | Yes (1h ago) |
| #8 | [APEX] Convergence Blueprint | OPEN | Architecture doc |

### BRIDGE WIRING STATUS (Elite v2 <-> OpenClaw)

| Component | Location | Status |
|-----------|----------|--------|
| `openclaw_bridge_service.py` | elite-trading-system/v2 | DONE (288 lines, 11 methods) |
| `openclaw.py` API routes | elite-trading-system/v2 | DONE (156 lines, 11 endpoints) |
| `api_data_bridge.py` | openclaw/main | DONE (v1.4, Gist JSON export) |
| Memory Intelligence parsers | bridge_service | DONE (get_memory_status, get_memory_recall) |
| Sector Rankings parser | bridge_service | DONE (get_sector_rankings) |
| LLM Summary parser | bridge_service | DONE (get_llm_summary, get_llm_candidate_analysis) |

### WHAT OLEH NEEDS TO BUILD (Feb 24 Sprint)

All backend wiring is COMPLETE. The frontend Agent Command Center needs:

1. **Regime Dashboard Widget** - reads `/api/v1/openclaw/regime`
2. **Top Candidates Table** - reads `/api/v1/openclaw/top`
3. **Whale Flow Panel** - reads `/api/v1/openclaw/whale-flow`
4. **FOM Expected Moves** - reads `/api/v1/openclaw/fom`
5. **LLM Analysis Card** - reads `/api/v1/openclaw/llm`
6. **Sector Rotation Heatmap** - reads `/api/v1/openclaw/sectors`
7. **Memory IQ Dashboard** - reads `/api/v1/openclaw/memory`
8. **Ticker Recall Panel** - reads `/api/v1/openclaw/memory/recall?ticker=AAPL`
9. **Health/Status Indicator** - reads `/api/v1/openclaw/health`
10. **Manual Refresh Button** - POST `/api/v1/openclaw/refresh`

### VERDICT

OpenClaw is a production-grade multi-agent trading intelligence platform with 42+ Python modules, Pub/Sub Blackboard architecture, XGBoost ML scoring, hybrid LLM analysis, and comprehensive bridge wiring to Elite Trading System v2. All critical issues have fix commits. The codebase is ready for the Feb 24 frontend sprint.
