# Settings — Mockup Fidelity Changes

**Page:** Settings (System Configuration)  
**Mockup:** `14-settings.png`  
**File:** `frontend-v2/src/pages/Settings.jsx`  
**Date:** March 2026

---

## Visual Differences Found (Before Fixes)

### Section Cards
- **Mockup:** Many section titles have a yellow star icon (★) indicating importance
- **Before:** No star icons on section headers
- **Mockup:** Cards have subtle shadows
- **Before:** Minimal shadow styling

### 1. Identity & Locale
- **Mockup:** Display Name, Email, Timezone, Currency, Timeframe (1D), Avatar "Choose File"
- **Before:** Display Name, Timezone, Language, Timeframe (15), # Stocks, Show FII

### 2. Trading Mode
- **Mockup:** PAPER (green) / LIVE (red); "▲ Live mode = real money" in light green; Status • Connected; Account; Sync (2026-03-01 06:50)
- **Before:** PAPER cyan/LIVE red; amber warning; different fields; no Sync

### 3. Position Sizing
- **Mockup:** Base Size ($25,000), Max Size ($100,000), Max Positions (5), Size Mode (Fixed), Auto-Scale
- **Before:** Position Rules with Base Size, Max Daily Risk, Max Open, Max Sector, Auto-Scale, Correlation

### 4. Risk Limits
- **Mockup:** Yellow star; Max Daily Risk (2.0%), Max Per Trade (0.5%), Max Daily Loss ($2,500), Portfolio Heat (8.0%), Correlation (0.75)
- **Before:** Different fields (Master Killswitch, Flash Crash, Max Drawdown, VaR, Auto-Pause)

### 5. Circuit Breakers
- **Mockup:** Yellow star; Master Killswitch (toggle OFF), VIX Halt (>15%) (ON), Flash Crash (ON), Daily Loss (ON), Consecutive Loss (5) (ON)
- **Before:** Fields instead of toggles; different structure

### 6. Brokerage Connections
- **Mockup:** Alpaca (Connected, PK8V2****, [Test][Edit]); IB and Tradier (Not Configured, [Add]); [+ Add Broker]
- **Before:** TD Ameritrade instead of Tradier; different badge/link styling

### 7. Data Feed API Keys
- **Mockup:** Unusual Whales (Connected, UW_882****); Polygon.io (▲ Degraded, sk-proj-****); OpenAI (Connected); FRED, SEC EDGAR (Not Set, [Add])
- **Before:** FinViz, different structure; no OpenAI; "Not set" vs "Not Set"

### 8. Data Source Priority
- **Mockup:** Primary Pricing, Fallback, Options Flow, Economic, Filings, Rate Limit with specific labels
- **Before:** Different dropdown labels (Polygon v3, etc.)

### 9. OLLAMA LOCAL LLM
- **Mockup:** Yellow star; Endpoint; Status (Not Connected red dot); [Test]; Models checkboxes; [Pull Models]; Use for (Pattern Analysis)
- **Before:** Global Local LLM; different structure; no model checkboxes

### 10. AI Inference Models
- **Mockup:** Primary (GPT-4o), Fallback (Claude 3.5), Local (Ollama), Timeout (10s), Max Tokens (2048), Temperature (0.3); Use for (Signal reasoning)
- **Before:** Inference Models with GPT-4o, GPU/CPU, Signal/Pattern/Gen models, Fallback

### 11. ML Models
- **Mockup:** Three columns LSTM, XGBoost, HMM; each: • Active, Min Conf, Lookback (60), Retrain (Weekly)
- **Before:** Two badges (XGBoost, HMM); different layout

### 12. ML Flywheel
- **Mockup:** Yellow star; Learning Loop, Auto-Retrain, Drift Detection, Schedule (Medium), Walk-Forward, Validation, Min Samples, Feature Tracking
- **Before:** Learning Log with different fields

### 13. OpenClaw Agents
- **Mockup:** Yellow star; Swarm Mode, Voting, Queue, Blackboard; agent toggles (Market Scanner, Pattern Recognition, etc.; Backtesting OFF)
- **Before:** Different agent list; priority sliders

