# OLEH HANDOFF - Monday Feb 23, 2026

**From:** Espen (via AI review)
**Date:** Sunday Feb 22, 2026 9:00 PM EST
**Priority:** Read this FIRST before starting any work

---

## TL;DR

Your work on v2 is excellent - 86 commits, all 17 pages, 22 API routes, 8 backend services. The #1 priority this week is connecting OpenClaw to Embodier Trader via a bridge service. OpenClaw is our AI brain; Embodier Trader (renamed from Elite Trader) is the dashboard/UI.

---

## WHAT YOU'VE BUILT (Verified Feb 22)

| Area | Status | Files |
|------|--------|-------|
| 17 frontend pages | DONE | All in frontend-v2/src/pages/ |
| App.jsx router | DONE | 4 sections, 16 routes, error boundary |
| Layout (Header/Sidebar/Layout) | DONE | components/layout/ |
| WebSocket real-time | DONE | websocket.js + websocket_manager.py |
| 8 backend services | DONE | alpaca, finviz, fred, sec_edgar, unusual_whales, database, signal_engine, market_data_agent |
| 22 API routes (v1/) | DONE | All in backend/app/api/v1/ |
| Toast notifications | DONE | react-toastify integrated |
| Component library | DONE | charts/, dashboard/, ui/ |

---

## WHAT'S MISSING - YOUR TASKS THIS WEEK

### DAY 1 (Monday Feb 24) - OpenClaw Bridge Backend - MOST CRITICAL

**Create:** `backend/app/services/openclaw_bridge_service.py`

This file does NOT exist yet. It connects OpenClaw's scan results to our frontend.

```python
# What this file needs to do:
# 1. Fetch JSON from GitHub Gist API using OPENCLAW_GIST_ID and OPENCLAW_GIST_TOKEN env vars
# 2. Parse OpenClaw scan output: scored_candidates, regime_status, macro_context, scan_timestamp
# 3. Cache results for 15 minutes
# 4. Expose: get_scan_results(), get_regime(), get_top_candidates(n=10)
```

**Create:** `backend/app/api/v1/openclaw.py`

```python
# Endpoints needed:
# GET /api/v1/openclaw/scan - returns all scored candidates
# GET /api/v1/openclaw/regime - returns GREEN/YELLOW/RED status
# GET /api/v1/openclaw/top - returns top 10 candidates by composite score
# GET /api/v1/openclaw/health - returns bridge status and last sync time
```

**Update:** `backend/app/core/config.py` - add these env vars:
```
OPENCLAW_GIST_ID=
OPENCLAW_GIST_TOKEN=
```

**Estimated time:** 4-6 hours

---

### DAY 2 (Tuesday Feb 25) - Frontend OpenClaw Widgets

**Update Dashboard.jsx:**
- Add regime status card at top (GREEN/YELLOW/RED with color coding)
- Show top 5 OpenClaw candidates with composite scores
- Add last scan timestamp

**Update Signals.jsx:**
- Add OpenClaw composite score column
- Add tier badge column (SLAM 90+ / HIGH 80+ / TRADEABLE 70+ / WATCH 50+)

**Update DataSourcesMonitor.jsx:**
- Add OpenClaw bridge health row (last sync time, status, candidate count)

**Estimated time:** 4-5 hours

---

### DAY 3 (Wednesday Feb 26) - yfinance Removal + Symbol Universe

**Search and replace across entire codebase:**
- Find all `import yfinance` or `yf.download` calls
- Replace with `alpaca_service.py` -> `get_bars(symbol, timeframe, limit)` which already exists
- Wire `modules/symbol_universe/` as single source of tickers - remove any hardcoded ticker lists

**Estimated time:** 3-4 hours

---

### DAY 4 (Thursday Feb 27) - ClawBot Panel

**Create:** New component or page `ClawBotPanel.jsx`
- Shows live OpenClaw candidates from /api/v1/openclaw/top
- Sorted by composite score
- Click candidate -> pre-populates TradeExecution.jsx with entry/stop/target
- Add persistent regime banner to Header.jsx (always visible at top of app)

**Estimated time:** 5-6 hours

---

