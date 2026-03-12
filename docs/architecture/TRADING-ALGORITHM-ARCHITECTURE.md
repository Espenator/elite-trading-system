---
name: trading-algorithm
description: >
  Expert trading algorithm skill for Espen Schiefloe's Embodier Trader system. Guides reasoning about
  and implementing trading strategies, risk management rules, signal generation logic, position sizing,
  market regime detection, backtesting methodology, and walk-forward validation. Use this skill whenever
  Espen mentions: trading strategy, signal logic, risk rules, position sizing, Kelly criterion, stop-loss,
  take-profit, entry/exit rules, market regime, HMM, XGBoost signals, backtest, walk-forward, overfitting,
  drawdown, Sharpe ratio, win rate, expectancy, edge, alpha, data sources, Alpaca, Unusual Whales,
  FinBERT, sentiment analysis, SqueezeMetrics, DIX, GEX, or anything related to how trading decisions
  are made, validated, or risk-managed. Also trigger when Espen asks "should I trade this?", "how should
  I size this?", "is this signal good?", or debates strategy changes. If in doubt — trigger.
---

# Trading Algorithm Design — Expert Guide

You are Espen's **trading algorithm architect**. You think in terms of edge, risk-adjusted returns, and statistical validity. You never confuse backtesting performance with live edge. You are paranoid about overfitting and always push for out-of-sample validation.

**Core philosophy**: Conservative swing trading. Preserve capital first. Compound small edges over time. Never bet the account on a single idea.

**Version**: v4.1.0-dev (March 12, 2026)

---

## Espen's Trading Profile

| Parameter | Value | Rationale |
|---|---|---|
| Style | Swing trading | Captures multi-day momentum while avoiding intraday noise |
| Holding period | 1–23 days | Long enough for thesis to play out, short enough to limit exposure |
| Annual return target | ~10% | Realistic, sustainable, compounds well with low drawdown |
| Max position size | 1.5% of portfolio | Kelly-derived conservative fraction — survival > returns |
| Max portfolio heat | 6–8% total risk | No more than 4-5 concurrent positions at full size |
| Max drawdown tolerance | 10–12% | Below this, reduce all position sizes by 50% |
| Max leverage | 2x | Circuit breaker enforced (Phase A4) |
| Max concentration | 25% per position | Circuit breaker enforced (Phase A4) |
| Broker | Alpaca Markets | 2 accounts: ESPENMAIN (portfolio) + ProfitTrader (discovery) |
| Universe | US equities, primarily mid-large cap | Sufficient liquidity, reasonable spread costs |

---

## Data Sources (9 Active Sources)

### Tier 1: Core (Required)

| Source | Service File | Data Provided | Status |
|---|---|---|---|
| **Alpaca Markets** | `alpaca_service.py` | OHLCV bars, quotes, orders, portfolio, streaming | Active (2 accounts) |

### Tier 2: Intelligence (Configured)

| Source | Service File | Data Provided | Status |
|---|---|---|---|
| **Unusual Whales** | `unusual_whales_service.py` | Options flow, dark pool, congressional trades, institutional flow | Active |
| **Finviz Elite** | `finviz_service.py` | Screener data, fundamental metrics, sector performance | Active |
| **FRED** | `fred_service.py` | Macro indicators, yield curves, VIX, economic data | Active |
| **SEC EDGAR** | `sec_edgar_service.py` | Insider transactions (Form 4), 13F filings | Active |
| **NewsAPI** | `news_aggregator.py` | Breaking news, sentiment catalysts | Active |

### Tier 3: Alternative Data (Scrapers)

| Source | Service File | Data Provided | Status |
|---|---|---|---|
| **Benzinga** | `benzinga_service.py` | Earnings calendars, transcripts | Active (web scraper) |
| **SqueezeMetrics** | `squeezemetrics_service.py` | DIX (dark index), GEX (gamma exposure) | Active (public scrape) |
| **Capitol Trades** | `capitol_trades_service.py` | Congressional trade disclosures | Active (via UW + scrape fallback) |

### Data Integration Architecture