### 14. Agent Thresholds
- **Mockup:** Market Scanner (500K vol), Pattern (75% conf), Risk (10% heat), Sentiment (60 score), YouTube (10K views), Regime (0.65 prob), Options ($100K premium), Earnings (3 days)
- **Before:** Vol Threshold, Flow Threshold, Min/Max Price, Max Concurrent, etc.

### 15. Agent Coordination
- **Mockup:** Task Assignment (Auto), Timeout (30s), Max Tasks (3), Health Check (60s), Retry (2 attempts), Log Level (INFO), Telemetry (ON)
- **Before:** Signal Thresholds section instead

### 16. Trade Management
- **Mockup:** Default SL (1.0 ATR), TP1 (1.5 R), TP2 (3.0 R), Trailing, Partial Exit (50%), Time Exit (EOD), Extended Hours (OFF), Dry Run (ON)
- **Before:** TP1, TP2, TP3, Trailing, Time Exit, Post-Trade Confirm

### 17. Order Execution
- **Mockup:** Order Type (Limit), Offset (0.01%), Slippage (0.05%), Timeout (60s), Pre-Trade Check (ON), Post-Trade Confirm (ON)
- **Before:** Slippage, Trade Execution, EOD Summary, Partial Fill, Retry Failed, Timeout

### 18. Notifications
- **Mockup:** Yellow star; Channels (Discord, SMS, Email, Slack checkboxes); many alert toggles
- **Before:** PMS/Email/Push header; fewer toggles; no channel checkboxes

### 19. Security & Auth
- **Mockup:** Yellow star; Change Password (Current, New, Confirm, [Update]); [Enable TOTP][Enable SMS]; Encryption AES-256 • Active; Session; Last Login; [Revoke All]
- **Before:** 2FA toggle, Session Timeout, API Key Rotation, SSL/TLS, IP Whitelisting

### 20. Backup & System
- **Mockup:** [Export JSON][Import JSON]; Last Backup, Auto-Backup, Location; System Info (v0.9.2-alpha), DB, CPU, RAM, GPU
- **Before:** system.json, Auto-Save, latest timestamp

### 21. Appearance
- **Mockup:** Theme selectors (Midnight Bloomberg, Classic Dark, OLED Black — OLED selected with green border); Density (Ultra Dense), Charts (Lightweight), Font (10px)
- **Before:** Different theme set; color swatches; Dark/Ultra; Animations toggle

### 22. Market Data
- **Mockup:** Timeframe (10), Bars (200), Update (1s), Pre-market (ON), After-hours (ON), Volume (Bars + MA)
- **Before:** Different field set

### 23. Performance
- **Mockup:** Track P&L, Daily Stats, Metrics (Sharpe, Sortino), Benchmark (SPY), Tax (FIFO), Window, Export
- **Before:** Notification Channels section instead

### 24. Audit Log
- **Mockup:** Table with Time, Cat, Actor, Event; [View Full Log]
- **Before:** Logging & Audit with different fields

### 25. Strategy
- **Mockup:** Adaptive (ON), Regime Switch (Bull, Bear, Neutral), Min Prob (0.65), Override (None), Momentum, Mean Reversion, Range (ON)
- **Before:** Strategy Config with Order Type, Entry Method, Auto Execute, etc.

### Footer
- **Mockup:** [Export Settings], [Import Settings], [Reset Defaults] as blue text links; SAVE ALL CHANGES with yellow star icon
- **Before:** Buttons with borders; SAVE ALL CHANGES without star

---

