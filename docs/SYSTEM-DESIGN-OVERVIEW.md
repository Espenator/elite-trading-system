<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# ELITE TRADER — System Design Overview

**For Oleh | From Espen | February 6, 2026**

***

## What We're Building

Elite Trader is a **24/7 AI-powered signal engine** that scans four data sources, generates thesis-driven trade ideas, and gets smarter with every trade outcome through machine learning. It runs as a Claude AI agent (Anthropic) connected to live market data via MCP protocol. No social features. No gamification. Just the best signal system we can build — starting with one user (me), then scaling to paid subscribers and B2B white-label.

**One sentence:** *An AI agent that watches every market while you sleep, tells you what to trade and why when you wake up, and learns from the result to be smarter tomorrow.*

***

## Architecture (The Whole System)

```
┌──────────────────────────────────────────────────────────────┐
│                    CLAUDE AI AGENT (Anthropic Opus 4.6)       │
│                                                               │
│  Orchestrates all 4 data feeds via MCP tool calls             │
│  Generates plain-English thesis for every signal              │
│  Explains ML confidence in human terms                        │
│  Detects regime shifts that invalidate the model              │
│                                                               │
└─────┬──────────┬──────────────┬──────────────┬───────────────┘
      │          │              │              │
      ▼          ▼              ▼              ▼
┌──────────┐┌──────────┐┌────────────┐┌────────────────┐
│ FINVIZ   ││UNUSUAL   ││  ALPACA    ││  PREDICTION    │
│ ELITE    ││WHALES    ││  MARKETS   ││  MARKETS       │
│          ││          ││            ││                │
│ Universe ││ Options  ││ Real-time  ││ Kalshi API     │
│ filter   ││ flow     ││ price data ││ Polymarket API │
│ Sectors  ││ Dark pool││ Crypto     ││                │
│ Rel vol  ││ Instit.  ││ Historical ││ Event odds as  │
│ Technics ││ Congress ││ News feed  ││ leading        │
│          ││ FDA cal  ││ Options    ││ indicators     │
│          ││          ││            ││ (Fed, earnings,│
│ $25/mo   ││ $55/mo   ││ EXECUTION  ││  macro events) │
│          ││          ││ Paper+Live ││                │
│          ││          ││ 24/5 trade ││ Free APIs      │
│          ││          ││ $0 commis. ││                │
│          ││          ││ $99/mo data││                │
└──────────┘└──────────┘└─────┬──────┘└────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   ML LEARNING      │
                    │   ENGINE           │
                    │                    │
                    │ ┌────────────────┐ │
                    │ │ WEIGHT         │ │
                    │ │ OPTIMIZER      │ │    Bayesian optimization
                    │ │ Shifts factor  │ │    shifts scoring weights
                    │ │ weights based  │ │    toward what's actually
                    │ │ on outcomes    │ │    winning
                    │ └────────────────┘ │
                    │ ┌────────────────┐ │
                    │ │ XGBOOST        │ │    Predicts win probability
                    │ │ CLASSIFIER     │ │    per signal using features
                    │ │ Filters bad    │ │    from all 4 data sources
                    │ │ signals before │ │    (50+ features)
                    │ │ you see them   │ │
                    │ └────────────────┘ │
                    │ ┌────────────────┐ │
                    │ │ PATTERN        │ │    Discovers new cross-source
                    │ │ DETECTOR       │ │    edges humans can't see
                    │ │ Finds new      │ │    (e.g. "dark pool + prediction
                    │ │ edges across   │ │     shift = 72% win rate")
                    │ │ all 4 sources  │ │
                    │ └────────────────┘ │
                    │ ┌────────────────┐ │
                    │ │ OUTCOME        │ │    Every trade result feeds
                    │ │ RESOLVER       │◄├─── back in. Win, loss, R-multiple,
                    │ │ Closes the     │ │    stop hit, target reached.
                    │ │ learning loop  │ │    NO TRADE IS WASTED.
                    │ └────────────────┘ │
                    └────────────────────┘
```


***

## What a Signal Looks Like (The Output)

```
ELITE TRADER SIGNAL — Feb 6, 2026 9:15 AM
───────────────────────────────────────────
TICKER:     CRWD          CONFIDENCE: 87/100
ACTION:     BUY (Swing, 3-10 day hold)
ENTRY:      $388–392      STOP: $371 (2.1R)
TARGET 1:   $412 (1.5R)   TARGET 2: $428 (2.8R)

THESIS: CRWD coiling in 6-day compression near 20 SMA,
declining volume 78% avg — classic Velez setup.

SUPPORTING:
✓ Options flow: 4 call sweeps at $400, $2.1M (UW)
✓ Dark pool: 3 block prints above ask (UW)
✓ Prediction mkts: "Cybersecurity spend up" 79% (Kalshi)
✓ Sector: IGV +2.3% vs SPY this week (Finviz)

RISKS:
✗ Broad sell-off VIX > 22 invalidates
✗ Weak ARR at earnings = compression resolves down
───────────────────────────────────────────
```

Not a blinking ticker. A **complete trade thesis** with entry, stop, target, evidence from all four sources, and risk scenarios — every time.

***

## How the Machine Gets Smarter