### DAY 5 (Friday Feb 28) - Integration Testing + v2 to main merge

- End-to-end test: OpenClaw scan -> Gist -> bridge -> Dashboard displays data
- Fix any CORS / auth issues
- Clean up open PR, resolve conflicts
- Merge v2 into main branch

**Estimated time:** 3-4 hours

---

## HOW THE INTEGRATION WORKS

```
OpenClaw Pipeline (runs daily 6PM via GitHub Actions)
    |
    v
api_data_bridge.py -> pushes scored JSON to GitHub Gist
    |
    v
GitHub Gist (public JSON endpoint)
    |
    v
Embodier Trader Backend (FastAPI :8000)
    openclaw_bridge_service.py [YOU CREATE THIS]
        polls Gist every 15 min
        /api/v1/openclaw endpoints
    |
    v
Embodier Trader Frontend (React :3000)
    Dashboard.jsx -> Regime widget + top candidates
    Signals.jsx -> Composite score column
    DataSourcesMonitor.jsx -> Bridge health
```

---

## THE BIG PICTURE: ClawBot-First UX Redesign

We are renaming "Elite Trader" to "Embodier Trader". OpenClaw becomes the AI brain; Embodier Trader is the UI/dashboard.

| Page | Current Role | New ClawBot-First Role |
|------|-------------|------------------------|
| Dashboard | Generic stats | OpenClaw Command Center - regime + top candidates + heat gauge |
| Signals | Internal signal_engine | OpenClaw scored candidates sorted by tier |
| MLInsights | Internal XGBoost | OpenClaw ensemble_scorer SHAP breakdown |
| StrategyIntelligence | Strategy management | OpenClaw dynamic_weights - Bayesian pillar weights by regime |
| RiskIntelligence | Internal risk | OpenClaw risk_governor - portfolio heat + correlation matrix |
| AgentCommandCenter | Internal agents | ClawBot control - start/stop scan, execution queue |
| TradeExecution | Manual order entry | Pre-populated from ClawBot candidates |
| PerformanceAnalytics | Trade history | OpenClaw performance_tracker R-multiples |

**Pages that stay Embodier Trader native (complement OpenClaw):**
- Backtesting.jsx - deeper historical backtesting
- YouTubeKnowledge.jsx - YouTube agent (unique to ET)
- SentimentIntelligence.jsx - news/social sentiment layer
- Patterns.jsx - chart pattern display (visual layer)
- Settings.jsx - system configuration

---

## WEEK 2 TASKS (Mar 2-7)

1. Rename app to "Embodier Trader" across all files (app title, header, sidebar)
2. Create ClawBot.jsx main page with:
   - Live regime status from OpenClaw
   - Top 10 candidates ranked by composite score
   - One-click "Queue for Execution" button
   - /oc scan trigger button
3. Wire RiskIntelligence.jsx to OpenClaw portfolio heat + correlation
4. Wire MLInsights.jsx to OpenClaw ensemble_scorer breakdown
5. Wire PerformanceAnalytics.jsx to OpenClaw performance_tracker

---

## IMPORTANT NOTES

1. **Branch:** All work on `v2` branch
2. **OpenClaw repo:** github.com/Espenator/openclaw (247+ commits, see NEXT_STEPS.md there)
3. **Gist JSON format** from OpenClaw api_data_bridge.py contains: scored_candidates, regime_status, macro_context, scan_timestamp
4. **DO NOT use yfinance anywhere** - use alpaca_service.py for all market data
5. **No hardcoded tickers** - use symbol_universe module
6. **.env setup instructions** are at the bottom of V2-EMBODIER-AI-README.md

---

## OPENCLAW STATUS (for context)

OpenClaw has 7 completed prompt modules (streaming_engine, pullback_detector, rebound_detector, short_detector, dynamic_weights, ensemble_scorer, auto_executor). Prompt 8 (Master Integration) still needs risk_governor.py and async main.py update - Espen is handling those.

The api_data_bridge.py already pushes scan data to a GitHub Gist. Your bridge service just needs to READ that Gist.

---

Questions? Slack Espen or email espen@embodier.ai

Last updated: Feb 22, 2026 9:00 PM EST