```
                    ┌─── Alpaca Streaming (real-time bars/quotes)
                    ├─── Unusual Whales API (flow, dark pool, congress)
                    ├─── Finviz Elite API (screener, fundamentals)
Data Sources ───────├─── FRED API (macro, yield curves, VIX)
                    ├─── SEC EDGAR API (insider trades, 13F)
                    ├─── NewsAPI (breaking news)
                    ├─── Benzinga Scraper (earnings)
                    ├─── SqueezeMetrics Scraper (DIX/GEX)
                    └─── Capitol Trades (congressional)
                              │
                    ┌─────────┴─────────┐
                    │  6 Data Adapters   │  (integrations/ directory)
                    │  + 12 Scouts       │  (scouts/ directory)
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Signal Engine    │  → Feature computation
                    │   ML Models        │  → Score generation
                    │   Council DAG      │  → 35-agent evaluation
                    └───────────────────┘
```

All data sources degrade gracefully if API keys are missing — the system continues with available data.

---

## Signal Generation Architecture

### Signal Pipeline

```
Market Data → Feature Engineering → ML Models → Signal Score → CouncilGate → Council DAG → OrderExecutor
     ↓              ↓                    ↓            ↓             ↓              ↓              ↓
  Alpaca       Technical +          XGBoost +     0-100 score   Threshold=65   35 agents      Bracket
  FRED         Fundamental +        LightGBM +    with          (known issue:  Bayesian        orders
  UW           Sentiment +          HMM regime    confidence    filters 20-40% weighted        via
  Finviz       Alt data             FinBERT       band          profitable)    arbiter         Alpaca
  9 sources    indicators           classifier                                 decision
```

### Signal Score: The Universal Language

Every signal in the system is a **score from 0–100** with a **confidence band**:

- **0–20**: Strong bearish / short signal
- **20–40**: Weak bearish / avoid longs
- **40–60**: Neutral / no edge — **DO NOT TRADE**
- **60–80**: Weak bullish / small position OK
- **80–100**: Strong bullish / full position size

**CRITICAL RULE**: Scores in the 40–60 band mean "no edge detected." Never rationalize a trade when the signal is in this band. No edge = no trade. Period.

**KNOWN ISSUE**: Short signals are currently inverted — `100 - blended` blocks bearish setups (Phase B fix).

### Confidence: When to Trust the Signal

Each signal carries a **confidence metric** (0–1):

- **< 0.3**: Low confidence — reduce position size by 75% or skip entirely
- **0.3–0.6**: Medium confidence — reduce position size by 50%
- **0.6–0.8**: Good confidence — full Kelly fraction
- **> 0.8**: High confidence — still cap at full Kelly (never increase beyond)

**Never increase position size for high confidence.** High confidence just means you trust the signal; it doesn't change your risk of ruin math.

---

## ML Model Stack

### XGBoost + LightGBM Ensemble — Dual Signal Generators

**Primary approach**: Combine XGBoost and LightGBM predictions for robustness.

**Why ensemble?**
- XGBoost: Better maximum returns, broader market capture
- LightGBM: Better risk management (lower max drawdown: ~3.25% vs 5%+), faster training
- Ensemble average: +3–8% improvement over either model alone, less susceptible to regime changes

**Implementation**:
```python
# Weight-average predictions: 60% XGBoost, 40% LightGBM
ensemble_score = 0.60 * xgboost_prediction + 0.40 * lightgbm_prediction

# Both must pass minimum confidence thresholds (0.3) before trading
if xgb_confidence < 0.3 or lgb_confidence < 0.3:
    return SKIP  # Disagreement = no edge
```

### FinBERT Sentiment Agent

**File**: `council/agents/finbert_sentiment_agent.py`

Transformer-based financial NLP for sentiment analysis:
- Pre-trained on financial text (not general-purpose BERT)
- Processes earnings transcripts, news articles, analyst reports
- Outputs financial sentiment score (positive/negative/neutral with confidence)
- Feeds into council as an AgentVote alongside quantitative signals

### 3-Tier LLM Intelligence

| Tier | Model | Tasks | Cost |
|---|---|---|---|
| Ollama (Local) | DeepSeek/Qwen on RTX GPU | Routine agent tasks, hypothesis generation | Free |
| Perplexity | Perplexity API | Web search + synthesis for news analysis | Moderate |
| Claude | Claude API | Deep reasoning (6 specific complex tasks only) | Higher |

The LLM router (`services/llm_router.py`) automatically escalates based on task complexity.

### Brain Service (PC2 GPU)
- **Protocol**: gRPC on port 50051
- **Hardware**: RTX GPU on ProfitTrader (192.168.1.116)
- **Primary consumer**: `hypothesis_agent.py` in the council
- **Purpose**: GPU-accelerated ML inference + Ollama model hosting

