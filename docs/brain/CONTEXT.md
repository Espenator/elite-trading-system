# 🧠 ESPEN'S SECOND BRAIN — TRADING ASSISTANT CONTEXT
> **Claude: Read this file at the START of every session before doing anything.**
> Last updated: March 10, 2026

---

## 👤 WHO I AM
- **Name:** Espen Schiefloe
- **App:** Embodier Trader (elite trading system — FastAPI backend, React frontend, Electron desktop)
- **Trading style:** Price-structure trader — structure FIRST, indicators confirm
- **Markets:** Crypto (spot & futures), Equities, Forex, Options
- **Core markets always monitored:** QQQ, SPY, BTC, ETH, TQQQ, SPXL, NVDA, GOOG

---

## 🎯 MY TRADING BIBLE (Core Rules — Never Override)

### Structure Rules
- **LONG setups:** Only from LONG scan — requires HH/HL structure
- **SHORT setups:** Only from SHORT scan — requires LL/LH structure
- **Indicators DESCRIBE structure, never override it**
- **Entry:** Only at structurally meaningful points (zone retests, structural breaks)
- **Stop-loss:** Precise structural invalidation (beyond the swing/zone defining the thesis)

### Risk Rules
- Max **5% per position**
- Max **2% daily loss** (hard stop for the day)
- **3% trailing stop** on all trades
- Max **5 open positions** simultaneously
- Minimum **2:1 R:R** before entry
- Scale out: **50% at 1R**, **50% at 2R**
- VIX regime adjusts position size — never changes structural logic

### Scanner Thresholds (Finviz Elite)
- Volume > 500k
- Price > $10
- Fractal score ≥ 40 (signals), ≥ 60 (elite setups)
- Vol score ≥ 50 for elite

---

## 🚀 EMBODIER TRADER APP — CURRENT STATE (Audited March 10, 2026)

### Architecture: Full-Stack Trading System
```
elite-trading-system/
├── backend/          ← Python FastAPI (34 API routes, 35-agent council, 68+ services)
│   ├── app/api/v1/   ← 34 route modules (signals, market, orders, council, alignment, risk, ml_brain...)
│   ├── app/council/  ← 35-agent DAG (7 stages), CouncilGate, arbiter, weight_learner
│   ├── app/core/     ← Config, message bus
│   ├── app/modules/  ← OpenClaw, ML engine, Social/News, YouTube agent
│   ├── app/services/ ← llm_clients (Ollama, Perplexity, Claude), firehose, scouts, scanning, trading, Alpaca, Finviz, FRED, SEC EDGAR, etc.
│   └── tests/        ← 666 tests passing
├── brain_service/    ← gRPC + Ollama (local LLM); part of 3-tier router
├── desktop/          ← Electron app (BUILD-READY); service orchestrator, backend manager
├── frontend-v2/      ← React + Vite + Tailwind (15 pages); WebSocket active, 5 pages wired
│   ├── src/pages/    ← Dashboard, SignalIntelligence, TradeExecution, Agents...
│   ├── src/hooks/    ← useApi, useWebSocket, useSettings
│   └── src/components/ ← Charts, dashboard, UI kit
└── docs/             ← Mockups, audits, implementation plans
```

### System Health (March 10, 2026)
- **Backend:** ✅ Operational (auth Bearer token fail-closed, WebSocket, startup resolved)
- **Frontend:** ✅ 15 pages wired; WebSocket active on 5 pages
- **Desktop:** ✅ BUILD-READY (Electron)
- **Council:** 35-agent DAG, 7 stages; SignalEngine → CouncilGate → Council → OrderExecutor
- **LLM:** 3-tier router (Ollama → Perplexity → Claude). Ollama handles most routine calls; Claude used for 6 deep-reasoning tasks: strategy_critic, strategy_evolution, deep_postmortem, trade_thesis, overnight_analysis, directive_evolution
- **Tests:** 666 passing (CI green)
- **Auth:** Bearer token, fail-closed
- **Redis:** Used for caching/sessions where applicable

### Top-Quality Modules
- `backend/app/api/v1/orders.py` — Production-quality order execution (alignment gate)
- `frontend-v2/src/pages/TradeExecution.jsx` — Fully wired trade UI
- `backend/app/council/` — 35-agent council, CouncilGate, Bayesian weight learning
- `backend/app/services/llm_router.py` + `llm_clients/` — 3-tier LLM routing