## Files Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/Settings.jsx` | All section updates, SectionCard star prop, footer, layout |

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| SectionCard | Added `star` prop; yellow Star icon for important sections; `shadow-sm` |
| Identity & Locale | Email, Currency, Timeframe (1D); Avatar "Choose File" |
| Trading Mode | PAPER green (emerald); "▲ Live mode = real money"; Status • Connected; Sync field |
| Position Sizing | Renamed from Position Rules; Base $25K, Max $100K, Max Positions 5, Size Mode, Auto-Scale |
| Risk Limits | Star; Max Daily Risk 2%, Max Per Trade 0.5%, Max Daily Loss $2,500, Portfolio Heat 8%, Correlation 0.75 |
| Circuit Breakers | Star; Master Killswitch, VIX Halt, Flash Crash, Daily Loss, Consecutive Loss (5) as toggles |
| Brokerage | Alpaca PK8V2****, [Test][Edit] links; Tradier instead of TD Ameritrade; [Add] for IB/Tradier |
| Data Feed | Unusual Whales UW_882****; Polygon ▲ Degraded sk-proj-****; OpenAI Connected; FRED/SEC Not Set [Add] |
| Data Source Priority | Primary Pricing (Polygon SIP), Fallback (Alpaca V2), Economic, Filings, Rate Limit |
| OLLAMA Local LLM | Star; Status Not Connected; model checkboxes; [Pull Models]; Use for Pattern Analysis |
| AI Inference Models | Primary GPT-4o, Fallback Claude 3.5, Local Ollama, Timeout 10s, Max Tokens 2048, Temp 0.3; Use for Signal reasoning |
| ML Models | Three columns LSTM, XGBoost, HMM; Active, Min Conf, Lookback 60, Retrain Weekly |
| ML Flywheel | Star; Learning Loop, Auto-Retrain, Drift Detection, Schedule, Walk-Forward, Validation, Min Samples, Feature Tracking |
| OpenClaw Agents | Star; Swarm Mode, Voting, Queue, Blackboard; agent toggles per mockup; Backtesting OFF |
| Agent Thresholds | Market Scanner 500K vol, Pattern 75% conf, Risk 10% heat, Sentiment, YouTube, Regime, Options, Earnings |
| Agent Coordination | Replaced Signal Thresholds; Task Assignment, Timeout, Max Tasks, Health Check, Retry, Log Level, Telemetry |
| Trade Management | Default SL 1.0 ATR, TP1 1.5 R, TP2 3.0 R, Trailing, Partial Exit 50%, Time Exit EOD, Extended Hours, Dry Run |
| Order Execution | Order Type Limit, Offset 0.01%, Slippage 0.05%, Timeout 60s, Pre-Trade Check, Post-Trade Confirm |
| Notifications | Star; Channels (Discord, SMS, Email, Slack) checkboxes; full toggle list per mockup |
| Security & Auth | Star; Change Password fields; [Enable TOTP][Enable SMS]; Encryption AES-256 Active; Session; Last Login; [Revoke All] |
| Backup & System | [Export JSON][Import JSON]; Last Backup, Auto-Backup, Location; System Info (v0.9.2-alpha), DB, CPU, RAM, GPU |
| Appearance | Theme selectors Midnight Bloomberg, Classic Dark, OLED Black (OLED default, green border); Density, Charts, Font 10px |
| Market Data | Timeframe 10, Bars 200, Update 1s, Pre-market, After-hours, Volume Bars+MA |
| Performance | Replaced Notification Channels; Track P&L, Daily Stats, Metrics, Benchmark, Tax, Window, Export |
| Audit Log | Table Time/Cat/Actor/Event; mockup fallback rows; [View Full Log] |
| Strategy | Adaptive, Regime Switch, Min Prob 0.65, Override None, Momentum, Mean Reversion, Range |
| Footer | [Export Settings], [Import Settings], [Reset Defaults] as blue links; SAVE ALL CHANGES with yellow star |

---

## Anything Still Off From Mockup

- **Layout:** Mockup uses 3–4 column grid; implementation uses 5-column grid (could be adjusted for responsiveness).
- **Theme default:** OLED Black set as default selected theme; backend may not persist.
- **Security Change Password:** Placeholder inputs; not wired to API.
- **2FA / Revoke All:** Placeholder buttons; not wired to API.
- **Ollama model checkboxes:** Wired to `ollama.models`; backend schema may differ.
- **Some fallback values:** Mockup-specific (e.g., System Info v0.9.2-alpha, GPU RTX 4090) are static.

---

## Approval Status

- **Section structure, labels, and fields:** Aligned with mockup
- **Yellow star icons:** Applied to Risk Limits, Circuit Breakers, OLLAMA, ML Flywheel, OpenClaw, Notifications, Security & Auth
- **Footer:** Blue links; SAVE ALL CHANGES with star icon
- **Shared nav/header/sidebar:** Not modified
- **Ready for approval:** Yes, with noted backend/API wiring gaps