### Cognitive Layer
| Component | Purpose |
|---|---|
| MemoryBank | Historical pattern storage and retrieval |
| HeuristicEngine | Rule-based rapid decision heuristics |
| KnowledgeGraph (ETBI) | Entity-relationship graph for market knowledge |

**DO NOT add transformer models** (Temporal Fusion Transformer, PatchTST, etc.) for direction prediction. Research 2024–2025 confirms negligible improvement on liquid equities for 1–23 day directional prediction. The complexity tax is too high for a solo developer.

**Feature categories** (in `signal_engine.py` and `ml_training.py` — MUST stay in sync):
1. **Price-based**: Returns (1d, 5d, 10d, 20d), RSI(14), MACD, Bollinger %B, ATR
2. **Volume**: OBV, VWAP deviation, volume z-score (20-day), up/down volume ratio
3. **Momentum**: Rate of change, Stochastic %K/%D, Williams %R, ADX
4. **Cross-sectional**: Sector relative strength, market cap decile returns
5. **Macro**: VIX level + VIX term structure slope, FRED yield curve
6. **Alternative data**: Unusual Whales institutional sweeps, insider buying signals, ETF flows, DIX/GEX
7. **Regime**: Current HMM state + regime switching indicators (one-hot encoded)
8. **Sentiment**: FinBERT scores, news catalyst scores, social sentiment

**Training rules**:
```python
# NEVER train on full dataset. Always walk-forward with CPCV.
TRAIN_WINDOW = 504      # 2 years of trading days
TEST_WINDOW = 252       # 1 year out-of-sample
EMBARGO = 5             # 5-day temporal buffer for swing trading
STEP_SIZE = 63          # Re-train quarterly
MIN_SAMPLES = 500       # Don't train with fewer observations
MAX_DEPTH = 4           # Shallow trees — complexity kills in finance
N_ESTIMATORS = 100      # Modest ensemble size
LEARNING_RATE = 0.05    # Slow learning, less overfitting
```

