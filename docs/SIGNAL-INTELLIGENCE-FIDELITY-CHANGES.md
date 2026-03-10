# Signal Intelligence — Mockup Fidelity Changes

**Page:** Signal Intelligence  
**Mockup:** `03-signal-intelligence.png`  
**File:** `frontend-v2/src/pages/SignalIntelligenceV3.jsx`  
**Date:** March 2026

---

## File Changed

| File | Description |
|------|-------------|
| `frontend-v2/src/pages/SignalIntelligenceV3.jsx` | Full mockup fidelity pass |

---

## Visual Differences Found

### Header Bar
- Missing: OC_CORE_v5.2.1, WS_LATENCY, SWARM_SIZE
- Extra: PAS/FWL/E.I.T, VL/SHAP, SIZE selector
- Save Profile: grey/cyan vs green rectangle

### Regime Banner
- Missing: Prominent BULL_TREND REGIME panel at top with HMM subtitle, Override, padlock
- Implementation had Regime Detector in column 3 only

### Scanner Modules (Layer 1)
- Wrong scanner names (Entity Scanner, Force Scanner, etc.)
- Mockup: Daily Scanner 100%, Finviz Screener 70%, AMD Detector 85%, etc. with percentage + slider
- Implementation: toggles + activity bar

### Global Scoring Engine (Layer 2)
- Wrong content: SCORING_METRICS (Signal Rationalization, LSTM, etc.)
- Mockup: OpenClaw Core vs Tech Analysis (Blend 60/40, Regime Multiplier 1.2, SLAM DUNK Tier 90)
- Mockup: PER-FACTOR SHAP WEIGHTS (UN Options Flow 8, Velez Score 8, etc.)

### External Sensors
- Wrong list: Whale Flow, Insider API vs NewsAPI, Benzinga Pro, RSS, YouTube Agent
- Discord: should show "Connected" in green, not toggle
- YouTube Agent: Weight 1

### OpenClaw Swarm (Layer 4)
- Title: "OpenClaw Score" vs "OpenClaw Swarm"
- Wrong agents when API empty (no fallback)
- Mockup: 7 CORE AGENTS (Apex Orchestrator 100%, Relative Weakness 85%, etc.)
- EXTENDED SWARM (93)

### Signal Data Table
- Actions: Eye + Play vs Accept, Reject, Watch, Execute buttons
- Origin Agent: should be underlined/clickable

### Intelligence Modules (Layer 3)
- Wrong modules: HMM, Sentiment, LSTM Trainer, Macro, Monte Carlo
- Mockup: HMM Regime, LLM Client, LoRA Trainer, Macro Context, Memory v1/v3, MTF Alignment, Perf Tracker, Regime Detector — each with percentage slider (100%, 85%, 70%, etc.)
- Title had trailing colon

### Execution & Automation Engine
- Missing: IF/THEN rules section
- Labels: Trading Mode dropdown, Position Sizer (not Position Size)
- AUTO EXECUTION: orange when ON

### ML Model Control (Layer 5)
- Missing version numbers, status (Ready/Training/Idle), Confidence sliders, RETRAIN buttons

### System Telemetry
- Strategy Telemetry / API Priority Engine vs System Telemetry
- Mockup: API ENDPOINT HEALTH subtitle, dot grid, DB: 4.2ms MEM: 64%

---

## Fidelity Fixes Made

| Section | Changes |
|---------|---------|
| **Header** | Teal circles, SIGNAL_INTELLIGENCE_V3, OC_CORE_v5.2.1, WS_LATENCY, SWARM_SIZE; download/upload/share icons; green Save Profile button |
| **Regime Banner** | Prominent panel: ((-)) BULL_TREND REGIME with pulsating icon, HMM (Layer 3) subtitle, HMM Confidence, Override, padlock toggle |
| **Scanner Modules** | Mockup names (Daily Scanner, Finviz Screener, AMD Detector, etc.) with percentage + range slider |
| **Global Scoring** | OpenClaw Core vs Tech Analysis (Blend, Regime Multiplier, SLAM DUNK Tier); PER-FACTOR SHAP WEIGHTS with sliders |
| **External Sensors** | Twitter/X, Reddit, NewsAPI, Benzinga Pro, RSS, Discord Listener (Connected), YouTube Agent (Weight 1) |
| **OpenClaw Swarm** | Title "OpenClaw Swarm (Layer 4)", 7 CORE AGENTS fallback, EXTENDED SWARM (93) |
| **Signal Table** | Accept, Reject, Watch, Execute buttons; Origin Agent underlined |
| **Intelligence Modules** | 9 modules per mockup with Slider components (HMM Regime 100%, LLM Client 85%, etc.); same layout as Global Scoring sliders |
| **Execution Engine** | Title "Execution & Automation Engine"; Trading Mode/Position Sizer dropdowns; Max Portfolio Heat, Daily Loss Limit; IF/THEN rules; AUTO EXECUTION orange toggle |
| **ML Model Control** | Version numbers, status (Ready/Training/Idle), Confidence slider per model, RETRAIN buttons; sliders share width with other sections |
| **System Telemetry** | API ENDPOINT HEALTH subtitle; dot grid; DB/MEM line |

---

## Remaining Differences (Acceptable)

- Chart annotations (H&S Top, Cup & Handle, Bull Flag Break) — require pattern API
- Chart OHLC line (G/H/L format) — cosmetic
- Some API sync keys may not match new data source IDs
