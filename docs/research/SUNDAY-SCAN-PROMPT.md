# SUNDAY SCAN: CLAUDE AI SUPER PROMPT FOR SWING MOMENTUM TRADING

**Objective:**
Run a comprehensive Sunday scan for high-probability swing and momentum trading setups for the coming week using best practices from Espen's integrated Velez system, all available watchlists, Finviz/Unusual Whales/TradingView workflows, and state-of-the-art academic insights on swing and momentum trading.

---

## CONTEXT
- **Trader:** Espen | $800K account | Swing/momentum style | 5-system Velez Trading Plan (1-15 day holds, strict risk management)
- **Platform:** Google Sheets dashboard, TradingView (Enhanced Velez v2.0), Finviz Elite, Unusual Whales, Smart Trading Club
- **Reference docs:** Daily Memory Restoration, Sunday Scan Guide, Crash Protection Protocol, Finviz Screener Automation, Unusual Whales 5-Chart Dashboard, Master Watchlist, and all supporting PDFs/txts.

---

## PROMPT TO PASTE INTO CLAUDE (edit [date/values] before running)

---

> **RESTORE MEMORY & FULL CONTEXT**
> Load Google Sheets "🧠 AI Memory Bank" (tab), the Master Watchlist, and all supporting reference docs. Recall the 5-system structure, regime rules matrix (Green/Yellow/Red/Red Recovery), entry/exit logic, and all constraints (esp. the 6-Question Zone Checklist and position sizing).

---

## STEP-BY-STEP SUNDAY SCAN SEQUENCE

1. **UPDATE MARKET CONDITIONS**
    - Input latest VIX, Breadth (Adv/Dec), HY Spread (from Finviz/Smart Trading Club)
    - Calculate current trading regime (Green <20 VIX, Yellow 20-30, Red >30, Red Recovery VIX>30 + RSI>40)
    - Set risk per trade, max positions, and allocation per regime as per system rules

2. **WEEKLY HIGHER-TIMEFRAME ANALYSIS**
    - For SPY, QQQ, Sectors (XLK, XLE, XLF, XLV):
        - Assess weekly position vs 20-week SMA, volume profile, 52W highs/lows, broad market support/resistance
        - Note market phase (accumulation, markup, distribution, markdown)
    - For all: Color-code macro bias (🟢 bullish / 🟡 neutral / 🔴 bearish)

3. **ORDER FLOW & WHALE ACTIVITY SCAN**
    - Open Unusual Whales, run the 5-Chart Dashboard
    - Top signals: Whale buy alerts ($250K+), SPY/QQQ hedge flow, dark pool accumulation/distribution, sector rotation, watchlist updates
    - Watch for contrarian signals (e.g., massive put/hedge activity or VIX spikes at market turning points)
    - Rate order flow for each candidate: 🟢 bullish / 🔴 bearish / 🔄 contrarian / ⚪ neutral

4. **RUN SCREENERS (FINVIZ/MASTER WATCHLIST)**
    - Use pre-built screeners:
        - "Quality_Momentum_Swing": Price above 50/200 MA, RSI 55-70, volume 2x avg, >$10, < $200, FA quality; prioritize top 10 by 5D/10D perf vs SPY
        - "Mean_Reversion_Bounce": RSI 25-40, above 20 MA but below 50 MA, volume up, quality positive
        - "Quality_Shorts": Bear setups for Red regime only
    - Export top 10 from each, cross-reference against Master Watchlist

5. **CANDIDATE RANKING — 3-LAYER CONFIRMATION**
    - For each candidate:
        - Layer 1: Confirm HTF bias aligns (weekly macro + daily tactical)
        - Layer 2: Institutional order flow rating (Whale/DP confirmation)
        - Layer 3: Velez Score (Enhanced Indicator: SMA alignment, RSI/Williams %R, elephant/tail bar, volume confirmation)
    - Score setups:
        - 🟢 SLAM DUNK: 80-100 Velez + all 3 layers confirmed
        - 🔵 STRONG GO: 70-79 Velez + at least 2 layers confirmed
        - 🟡 WATCH: 50-69 mixed
        - ⚪️ SKIP: <50 or no confirmation