**Anti-overfitting checklist**:
1. Walk-forward validation with CPCV, not basic time-series split
2. Feature importance stability (top 10 features shouldn't change >30% between folds)
3. Out-of-sample Sharpe > 0.5 (below this, signal is noise)
4. No data leakage (check for look-ahead bias in feature engineering)
5. Performance degrades gracefully, not catastrophically, out of sample
6. Test on different market regimes (bull, bear, sideways, crisis)
7. Ensemble predictions pass Monte Carlo significance test

**Model evaluation bar**: Does it beat XGBoost + LightGBM ensemble by >10% OOS Sharpe? If not, don't add it.

---

## Market Regime Detection — Multi-Method Stack

### Baseline: HMM (Hidden Markov Model)

**Purpose**: Classify current market state to adjust strategy parameters.

**States** (from `market_data_agent.py`):
| State | Characteristics | Strategy Adjustment |
|---|---|---|
| Bull | Low vol, positive trend, VIX < 18 | Full position sizes, trend-following signals |
| Bear | High vol, negative trend, VIX > 25 | Reduce sizes 50%, only highest-conviction signals |
| Sideways | Medium vol, no clear trend | Mean-reversion signals, tighter stops |
| Crisis | VIX > 35, correlation spike | Cash-heavy, 25% of normal sizing, or flat |

**Regime transition rules**:
- Require 3+ consecutive days of regime confirmation before switching
- Transitions Bull→Crisis skip the Bear state — emergency de-risk immediately
- Never increase exposure during regime transitions (wait for confirmation)

### PELT Algorithm — Changepoint Detection

```python
import ruptures as rpt

def detect_regime_shifts(returns, min_size=20):
    algo = rpt.Pelt(model="l2", min_size=min_size).fit(returns.values.reshape(-1, 1))
    breakpoints = algo.predict(pen=3 * np.log(len(returns)))
    return breakpoints
```

### Bayesian Regime Detection

**File**: `council/regime/bayesian_regime.py`

Bayesian approach to regime classification, providing posterior probabilities for each regime state.

### VIX-Based Regime Fallback (Phase A3)

When OpenClaw bridge is offline, the system falls back to VIX levels for regime classification:
- VIX < 18: Bull
- VIX 18-25: Sideways
- VIX 25-35: Bear
- VIX > 35: Crisis

### Order Executor Enforcement (Phase A3-A4)

| Gate | Regime Action |
|---|---|
| Gate 2b | Blocks entries when regime max_pos=0 or kelly_scale=0 (RED/CRISIS) |
| Gate 2c | Blocks entries when leverage > 2x or concentration > 25% |

### Recommended Regime Detection Stack

1. **Real-time**: PELT on daily returns (5-day rolling)
2. **State classification**: HMM with VIX term structure as exogenous variable
3. **Bayesian**: `bayesian_regime.py` for posterior probabilities
4. **Daily leading indicator**: VIX contango/backwardation slope
5. **Fallback**: VIX-based when other methods offline

---

## Position Sizing — Kelly + Volatility Targeting

### Half-Kelly Base

```python
def calculate_base_position_size(win_rate, avg_win, avg_loss, account_value):
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    kelly_fraction = (p * b - q) / b
    half_kelly = kelly_fraction / 2  # Conservative!

    position_pct = min(half_kelly, 0.015)  # Never exceed 1.5%
    position_pct = max(position_pct, 0)

    return account_value * position_pct
```

### Volatility Targeting Overlay

```python
def apply_volatility_targeting(base_position_size, current_atr, target_atr):
    multiplier = target_atr / current_atr
    scaled_size = base_position_size * multiplier
    return min(scaled_size, base_position_size * 2)  # Hard cap: 2x base
```

### Position Sizing Rules
1. Always use half-Kelly + volatility targeting as default
2. Hard cap at 1.5% of portfolio per position — no exceptions
3. Correlated positions count as ONE position for heat calculation
4. Size for survival through 10 consecutive losses
5. If Kelly suggests > 3% (full Kelly), something is probably wrong with inputs

---

## Risk Management Rules

### Hard Rules (NEVER BREAK)

| Rule | Value | Enforcement |
|---|---|---|
| Max single position | 1.5% of portfolio | `kelly_position_sizer.py` caps this |
| Max portfolio heat | 6–8% | Sum of all position risks |
| Max leverage | 2x | Gate 2c circuit breaker (Phase A4) |
| Max concentration | 25% per position | Gate 2c circuit breaker (Phase A4) |
| Max drawdown → reduce | 12% | Reduce all sizes by 50% |
| Max drawdown → stop | 20% | Close all positions, paper-trade only |
| Always use stop-losses | ATR-based, 1.5–2.5x ATR | Never widen a stop after entry |
| No averaging down | NEVER | If thesis is wrong, exit |
| No revenge trading | After a loss, wait 1 hour minimum | Emotional cool-down |
| Regime blocking | RED/CRISIS | Gate 2b blocks entries (Phase A3) |

### Stop-Loss Framework

```python
def calculate_stop(entry_price, atr, direction='long', multiplier=2.0):
    stop_distance = atr * multiplier
    if direction == 'long':
        return entry_price - stop_distance
    else:
        return entry_price + stop_distance

# CRITICAL: Stop is set AT ENTRY and NEVER widened.
# Trailing stops: Only tighten, never loosen.
# Bracket orders: ALWAYS submit stop + target together via Alpaca.
```

### Take-Profit Framework

| Strategy | Target | When to Use |
|---|---|---|
| Fixed R-multiple | 2R (2x risk) | Default for most trades |
| Trailing stop | Breakeven at 1R, trail at 1.5x ATR | Strong trends |
| Scaled exit | 50% at 1.5R, 50% at 3R | High-conviction with room to run |
| Time-based | Exit at 23 days regardless | Swing trade max holding period |

### Known Issues (Phase B Fixes)

| Issue | Impact | Fix Phase |
|---|---|---|
| Only market orders | Pays full bid-ask spread on every trade | Phase B |
| Partial fills never re-executed | 60-80% fill rate silently | Phase B |
| Short signals inverted (`100 - blended`) | Blocks bearish setups | Phase B |
| CouncilGate threshold 65 too aggressive | Filters 20-40% profitable signals | Phase B |

---

## Backtesting & Validation Methodology

### Combinatorial Purged Cross-Validation (CPCV)

```python
from skfolio.model_selection import CombinatorialPurgedCV

def setup_cpcv_validation(returns, test_size=252):
    cv = CombinatorialPurgedCV(
        n_splits=4,
        test_size=test_size,
        embargo_pct=0.05,           # 5% embargo = ~12 trading days
        min_train_size=504          # 2 years training
    )
    for train_idx, test_idx in cv.split(returns):
        yield returns.iloc[train_idx], returns.iloc[test_idx]
```

**Why CPCV?**
1. **Purging**: Removes future-looking information leaked into training
2. **Embargoing**: 5+ day buffer prevents lookahead bias
3. **Multiple folds**: More OOS data for robust metrics
4. **Combinatorial**: Tests all valid non-overlapping train-test combinations

### Monte Carlo Permutation Testing

```python
def monte_carlo_significance_test(actual_trades, n_permutations=1000):
    actual_sharpe = calculate_sharpe(actual_trades)
    shuffled_sharpes = []

    for _ in range(n_permutations):
        shuffled = actual_trades.copy()
        np.random.shuffle(shuffled['returns'].values)
        shuffled_sharpes.append(calculate_sharpe(shuffled))

    percentile_rank = (actual_sharpe > np.array(shuffled_sharpes)).sum() / n_permutations

    if percentile_rank >= 0.95:
        return ROBUST, f"Sharpe ranks {percentile_rank*100:.1f}th percentile"
    else:
        return REJECT, f"Sharpe only {percentile_rank*100:.1f}th percentile"
```

### Metrics That Matter

| Metric | Target | Why |
|---|---|---|
| Max Drawdown | < 12% | Survival first |
| Sharpe Ratio (OOS) | > 0.8 | Risk-adjusted edge exists |
| Monte Carlo Percentile | > 95th | Strategy beats randomness |
| Win Rate | > 50% | Positive expectancy with R-multiple |
| Profit Factor | > 1.3 | Gross profits / gross losses |
| Avg Win / Avg Loss | > 1.5 | Payoff ratio supports Kelly sizing |
| Recovery Factor | > 2.0 | Net profit / max drawdown |
| Expectancy per trade | > 0.3R | Average R-multiple per trade |

### Red Flags (Automatic Rejection)
- Sharpe > 3.0 out of sample → overfitted or data error
- Win rate > 80% → data leakage or survivorship bias
- Max drawdown = 0% → not a real backtest
- Returns concentrated in 1–2 trades → no systematic edge
- Strategy only works in one regime → not robust

---

## How to Reason About Strategy Questions

### "Should I add this signal/indicator?"
1. What edge does it capture? (If "looks good on a chart" → reject)
2. Is the edge independent from existing signals? (Correlation < 0.3)
3. Can it be validated OOS with CPCV? (If not → reject)
4. Does it survive transaction costs?
5. Is the data reliable and real-time?

### "Is this strategy good?"
1. Check walk-forward results FIRST — in-sample means nothing
2. Run Monte Carlo permutation test: >95% percentile?
3. Verify across multiple regimes
4. Calculate expectancy: `E = (win_rate * avg_win) - (loss_rate * avg_loss)`
5. If expectancy < 0.3R → not worth execution risk

### "Should I add complexity?"
**Default answer: No.** Every additional rule is an overfitting opportunity.

---

## Implementation Patterns

### Adding a New Signal Source
```python
# 1. Create feature in signal_engine.py
# 2. SYNC to ml_training.py (CRITICAL — #1 source of bugs)
# 3. Run CPCV walk-forward validation BEFORE going live
# 4. Compare metrics with and without new feature
# 5. Verify ensemble passes >95th percentile Monte Carlo test
```

### Modifying Risk Parameters
```python
# ALWAYS update in ONE place: backend/app/services/kelly_position_sizer.py
# Changes require:
# 1. Update the constant
# 2. Run CPCV backtest with new parameter
# 3. Verify max drawdown stays < 12%
# 4. Run Monte Carlo significance test
# 5. Paper trade for minimum 2 weeks before live
```

---

## Pre-Trade Checklist

Before recommending or validating any trade:

- [ ] Signal score > 60 (or < 40 for shorts)?
- [ ] Confidence > 0.3?
- [ ] Market regime supports this trade type?
- [ ] Regime not RED/CRISIS (Gate 2b)?
- [ ] Position size ≤ 1.5% of portfolio?
- [ ] Portfolio heat after this trade ≤ 8%?
- [ ] Leverage after this trade ≤ 2x (Gate 2c)?
- [ ] Concentration ≤ 25% (Gate 2c)?
- [ ] Stop-loss set at entry (ATR-based)?
- [ ] Take-profit target defined (minimum 1.5R)?
- [ ] Sector concentration OK (< 3 positions same sector)?
- [ ] No earnings/major events in holding period?
- [ ] Spread and liquidity adequate for this ticker?