| Timeframe | What Happens |
| :-- | :-- |
| **Day 1** | Fixed scoring weights (Velez 30%, Flow 25%, Prediction 20%, Compression 15%, ML 10%). Expert rules. |
| **Month 1** (~50 trades) | Weight optimizer makes first adjustments based on real outcomes. XGBoost trains on initial data. |
| **Month 3** (~150 trades) | XGBoost filters bad signals before they reach the user. ~20% false signal reduction. |
| **Month 6** (~300 trades) | Pattern detector finds cross-source edges. Regime-specific weights emerge (different in bull/bear/chop). |
| **Month 12** (~600 trades) | Full flywheel. Weekly retraining. System knows what works in each regime. Fundamentally different from day 1. |


***

## What Already Exists vs. What We Build

| Component | Status | File |
| :-- | :-- | :-- |
| Finviz scanner | ✅ Built | `finvizscraper.py` |
| Unusual Whales integration | ✅ Built | `unusualwhalesscraper.py` + full API spec |
| Velez scoring engine | ✅ Built | `velezengine.py`, `compositescorer.py` |
| Compression + ignition detection | ✅ Built | `compressiondetector.py`, `ignitiondetector.py` |
| XGBoost model trainer | ✅ Built | `modeltrainer.py` |
| Bayesian weight optimizer | ✅ Built | `weightoptimizer.py` |
| Self-learning flywheel | ✅ Built | `selflearningflywheel.py` |
| Weekly retraining (Sun 11PM) | ✅ Built | `continuouslearner.py` |
| Backtest engine | ✅ Built | `backtestengine.py` |
| Risk management + position sizing | ✅ Built | `positionsizer.py`, `stopcalculator.py` |
| FastAPI backend + WebSocket | ✅ Built | `backend/main.py` (port 8000) |
| Glass House UI (Next.js) | ✅ Built | `glass-house-ui/` (port 3000) |
| **Claude AI agent + MCP wrappers** | 🔨 Build | ~10 lines per tool wrapper, agent prompt |
| **Alpaca API connector** (replaces yFinance) | 🔨 Build | MCP server exists, wire to backend |
| **Prediction market feed** (Kalshi + Polymarket) | 🔨 Build | MCP server exists, add as ML feature |
| **Outcome resolver** (trade result → learning loop) | 🔨 Build | Connects Alpaca trade history → ML |
| **Pattern detector** (cross-source discovery) | 🔨 Build | Feature importance + correlation |

**~70% exists. We build four new connectors and wire them into the existing learning loop.**

***

## Build Order

| Phase | What | Timeline |
| :-- | :-- | :-- |
| **1. Wire data** | MCP tool wrappers for Finviz, UW, Alpaca, prediction markets | Week 1 |
| **2. Build brain** | Claude agent prompt — orchestrates tools, outputs structured thesis | Week 2 |
| **3. Run for Espen** | Scheduled scans → signals to dashboard or Telegram. Paper trading via Alpaca. | Week 3 |
| **4. Close the loop** | Outcome resolver → weight optimizer → XGBoost retrain → pattern detector | Week 4 |

**End of month 1**: Elite Trader runs 24/7, scans 4 sources, delivers AI thesis signals, paper trades via Alpaca, and begins learning from outcomes.

***

## Tech Stack (Final)

| Layer | Technology |
| :-- | :-- |
| **AI Brain** | Anthropic Claude Opus 4.6 via API + MCP tools |
| **ML Engine** | Python 3.13, XGBoost, Bayesian optimization (Optuna) |
| **Backend** | FastAPI (port 8000), WebSocket for real-time |
| **Frontend** | Next.js 14 + TypeScript + Tailwind (port 3000) |
| **Data** | Finviz Elite, Unusual Whales API, Alpaca API, Kalshi/Polymarket APIs |
| **Execution** | Alpaca (paper + live, stocks/options/crypto, \$0 commission, 24/5) |
| **Database** | SQLite → TimescaleDB (for ML feature store + outcome tracking) |
| **Hosting** | Local (`C:\trading-system\`) → cloud when ready to scale |


***

## Business Model (Later, Not Now)

| Phase | Revenue |
| :-- | :-- |
| **Now** | Works for Espen. Proves the signal engine. |
| **6 months** | Invite beta users (\$99-199/mo SaaS). |
| **12 months** | Public launch. B2B white-label for brokers (\$500K+/yr). |

Non-custodial (never touch user funds) = no broker license, no gambling regulation, Stripe-friendly SaaS. Social + gamification layers added later as growth features — not in v1.[^1]

***

**Oleh — questions? Let's discuss and start Week 1.**
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^2][^20][^21][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://www.businessresearchinsights.com/market-reports/social-trading-platform-market-116569

[^2]: Comet-Prompt-v3.0.txt

[^3]: elite-trading-system-480216-99c4b06479d1.json

[^4]: trading-bot@elite-trading-system-48.txt

[^5]: PROJECT_RESUME.txt

[^6]: 📋 __HANDOFF PROMPT FOR COMET ASSISTANT__ (1).md

[^7]: Yaml file.txt

[^8]: file structure.txt

[^9]: velezcode1.txt

[^10]: tradingplan2.pdf

[^11]: velezcode2unknown.txt

[^12]: 
# ✅ Unusual Whales 5-Chart Dashboar.txt

[^13]: Run Premarket.txt

[^14]: tradingplan3.txt

[^15]: sunday-scan-prompt.md

[^16]: tradingplan4.md

[^17]: Never Lie Always Do Each Task Layla Pernament instructions non negotiable.txt

[^18]: tradingsteps5.pdf

[^19]: tradingsteps6.md

[^20]: shortsellingrules.txt

[^21]: oversold bounce workflow.txt

