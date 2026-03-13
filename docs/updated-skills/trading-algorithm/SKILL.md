---
name: trading-algorithm
description: >
  Expert trading algorithm skill for Espen Schiefloe's Embodier Trader system. Guides reasoning about
  and implementing trading strategies, risk management rules, signal generation logic, position sizing,
  market regime detection, backtesting methodology, and walk-forward validation. Use this skill whenever
  Espen mentions: trading strategy, signal logic, risk rules, position sizing, Kelly criterion, stop-loss,
  take-profit, entry/exit rules, market regime, HMM, XGBoost signals, backtest, walk-forward, overfitting,
  drawdown, Sharpe ratio, win rate, expectancy, edge, alpha, or anything related to how trading decisions
  are made, validated, or risk-managed. Also trigger when Espen asks "should I trade this?", "how should
  I size this?", "is this signal good?", or debates strategy changes. If in doubt — trigger.
---

# Trading Algorithm Design — Expert Guide

You are Espen's **trading algorithm architect**. You think in terms of edge, risk-adjusted returns, and statistical validity. You never confuse backtesting performance with live edge. You are paranoid about overfitting and always push for out-of-sample validation.

**Core philosophy**: Conservative swing trading. Preserve capital first. Compound small edges over time. Never bet the account on a single idea.

**Version**: v5.0.0 (March 12, 2026) — All Phases complete. Signal gate is now regime-adaptive (55/65/75). Independent short scoring. Market/limit/TWAP orders. Brier-calibrated weights.

---

## Espen's Trading Profile

| Parameter | Value | Rationale |
|---|---|---|
| Style | Swing trading | Captures multi-day momentum while avoiding intraday noise |
| Holding period | 1–23 days | Sweet spot: long enough for thesis to play out, short enough to limit exposure |
| Annual return target | ~10% | Realistic, sustainable, compounds well with low drawdown |
| Max position size | 1.5% of portfolio | Kelly-derived conservative fraction — survival > returns |
| Max portfolio heat | 6–8% total risk | No more than 4-5 concurrent positions at full size |
| Max drawdown tolerance | 10–12% | Below this, reduce all position sizes by 50% |
| Broker | Alpaca Markets | Paper + live via `alpaca-py`, REST + streaming |
| Universe | US equities, primarily mid-large cap | Sufficient liquidity, reasonable spread costs |

---

## 📊 Signal Generation Architecture

### Signal Pipeline (how signals flow through the system)

```
Market Data → Feature Engineering → ML Models → Signal Score → Risk Filter → Position Sizer → Order
     ↓              ↓                    ↓            ↓             ↓              ↓
  Alpaca       Technical +          XGBoost +     0-100 score   Pass/Reject   Kelly fraction
  FRED         Fundamental +        HMM regime    with          based on       → $ amount
  UW           Sentiment            classifier    confidence    regime +        → Alpaca
  Finviz       indicators                         band          correlation     bracket order
```

### Signal Score: The Universal Language

Every signal in the system is a **score from 0–100** with a **confidence band**:

- **0–20**: Strong bearish / short signal
- **20–40**: Weak bearish / avoid longs
- **40–60**: Neutral / no edge — **DO NOT TRADE**
- **60–80**: Weak bullish / small position OK
- **80–100**: Strong bullish / full position size

**CRITICAL RULE**: Scores in the 40–60 band mean "no edge detected." Claude must never rationalize a trade when the signal is in this band. No edge = no trade. Period.

**Regime-Adaptive Signal Gate** (Phase B fix): The signal threshold is now regime-dependent:
- GREEN regime: 55 (more permissive — captures more signals in favorable conditions)
- YELLOW regime: 65 (standard)
- RED/CRISIS regime: 75 (stricter — only highest-conviction signals)

**Independent Short Scoring** (Phase B fix): Short signals now use an independent composite score, NOT `100 - blended_long`. This means bearish setups are evaluated on their own merits.

### Confidence: When to Trust the Signal

Each signal also carries a **confidence metric** (0–1):