6. **FOR TOP 3 SETUPS: APPLY ZONE CHECKLIST**
    - For each:
        1. Edge confirmed (Velez ≥ 70, 2 timeframes aligned)?
        2. ATR stop and position size calculated (per regime)?
        3. Risk accepted (OK with defined loss)?
        4. No hesitation (mechanical execution)?
        5. Profit plan (trailing stop and R-multiple defined)?
        6. Entry reason journaled BEFORE execution?
    - If any NO, skip the trade.

7. **BUILD ENTRY/STOP/TARGET PLAN**
    - Entry: Current/trigger price
    - ATR-based stop: 2.5x ATR (momentum) or 2x ATR (reversion)
    - Target: Set T1 (1R), T2 (2R), T3 (3R)
    - Position size: (Account × risk %) ÷ (entry-stop)
    - Scale-in plan: 33% at entry, 33% on confirmation, 34% on breakout/vol surge
    - Note any special conditions (earnings, macro events)

8. **UPDATE DASHBOARD & ALERTS**
    - Update Google Sheets (regime tab, watchlist Velez scores/layers)
    - Configure TradingView alerts for:
        - All entries, stops, profit targets
        - Regime/crash protocol (VIX spike, HY spread, whale flow reversals)

9. **SUMMARY VISUAL (BUBBLE FORMAT)**
    - Recap regime, VIX, breadth, allocations
    - List top 3 trades with full plan (entry, stop, targets, size)
    - List watch candidates and any high-priority alerts

10. **END OF SCAN: CHECKLIST**
    - Final review: Are all constraint rules, regime settings, and candidate checks met?
    - Ready for Monday open. If not — fix before going live. Otherwise: EXECUTE.

---

### IMPORTANT RESEARCH-DRIVEN ADDITIONS (2024-2025 EVIDENCE)
1. **Dynamic Volatility Scaling:** Use VIX/ATR-based position sizing multiplier. (Full = VIX < 20, reduce ≥ 20, minimal > 30, adjust max size)
2. **Quality Factor:** For momentum: Only trade stocks with ROE>15%, Debt/Equity<0.5, YoY improving margin, and positive cash flow. Exempt mean reversion.
3. **Hold Time Flex:** Extend winners up to 15-30+ days ONLY if trend strength (ADX rising/volume strong) and no negative divergence. Exit early on 3-day volume decline or RSI divergence.
4. **Crash Protection Triggers:** If HY spread >700bps, VIX > 40 or major negative breadth events = exit all momentum trades, switch to mean reversion only (System 5, Red Recovery regime).
5. **Backtest/Walk-Forward Validation:** Review all system parameters, live vs backtest every quarter for drift, adapt as needed.

---

## SYSTEM COMPONENTS (KEY DEFINITIONS)
- **Momentum Breakout:** Price above resistance, confirmed by vol > 1.5x avg, positive MACD cross, RSI >60 (<85)
- **Volatility Contraction Pattern (VCP):** Mark Minervini pattern of higher lows, tighter ranges before breakout; surge in vol is trigger
- **20/50/200 SMA (Velez):** Uptrend only if 20>50>200; flat 200SMA best (ideal for explosive moves)
- **Williams %R:** Overbought/oversold momentum filter (<-80 = buy zone; >-20 = short/fade)
- **Elephant Bar:** Large conviction bar (body 70%+ of bar, >1.3x average range)

---

## OUTPUT (ACTIONABLE DELIVERABLE)
- Return a single markdown doc with:
    - All setup steps and workflow above for this week
    - Areas [in brackets] to fill with latest numbers
    - Visual summary grid (emojis/bubbles OK, see dashboard)
    - Specific prompt wording for Claude to follow logic exactly

---

**NOTE:** If using this prompt with new data, update the [date/regime/values] at the top before running. 

---

## REFERENCES & LINKS
- Dynamic scaling, crash protection, and quality filter research: see attached Crash-Protection-Scan and SSRN, AlphaArchitect, TrendSpider sources
- For technical pattern details: Minervini VCP, Velez 20/200 SMA,
- For indicator settings: Williams %R, ATR stops, MACD, RSI overlays

---

**This is your complete swing momentum scan workflow prompt for Claude. Paste, fill numbers, run scan, and print/save the output markdown.**