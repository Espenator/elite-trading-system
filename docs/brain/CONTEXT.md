# 🧠 ESPEN'S SECOND BRAIN — TRADING ASSISTANT CONTEXT
> **Claude: Read this file at the START of every session before doing anything.**
> Last updated: 2026-03-02

---

## 👤 WHO I AM
- **Name:** Espen Schiefloe
- **App:** Embodier Trader (elite trading system, Python/Streamlit-based)
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

## 🚀 EMBODIER TRADER APP — CURRENT STATE (Audited 2026-03-02)

### Architecture: Full-Stack Trading System (336 files)
```
elite-trading-system/
├── backend/          ← Python FastAPI (20+ API routes, OpenClaw agents, ML engine)
│   ├── app/api/v1/   ← 20 route modules (signals, market, orders, risk, ml_brain...)
│   ├── app/core/     ← Config + Alignment engine (Bible enforcement)
│   ├── app/modules/  ← OpenClaw (multi-agent), ML engine, Social/News, YouTube agent
│   ├── app/services/ ← Alpaca, Finviz, Unusual Whales, FRED, SEC EDGAR
│   └── tests/        ← 22 tests (~4% coverage)
├── frontend-v2/      ← React + Vite + Tailwind (15 pages)
│   ├── src/pages/    ← Dashboard, SignalIntelligence, TradeExecution, Agents...
│   ├── src/hooks/    ← useApi, useWebSocket, useSettings
│   └── src/components/ ← 30+ components (charts, dashboard, UI kit)
└── docs/             ← Mockups, audits, implementation plans
```

### System Health Score: 5.8/10 (40% functional, 60% scaffolding)
- **Backend:** ❌ NOT STARTING (4 critical blockers — see task board)
- **Frontend:** 🟡 75% Complete (all 15 pages wired, some stubs remain)
- **ML Engine:** 🟡 Pipeline solid, training has data leakage bug
- **Tests:** ❌ 4% coverage (need 20%+ for trading system)
- **Docker:** 🟡 Basic but functional

### Top-Quality Modules (9/10)
- `backend/app/api/v1/orders.py` — Production-quality order execution
- `frontend-v2/src/pages/TradeExecution.jsx` — Fully wired trade UI
- `backend/app/modules/ml_engine/outcome_resolver.py` — Clean ML resolution

### Key Integrations
- **Broker:** Alpaca (paper + live)
- **Data:** Finviz Elite, Unusual Whales, FRED, SEC EDGAR, TradingView
- **ML:** XGBoost + LSTM, 30+ features, drift detection
- **Agents:** OpenClaw multi-agent system (scanners, scorers, executors)
- **Real-time:** WebSocket streaming (needs auth)

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
- Code in Python (Streamlit, pandas, yfinance, sklearn, sqlite3)
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
# Test change Mon Mar  2 22:30:40 UTC 2026