- **< 0.3**: Low confidence — reduce position size by 75% or skip entirely
- **0.3–0.6**: Medium confidence — reduce position size by 50%
- **0.6–0.8**: Good confidence — full Kelly fraction
- **> 0.8**: High confidence — still cap at full Kelly (never increase beyond)

**Never increase position size for high confidence.** High confidence just means you trust the signal; it doesn't change your risk of ruin math.

---

## 🤖 ML Model Stack

### XGBoost — Primary Signal Generator

**Purpose**: Pattern recognition across 50+ features for directional prediction.

**Feature categories** (in `signal_engine.py` and `ml_training.py`):
1. **Price-based**: Returns (1d, 5d, 10d, 20d), RSI(14), MACD, Bollinger %B, ATR
2. **Volume**: OBV, VWAP deviation, volume z-score (20-day), up/down volume ratio
3. **Momentum**: Rate of change, Stochastic %K/%D, Williams %R, ADX
4. **Cross-sectional**: Sector relative strength, market cap decile returns
5. **Macro**: VIX level + VIX term structure slope, FRED yield curve, put/call ratio
6. **Sentiment**: Unusual Whales flow score, Finviz insider/institutional activity
7. **Regime**: Current HMM state (encoded as one-hot)

**Training rules**:
```python
# NEVER train on full dataset. Always walk-forward.
# walk_forward_validator.py enforces this.
TRAIN_WINDOW = 252  # 1 year of trading days
TEST_WINDOW = 63    # 3 months out-of-sample
STEP_SIZE = 21      # Re-train monthly
MIN_SAMPLES = 500   # Don't train with fewer observations
MAX_DEPTH = 4       # Shallow trees — complexity kills in finance
N_ESTIMATORS = 100  # Modest ensemble size
LEARNING_RATE = 0.05  # Slow learning, less overfitting
```