### Key Integrations
- **Broker:** Alpaca (paper + live)
- **Data:** Finviz Elite, Unusual Whales, FRED, SEC EDGAR (no yfinance)
- **ML:** XGBoost + LSTM, 30+ features, drift detection
- **Agents:** 35-agent council; OpenClaw legacy; discovery (TurboScanner, HyperSwarm, 12 Scout agents)
- **Real-time:** WebSocket active; Bearer token auth

### GitHub
- **Repo:** https://github.com/Espenator/elite-trading-system (public)
- **Local clone:** `Trading/elite-trading-system/`
- **Full audit:** `elite-trading-system/ANALYSIS-SUMMARY.txt`

---

## 📊 ACTIVE WATCHLIST
> Update this section each session using brain_tools.py

*(Load from database: `python3 .brain/brain_tools.py watchlist`)*

---

## 🗓️ CURRENT OPEN POSITIONS
> Update this section each session

*(Load from database: `python3 .brain/brain_tools.py positions`)*

---

## 📈 RECENT PERFORMANCE SNAPSHOT
> Update weekly

*(Load from database: `python3 .brain/brain_tools.py performance`)*

---

## 🔬 ACTIVE MARKET RESEARCH / HYPOTHESES
> Update as views change

*(Load from database: `python3 .brain/brain_tools.py research --active`)*

---

## 🛠️ APP DEV — PRIORITY TASK BOARD
> Embodier Trader development backlog

*(Load from database: `python3 .brain/brain_tools.py tasks --status backlog,in_progress`)*

---

## 💡 HOW CLAUDE SHOULD BEHAVE EACH SESSION

### On startup (every session):
1. **Read this file** (CONTEXT.md)
2. **Run:** `python3 .brain/brain_tools.py session-summary` to load live data
3. Ask: *"What are we working on today — trading, app dev, or research?"*

### When helping with trades:
- Always apply the Trading Bible rules
- Flag any setup that violates risk rules BEFORE proceeding
- Journal every completed trade using brain_tools.py
- Structure analysis language: HH/HL/LL/LH, clean zones, CHOCH, conviction

### When helping with app dev:
- Check app_tasks in the database first
- Code in Python (FastAPI, pandas, sklearn, DuckDB) or React/JS for frontend
- Always write production-quality, well-commented code
- Save significant code changes to git

### When doing market research:
- Save to research table via brain_tools.py
- Tag with instrument, category, timeframe_relevant
- Rate conviction: HIGH / MEDIUM / LOW

### Memory updates:
- After EVERY session, update this CONTEXT.md with key changes
- Log session notes via brain_tools.py

---

## 🔧 BRAIN TOOLS QUICK REFERENCE

```bash
# Session management
python3 .brain/brain_tools.py session-summary
python3 .brain/brain_tools.py new-session

# Trade journal
python3 .brain/brain_tools.py add-trade
python3 .brain/brain_tools.py trades --last 10
python3 .brain/brain_tools.py performance

# Watchlist
python3 .brain/brain_tools.py watchlist
python3 .brain/brain_tools.py add-watch SYMBOL "thesis"

# Research notes
python3 .brain/brain_tools.py research --active
python3 .brain/brain_tools.py add-research "title" "content"

# App dev tasks
python3 .brain/brain_tools.py tasks
python3 .brain/brain_tools.py add-task "title" "description" --priority high

# Market levels
python3 .brain/brain_tools.py levels SYMBOL
python3 .brain/brain_tools.py add-level SYMBOL 450.00 resistance "Daily resistance"
```

---

## 📅 DAILY ROUTINE (Structure-First Trading Day)

### Pre-Market (Before 9:00)
- [ ] Load CONTEXT.md + session summary
- [ ] Check SPY/QQQ/BTC structure on daily + 4H
- [ ] Check VIX level → adjust position sizing
- [ ] Run Finviz Elite scan → LONG list + SHORT list
- [ ] Check Unusual Whales flow for conviction signals
- [ ] Update watchlist with top 3-5 setups
- [ ] Set key S/R levels for the day

### Active Session (9:30 - 16:00 / crypto: all day)
- [ ] Only trade from pre-market watchlist (no FOMO entries)
- [ ] Confirm structure alignment on 2 timeframes before entry
- [ ] Log entry with thesis before executing
- [ ] Scale out at 1R (50%) and 2R (50%)
- [ ] Hard stop at 2% daily loss

### Post-Market / EOD
- [ ] Journal all trades (wins AND losses)
- [ ] Note: did I follow the rules? Y/N
- [ ] Update open positions in CONTEXT.md
- [ ] Capture 1-2 lessons learned
- [ ] Update app dev task board if worked on code

---
*Second Brain v1.0 | Built by Claude for Espen Schiefloe | Embodier Trader*