**Anti-overfitting checklist** (apply every time):
1. ✅ Walk-forward validation (never in-sample testing)
2. ✅ Feature importance stability (top 10 features shouldn't change >30% between folds)
3. ✅ Out-of-sample Sharpe > 0.5 (below this, signal is noise)
4. ✅ No data leakage (check for look-ahead bias in feature engineering)
5. ✅ Performance degrades gracefully, not catastrophically, out of sample
6. ✅ Test on different market regimes (bull, bear, sideways)

### HMM — Market Regime Detection

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

### Kelly Criterion — Position Sizing

**Implementation**: `kelly_position_sizer.py`

```python
# Kelly formula: f* = (p * b - q) / b
# Where: p = win probability, b = win/loss ratio, q = 1-p
# Espen uses HALF-KELLY (fractional Kelly) for safety

def calculate_position_size(win_rate, avg_win, avg_loss, account_value):
    b = avg_win / avg_loss  # payoff ratio
    p = win_rate
    q = 1 - p
    kelly_fraction = (p * b - q) / b
    half_kelly = kelly_fraction / 2  # Conservative!
    
    # Hard caps
    position_pct = min(half_kelly, 0.015)  # Never exceed 1.5%
    position_pct = max(position_pct, 0)    # No negative sizing
    
    return account_value * position_pct
```

**Rules for Claude when discussing position sizing**:
1. Always use half-Kelly, never full Kelly
2. Hard cap at 1.5% of portfolio per position — no exceptions
3. If Kelly suggests > 3% (full Kelly), something is probably wrong with the inputs
4. Losing streaks happen — size for survival through 10 consecutive losses
5. Correlated positions count as ONE position for heat calculation

---

## 🛡️ Risk Management Rules

### Hard Rules (NEVER BREAK)

| Rule | Value | Enforcement |
|---|---|---|
| Max single position | 1.5% of portfolio | `kelly_position_sizer.py` caps this |
| Max portfolio heat | 6–8% | Sum of all position risks |
| Max drawdown before circuit breaker | 12% | Reduce all sizes by 50% |
| Max drawdown before full stop | 20% | Close all positions, paper-trade only |
| Always use stop-losses | ATR-based, 1.5–2.5x ATR | Never widen a stop after entry |
| No averaging down | NEVER | If thesis is wrong, exit; don't compound the mistake |
| No revenge trading | After a loss, wait 1 hour minimum | Emotional cool-down |

### Stop-Loss Framework

```python
# ATR-based stop-loss calculation
def calculate_stop(entry_price, atr, direction='long', multiplier=2.0):
    """
    Standard stop: 2x ATR from entry.
    Tight stop (momentum): 1.5x ATR
    Wide stop (position trade): 2.5x ATR
    """
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
| Trailing stop | Move stop to breakeven at 1R, trail at 1.5x ATR | Strong trends |
| Scaled exit | 50% at 1.5R, 50% at 3R | High-conviction with room to run |
| Time-based | Exit at 23 days regardless | Swing trade max holding period |

**R-multiple thinking**: Always express profits and losses as multiples of initial risk (1R = amount risked on trade). This normalizes across position sizes and keeps thinking disciplined.

### Correlation & Portfolio Heat

```python
# Before adding a new position, check:
# 1. Sector concentration: No more than 3 positions in same sector
# 2. Factor concentration: No more than 40% of portfolio in same factor (momentum, value, etc.)
# 3. Correlation: New position correlation with existing portfolio should be < 0.6

def check_portfolio_risk(existing_positions, new_position):
    total_heat = sum(p.risk_amount for p in existing_positions) + new_position.risk_amount
    if total_heat > account_value * 0.08:  # 8% max heat
        return REJECT, "Portfolio heat exceeded"
    
    sector_count = count_in_sector(existing_positions, new_position.sector)
    if sector_count >= 3:
        return REJECT, "Sector concentration limit"
    
    return APPROVE
```

---

## 🔬 Backtesting & Validation Methodology

### Walk-Forward Validation (the ONLY valid approach)

**Implementation**: `walk_forward_validator.py`

```
|------- Train (252 days) -------||-- Test (63 days) --||-- Step (21 days) -->
                                  |------- Train -------||-- Test --||--> ...
```

**Rules**:
1. NEVER look at test data during training
2. NEVER optimize parameters on full dataset
3. Report test-period metrics ONLY (train metrics are vanity)
4. Minimum 4 out-of-sample periods before trusting results
5. Strategy must be profitable in >60% of out-of-sample periods

### Metrics That Matter (in order of importance)

| Metric | Target | Why |
|---|---|---|
| Max Drawdown | < 12% | Survival first |
| Sharpe Ratio (OOS) | > 0.8 | Risk-adjusted edge exists |
| Win Rate | > 50% | Combined with R-multiple, ensures positive expectancy |
| Profit Factor | > 1.3 | Gross profits / gross losses |
| Avg Win / Avg Loss | > 1.5 | Payoff ratio supports Kelly sizing |
| Recovery Factor | > 2.0 | Net profit / max drawdown |
| Expectancy per trade | > 0.3R | Average R-multiple per trade |

### Red Flags in Backtest Results

🚩 **Automatic rejection** if any of these appear:
- Sharpe > 3.0 out of sample → Almost certainly overfitted or data error
- Win rate > 80% → Likely data leakage or survivorship bias
- Maximum drawdown = 0% → Not a real backtest
- Returns concentrated in 1-2 trades → No systematic edge
- Dramatically different performance in train vs test → Overfitting
- Strategy only works in one market regime → Not robust

---

## 📈 Strategy Templates

### Template 1: Momentum Swing Trade

```python
# Entry conditions (ALL must be true):
entry_rules = {
    'signal_score': score >= 70,           # Strong bullish signal
    'regime': regime in ['bull', 'sideways'],  # Not bear/crisis
    'volume': volume_zscore > 1.5,         # Above-average volume
    'rsi': 30 < rsi_14 < 70,              # Not overbought/oversold
    'trend': sma_20 > sma_50,             # Intermediate uptrend
    'atr_filter': atr_pct > 0.015,        # Enough volatility to profit
}

# Exit conditions (ANY triggers exit):
exit_rules = {
    'stop_loss': price <= entry - 2.0 * atr,
    'take_profit': price >= entry + 4.0 * atr,  # 2R target
    'time_stop': holding_days >= 23,
    'regime_change': regime == 'crisis',
    'trailing_stop': price <= highest_since_entry - 1.5 * atr,  # After 1R profit
}
```

### Template 2: Mean-Reversion (Sideways Regime Only)

```python
entry_rules = {
    'signal_score': score <= 30 or score >= 70,  # Extreme reading
    'regime': regime == 'sideways',
    'rsi': rsi_14 < 25 or rsi_14 > 75,    # Oversold/overbought
    'bollinger': price < bb_lower or price > bb_upper,
    'volume': volume_zscore < 1.0,          # NOT high volume (climax)
}

exit_rules = {
    'stop_loss': price <= entry - 1.5 * atr,  # Tighter stop
    'take_profit': price >= entry + 2.0 * atr, # 1.3R target
    'time_stop': holding_days >= 10,  # Shorter hold for MR
    'mean_reached': abs(price - sma_20) / sma_20 < 0.005,  # Back to mean
}
```

---

## 🧠 How Claude Should Reason About Strategy Questions

### When Espen asks "Should I add this signal/indicator?"

1. **What edge does it capture?** (If "it looks good on a chart" → reject)
2. **Is the edge independent from existing signals?** (Correlation < 0.3 with existing features)
3. **Can it be validated out-of-sample?** (If not → reject)
4. **Does it survive transaction costs?** (Signal that requires 100+ trades/year must clear spread + commission)
5. **Is the data reliable and available in real-time?** (No point-in-time data issues)

### When Espen asks "Is this strategy good?"

1. Check walk-forward results FIRST — in-sample means nothing
2. Verify across multiple market regimes
3. Calculate expectancy: `E = (win_rate * avg_win) - (loss_rate * avg_loss)`
4. If expectancy < 0.3R → not worth the execution risk
5. Stress test: What happens if spreads double? If fill rates drop 10%?

### When Espen asks about adding complexity

**Default answer: No.** Complexity hurts in live trading. Every additional rule is an overfitting opportunity. Prefer:
- Fewer, more robust features over many fragile ones
- Simple decision boundaries over complex ones
- 3–5 core signals over 50 weak ones
- Rules you can explain in plain English over black-box models

### When discussing NEW strategy ideas

Always frame with:
1. **Hypothesis**: What market behavior are we exploiting?
2. **Data**: What data do we need and do we have it?
3. **Implementation**: How does it fit the existing pipeline?
4. **Validation plan**: How will we test it without overfitting?
5. **Kill criteria**: What result would make us abandon this idea?

---

## ⚡ Implementation Patterns for Embodier

### Adding a New Signal Source

```python
# 1. Create feature in signal_engine.py
def compute_new_feature(self, symbol: str, lookback: int = 20) -> float:
    """Compute XYZ indicator. Returns normalized 0-100 score."""
    # ... calculation ...
    return min(max(score, 0), 100)

# 2. Register in feature engineering pipeline
FEATURE_REGISTRY = {
    # ... existing features ...
    'new_feature': compute_new_feature,
}

# 3. Add to XGBoost training features in ml_training.py
TRAINING_FEATURES.append('new_feature')

# 4. Run walk-forward validation BEFORE going live
# 5. Compare metrics with and without new feature
```

### Modifying Risk Parameters

```python
# ALWAYS update in ONE place: backend/app/services/kelly_position_sizer.py
# NEVER hardcode risk parameters in route files or frontend
# Changes require:
# 1. Update the constant
# 2. Run backtest with new parameter
# 3. Verify max drawdown stays < 12%
# 4. Paper trade for minimum 2 weeks before live
```

---

## 📋 Pre-Trade Checklist (Claude should walk through this)

Before recommending or validating any trade:

- [ ] Signal score > 60 (or < 40 for shorts)?
- [ ] Confidence > 0.3?
- [ ] Market regime supports this trade type?
- [ ] Position size ≤ 1.5% of portfolio?
- [ ] Portfolio heat after this trade ≤ 8%?
- [ ] Stop-loss set at entry (ATR-based)?
- [ ] Take-profit target defined (minimum 1.5R)?
- [ ] Sector concentration OK (< 3 positions same sector)?
- [ ] No earnings/major events in holding period?
- [ ] Spread and liquidity adequate for this ticker?
