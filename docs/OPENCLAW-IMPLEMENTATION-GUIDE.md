<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# OpenClaw Real-Time Trading Engine: Implementation Prompts for Claude Opus

Below are **8 concrete implementation prompts** ready to copy-paste to Comet's Claude Opus assistant. Each prompt is self-contained and builds on the existing OpenClaw v3.0 codebase at `https://github.com/Espenator/openclaw`.

***

## CONTEXT BLOCK (Give this to Comet first)

```
You are enhancing the OpenClaw v3.0 trading system located at:
https://github.com/Espenator/openclaw

EXISTING ARCHITECTURE:
- composite_scorer.py: 100-point 5-pillar scoring (Regime:20, Trend:25, Pullback:25, Momentum:20, Pattern:10)
- technical_checker.py: Computes 15+ indicators from Alpaca bars (RSI, Williams %R, ADX, MACD, ATR, SMA, EMA, VWAP)
- daily_scanner.py: Batch pipeline that runs 1x per day (Steps 1-20)
- alpaca_client.py: Alpaca v2 API for order execution
- fom_expected_moves.py: Scrapes FOM expected move data from Discord, already integrated
- position_sizer.py: ATR-based sizing with Kelly criterion
- regime.py + hmm_regime.py: 3-layer regime detection (GREEN/YELLOW/RED)
- memory.py + performance_tracker.py: Trade outcomes tracking
- All API keys are in .env (ALPACA_API_KEY, ALPACA_SECRET_KEY, etc.)

GOAL: Transform from batch daily scanner to real-time event-driven trading engine with:
1. Streaming market data processing
2. Advanced pullback/rebound/short detection
3. AI-driven dynamic weight optimization
4. FOM expected moves integration into scoring
5. Immediate execution on signal triggers

Use Python 3.11+, maintain existing coding style, add comprehensive logging, write unit tests where applicable. Each module should be standalone and importable by daily_scanner.py and the new streaming_engine.py.
```


***

## PROMPT 1: Real-Time Streaming Engine Foundation

```
CREATE: streaming_engine.py

Build a real-time event-driven trading engine that replaces the batch daily_scanner.py workflow.

REQUIREMENTS:

1. ALPACA WEBSOCKET CONNECTION:
   - Use alpaca-py WebSocket client (not REST polling)
   - Subscribe to real-time 1-minute bars for a dynamic watchlist
   - Subscribe to trades stream for fill confirmations
   - Implement automatic reconnection with exponential backoff
   - Log all streaming events to logs/streaming_engine_{date}.log

2. CONTINUOUS SCORING LOOP:
   - Every time a new 1-min bar arrives, re-compute fast indicators for that ticker:
     * RSI (14-period rolling)
     * Williams %R (14-period rolling)
     * VWAP distance in ATR units
     * Volume ratio vs 20-bar average
   - Call composite_scorer.score_candidate() with updated technicals
   - If score crosses above 75 threshold, emit SIGNAL_READY event

3. WATCHLIST MANAGEMENT:
   - Load initial watchlist from daily_scanner.py results (JSON file: data/daily_watchlist.json)
   - Support dynamic add/remove of tickers via Slack command /oc stream add TSLA
   - Maximum 50 concurrent subscriptions (Alpaca limit)
   - Priority: Keep top 25 composite-scored tickers + 25 from whale flow

4. STATE PERSISTENCE:
   - Save current scores to Redis or JSON every 60 seconds: data/live_scores.json
   - Format: {"ticker": {"score": 78.5, "last_update": "2026-02-20T12:45:00", "pillars": {...}}}
   - On restart, reload state and resume

5. INTEGRATION POINTS:
   - Import: from composite_scorer import CompositeScorer
   - Import: from technical_checker import TechnicalChecker
   - Import: from alpaca_client import alpaca_client
   - Emit events to auto_executor.py (we'll build this next)

6. SIGNAL TRIGGER LOGIC:
   Define trigger conditions as a dictionary:
   TRIGGERS = {
     "pullback_entry": "score >= 75 AND williams_r crosses above -80 AND price touches vwap",
     "breakout_entry": "score >= 80 AND price > 20_bar_high AND volume_ratio > 1.5",
     "mean_reversion": "score >= 70 AND rsi < 30 AND williams_r < -85 AND price > sma_200"
   }
   
   Parse these conditions and evaluate on every bar update. When TRUE, emit:
   {
     "event": "SIGNAL_READY",
     "ticker": "AAPL",
     "trigger": "pullback_entry",
     "score": 78.2,
     "entry_price": 182.45,
     "timestamp": "2026-02-20T12:47:33"
   }

7. MAIN LOOP STRUCTURE:
   ```python
   async def run_streaming_engine():
       # Initialize WebSocket
       # Load watchlist from data/daily_watchlist.json
       # Subscribe to 1-min bars for all tickers
       while True:
           # On bar event: update_indicators() -> score_candidate() -> check_triggers()
           # On signal: emit_to_executor()
           # Every 60s: persist_state()
           await asyncio.sleep(0.01)
```

8. CLI COMMANDS:
    - python streaming_engine.py --start (daemon mode)
    - python streaming_engine.py --watchlist (show current subscriptions)
    - python streaming_engine.py --scores (print live scores table)
9. SLACK INTEGRATION:
Post real-time alerts to \#oc-trade-desk when score crosses 80+:
":rocket: AAPL score 82.3 | pullback_entry trigger | Entry: \$182.45 | Stop: \$180.12"
10. ERROR HANDLING:

- Catch all exceptions in the main loop, log them, continue running
- If Alpaca WebSocket disconnects, reconnect after 5s
- If a ticker throws errors 3x in a row, remove from watchlist

TESTING:
Write tests/test_streaming_engine.py with mock Alpaca WebSocket events.

DELIVERABLE:

- streaming_engine.py (400-600 lines)
- tests/test_streaming_engine.py
- Updated README.md with usage instructions

```

***

## PROMPT 2: Advanced Pullback Detection Module

```

CREATE: pullback_detector.py

Build a sophisticated pullback detection system that identifies high-probability mean-reversion entries.

REQUIREMENTS:

1. FIBONACCI RETRACEMENT ZONES:
    - Detect swing points over last 60 bars using zigzag algorithm (min 3% swing)
    - Calculate Fibonacci levels: 23.6%, 38.2%, 50%, 61.8%, 78.6% from swing_low to swing_high
    - Return which Fib level price is currently testing (within 0.3 ATR)
    - Function: detect_fib_pullback(highs, lows, closes, atr) -> {"level": 0.618, "price": 182.30, "distance_atr": 0.2}
2. VOLUME PROFILE SUPPORT:
    - Calculate Point of Control (POC) = price level with highest volume over last 20 bars
    - Calculate Value Area = 70% of volume distribution around POC
    - Function: calculate_volume_profile(bars) -> {"poc": 181.50, "va_high": 183.20, "va_low": 179.80}
    - Flag when price pulls back to POC or VA boundaries
3. MOVING AVERAGE CONFLUENCE ZONES:
    - Detect when 20 SMA, 50 EMA, and nearest Fib level all converge within 1 ATR
    - Function: detect_ma_confluence(sma_20, ema_50, fib_levels, atr) -> bool
    - Assign confluence_score: 0-10 based on how tight the cluster is
4. PULLBACK QUALITY SCORING (0-100):
Components:
    - Declining volume on pullback (30 pts): volume ratio < 0.8 = +30
    - ATR compression (20 pts): current ATR < 20-bar avg ATR = +20
    - Staying above key MA (20 pts): price > 50 EMA = +20
    - RSI oversold but not panic (15 pts): 30 < RSI < 45 = +15
    - Williams %R entry zone (15 pts): -80 < W%R < -60 = +15

Function: score_pullback_quality(bars, indicators) -> float (0-100)
5. MEAN-REVERSION TRIGGER:
Multi-confirmation trigger:
    - RSI < 30 OR Williams %R < -80
    - AND price touches lower Bollinger Band (2 std dev)
    - AND stock is in uptrend (price > 200 SMA)
    - AND volume spike on reversal bar (volume_ratio > 1.3)

Function: detect_mean_reversion_trigger(bars, indicators) -> bool
6. PULLBACK PATTERN CLASSIFICATION:
Classify pullback type:
    - "healthy_retracement": Fib 38-50%, declining volume, tight ATR
    - "deep_value": Fib 61.8%, RSI < 30, above 200 SMA
    - "consolidation": Tight range, low ATR, near POC
    - "failed": Below 200 SMA or volume increasing

Function: classify_pullback(bars, indicators, fib_data) -> str
7. INTEGRATION WITH COMPOSITE SCORER:
Enhance composite_scorer.py _score_pullback() method:
    - If pullback_detector.score_pullback_quality() > 70, add +5 bonus
    - If detect_ma_confluence() == True, add +3 bonus
    - If classify_pullback() == "healthy_retracement", add +2 bonus
8. FOM EXPECTED MOVES INTEGRATION:
    - Import from fom_expected_moves import get_expected_move
    - If pullback distance equals 50-70% of daily expected move, boost score +3
    - This identifies pullbacks that are sized appropriately for the stock's volatility

Function: score_em_alignment(pullback_distance, expected_move) -> int (0-5)
9. DATA STRUCTURE:
Return comprehensive pullback data:

```python
{
  "ticker": "AAPL",
  "pullback_detected": True,
  "quality_score": 85.0,
  "pattern": "healthy_retracement",
  "fib_level": 0.618,
  "fib_price": 182.30,
  "poc": 181.50,
  "ma_confluence": True,
  "mean_reversion_trigger": False,
  "em_alignment_score": 3,
  "expected_move_pct": 2.3,
  "entry_zone": 182.30,
  "confidence": 0.85
}
```

10. BATCH PROCESSING:
Function: batch_detect_pullbacks(tickers: List[str]) -> Dict[str, dict]
Process 20+ tickers efficiently using ThreadPoolExecutor

TESTING:
Write tests/test_pullback_detector.py with synthetic OHLCV data for each pattern type.

DELIVERABLE:

- pullback_detector.py (400-500 lines)
- tests/test_pullback_detector.py
- Integration diff for composite_scorer.py

```

***

## PROMPT 3: Rebound & Reversal Detection Module

```

CREATE: rebound_detector.py

Build a reversal and rebound detection system for capitulation bounces and trend reversals.

REQUIREMENTS:

1. CAPITULATION VOLUME DETECTION:
    - Detect volume spike: current_volume > 3.0 * 20_bar_avg_volume
    - Must occur on down day: close < open
    - Followed by reversal within 1-3 bars: close > prior_high
    - Function: detect_capitulation(bars) -> {"detected": bool, "spike_ratio": 3.5, "reversal_bar": 2}
2. REVERSAL CANDLESTICK PATTERNS:
Implement detection for:
    - Hammer: small body, long lower wick (2x body), appears after downtrend
    - Bullish engulfing: current bar engulfs prior red bar completely
    - Morning star: 3-bar pattern (red, doji, green with gap)
    - Piercing line: green bar closes > 50% of prior red bar

Function: detect_reversal_pattern(bars) -> str ("hammer"|"engulfing"|"morning_star"|"piercing"|"none")
3. RSI DIVERGENCE WITH VOLUME CONFIRMATION:
    - Enhance existing technical_checker.detect_rsi_divergence()
    - Add volume requirement: second low must have volume > 1.3x first low
    - Function: detect_confirmed_divergence(bars, rsi_series) -> {"type": "bullish"|"bearish"|"none", "confirmed": bool}
4. VWAP RECLAIM DETECTION:
    - Track when price crosses below VWAP then reclaims it
    - Require above-average volume on reclaim bar: volume_ratio > 1.2
    - Calculate bars_below_vwap (how long it was underwater)
    - Function: detect_vwap_reclaim(bars, vwap) -> {"reclaimed": bool, "bars_below": 3, "volume_ratio": 1.45}
5. SUPPORT BOUNCE SCORING:
Identify support levels:
    - Prior swing lows (last 3 occurrences in 60 bars)
    - High-volume nodes from volume profile (top 3 POCs)
    - Round numbers (multiples of \$5, \$10, \$50)
    - Key moving averages (50 EMA, 200 SMA)

When price bounces off support (touches within 0.5 ATR then rallies):
    - Count how many support types converge
    - Score: 1 support = 5pts, 2 supports = 8pts, 3+ supports = 10pts

Function: score_support_bounce(bars, support_levels, atr) -> int (0-10)
6. REBOUND QUALITY SCORING (0-100):
Components:
    - Capitulation volume detected (25 pts)
    - Reversal pattern present (20 pts)
    - RSI divergence confirmed (20 pts)
    - VWAP reclaim (15 pts)
    - Support bounce score (10 pts)
    - Price > 200 SMA (10 pts)

Function: score_rebound_quality(bars, indicators, support_levels) -> float (0-100)
7. REBOUND TRIGGER CONDITIONS:
Multi-confirmation:
    - Reversal pattern detected (hammer or engulfing)
    - AND RSI was < 30 in last 5 bars, now > 35
    - AND volume ratio > 1.3 on reversal bar
    - AND price reclaimed VWAP or touched support

Function: detect_rebound_trigger(bars, indicators) -> bool
8. FOM EXPECTED MOVES FOR REBOUNDS:
    - Import from fom_expected_moves import get_expected_move
    - Calculate bounce_magnitude: (current_price - recent_low) / recent_low
    - If bounce_magnitude is 30-50% of daily expected move, flag as "proportional rebound"
    - This filters out noise bounces vs. meaningful reversals

Function: score_rebound_em_alignment(bounce_magnitude, expected_move) -> int (0-5)
9. INTEGRATION WITH COMPOSITE SCORER:
Add new bonus modifier in composite_scorer._calc_bonus():
    - If rebound_detector.score_rebound_quality() > 70, add +5 bonus
    - If detect_rebound_trigger() == True, add +3 bonus
    - If detect_confirmed_divergence()['confirmed'] == True, add +2 bonus
10. DATA STRUCTURE:
Return comprehensive rebound data:
```python
{
  "ticker": "AAPL",
  "rebound_detected": True,
  "quality_score": 78.0,
  "capitulation": True,
  "reversal_pattern": "hammer",
  "rsi_divergence": {"type": "bullish", "confirmed": True},
  "vwap_reclaim": {"reclaimed": True, "bars_below": 4, "volume_ratio": 1.52},
  "support_bounce_score": 8,
  "trigger_active": True,
  "em_alignment_score": 4,
  "expected_move_pct": 2.8,
  "entry_zone": 183.50,
  "confidence": 0.78
}
```

11. BATCH PROCESSING:
Function: batch_detect_rebounds(tickers: List[str]) -> Dict[str, dict]

TESTING:
Write tests/test_rebound_detector.py with synthetic reversal scenarios.

DELIVERABLE:

- rebound_detector.py (400-500 lines)
- tests/test_rebound_detector.py
- Integration diff for composite_scorer.py

```

***

## PROMPT 4: Short Selling & Bearish Setup Detection

```

CREATE: short_detector.py

Build a complete bearish setup detection system with inverted scoring logic for RED regime.

REQUIREMENTS:

1. BEARISH PATTERN DETECTION:
Implement:
    - Distribution pattern: rising price + declining volume over 10+ bars
    - Head \& shoulders: detect 3 peaks with middle peak highest
    - Descending channel: lower highs + lower lows over 20 bars (inverse of _detect_channel_up)
    - Breakdown: price breaks below 20-bar low with volume surge

Functions:
    - detect_distribution(bars) -> bool
    - detect_head_shoulders(bars) -> bool
    - detect_descending_channel(highs, lows) -> bool
    - detect_breakdown(bars) -> bool
2. BEARISH TECHNICAL INDICATORS:
Short entry signals:
    - Williams %R > -20 (overbought)
    - RSI > 70 (overbought)
    - Price < 200 SMA (downtrend)
    - MACD histogram declining (momentum weakening)
    - Price breaks below 50 EMA with volume

Function: compute_bearish_indicators(bars, indicators) -> dict
3. BEARISH WHALE FLOW FILTER:
    - Import from whale_flow import whale_flow_scanner
    - Filter for bearish signals:
        * Large put sweeps (premium > \$100K)
        * Put/Call ratio > 1.5
        * Dominant sentiment == "bearish"
    - Function: get_bearish_whale_flow(ticker) -> dict
4. INVERTED COMPOSITE SCORER (for RED regime):
Create BearishCompositeScorer class that inherits from CompositeScorer:
    - Regime pillar: RED=15pts, YELLOW=8pts, GREEN=0pts (inverted)
    - Trend pillar: price < 200 SMA (+5), SMA20 < SMA200 (+3), ADX > 25 (+5)
    - Pullback pillar: Williams %R > -20 (+10), RSI > 65 (+5), distance above MA (+5)
    - Momentum pillar: MACD hist declining (+6), RSI > 70 (+5), volume ratio > 1.5 (+5)
    - Pattern pillar: distribution (+3), breakdown (+3), descending channel (+2), head\&shoulders (+2)

Class: BearishCompositeScorer(CompositeScorer)
Method: score_short_candidate(ticker, technicals, whale_data) -> ScoreBreakdown
5. SECTOR-RELATIVE WEAKNESS:
    - Import from sector_rotation import get_sector_rankings
    - Find stocks in bottom 3 sectors that are also individually weak
    - Compute relative_weakness_score: (stock_performance - sector_avg) < -5% = +5 bonus

Function: score_relative_weakness(ticker, sector_data) -> int (0-5)
6. SHORT PULLBACK DETECTION:
Identify bearish pullbacks (rallies into resistance):
    - Price rallies to 20 SMA or 50 EMA from below
    - Volume declining on rally
    - RSI approaches 60-70 (overbought zone)
    - This is the optimal short entry (fade the rally)

Function: detect_short_pullback(bars, indicators) -> bool
7. FOM EXPECTED MOVES FOR SHORTS:
    - Import from fom_expected_moves import get_expected_move
    - If breakdown distance is 40-60% of expected move, flag as "proportional breakdown"
    - Use this to size stop losses: stop = entry + (0.4 * expected_move)

Function: calculate_short_stop(entry_price, expected_move) -> float
8. SHORT TRIGGER CONDITIONS:
Multi-confirmation:
    - Bearish pattern detected (distribution OR breakdown OR descending channel)
    - AND RSI > 65 OR Williams %R > -30
    - AND bearish whale flow present (put premium > \$50K)
    - AND price < 50 EMA AND 50 EMA < 200 SMA

Function: detect_short_trigger(bars, indicators, whale_data) -> bool
9. INTEGRATION WITH DAILY SCANNER:
Modify daily_scanner.py:
    - In run_full_scan(), check if regime == 'RED'
    - If RED, run parallel short scan:
        * bearish_scorer = BearishCompositeScorer(regime_data, macro_data)
        * short_candidates = short_detector.batch_detect_shorts(all_tickers)
        * short_scored = bearish_scorer.score_watchlist(short_candidates)
    - Post separate Slack message: ":chart_with_downwards_trend: *SHORT CANDIDATES (RED Regime):*"
10. DATA STRUCTURE:
Return comprehensive short data:
```python
{
  "ticker": "AAPL",
  "short_setup_detected": True,
  "pattern": "distribution",
  "bearish_score": 76.0,
  "bearish_indicators": {
    "williams_r": -15,
    "rsi": 72,
    "below_200sma": True,
    "macd_declining": True
  },
  "bearish_whale_flow": {"put_premium": 125000, "sentiment": "bearish"},
  "relative_weakness_score": 4,
  "short_pullback": True,
  "trigger_active": True,
  "entry_zone": 184.50,
  "stop_loss": 187.20,
  "expected_move_pct": 3.1,
  "confidence": 0.76
}
```

11. BATCH PROCESSING:
Function: batch_detect_shorts(tickers: List[str]) -> Dict[str, dict]

TESTING:
Write tests/test_short_detector.py with bearish scenario data.

DELIVERABLE:

- short_detector.py (500-600 lines)
- BearishCompositeScorer class
- tests/test_short_detector.py
- Integration diffs for daily_scanner.py and composite_scorer.py

```

***

## PROMPT 5: AI-Driven Dynamic Weight Optimization

```

CREATE: dynamic_weights.py

Build an online Bayesian optimization system that learns optimal pillar weights from actual trade outcomes.

REQUIREMENTS:

1. WEIGHT OPTIMIZATION ENGINE:
    - Use Optuna library for Bayesian optimization
    - Objective function: Maximize Sharpe ratio over trailing 30 closed trades
    - Parameters to optimize:
        * regime_weight: 10-30
        * trend_weight: 15-35
        * pullback_weight: 15-35
        * momentum_weight: 10-30
        * pattern_weight: 5-15
    - Constraint: sum of weights must equal 100

Function: optimize_weights(trade_history) -> dict
2. REGIME-CONDITIONED WEIGHTS:
Store separate weight sets per regime:

```python
OPTIMIZED_WEIGHTS = {
  "GREEN": {"regime": 18, "trend": 28, "pullback": 24, "momentum": 22, "pattern": 8},
  "YELLOW": {"regime": 22, "trend": 25, "pullback": 25, "momentum": 18, "pattern": 10},
  "RED": {"regime": 25, "trend": 20, "pullback": 28, "momentum": 17, "pattern": 10}
}
```

Function: get_regime_weights(regime: str) -> dict
3. CONTINUOUS LEARNING LOOP:
    - After every trade closes (detected via performance_tracker.py):
        * Load last 30 closed trades
        * Run Optuna optimization (50 trials)
        * If new weights produce Sharpe > current + 0.1, adopt them
        * Persist to data/optimized_weights.json

Function: continuous_weight_update() -> bool
4. PERFORMANCE METRICS:
Track for each weight set:
    - Sharpe ratio (risk-adjusted return)
    - Win rate (% profitable trades)
    - Profit factor (gross_profit / gross_loss)
    - Max drawdown
    - Average R-multiple

Function: calculate_weight_performance(trades, weights) -> dict
5. INTEGRATION WITH COMPOSITE SCORER:
Modify composite_scorer.py:
    - In __init__, load weights from dynamic_weights.get_regime_weights(regime)
    - Replace hardcoded pillar maxes with loaded weights
    - Add dynamic_weights attribute to ScoreBreakdown for audit trail
6. BACKTESTING VALIDATION:
Before adopting new weights:
    - Backtest on last 100 historical signals from memory.py
    - Compare new_weights performance vs old_weights
    - Only adopt if new_weights improve Sharpe by 10%+

Function: validate_new_weights(old_weights, new_weights, historical_signals) -> bool
7. WEEKLY RE-OPTIMIZATION SCHEDULE:
    - Every Friday 4:30 PM ET, run full optimization
    - Use all closed trades from the past week
    - Post results to Slack: ":chart_with_upwards_trend: *Weight Optimization Results:* Sharpe improved 15% | New weights: R:22 T:27 P:23 M:20 Pat:8"

Function: scheduled_optimization() -> dict
8. FOM EXPECTED MOVES WEIGHT:
Add 6th pillar: "expected_move_alignment" (max 10 points)
    - Score: If entry is within optimal zone of expected move (40-60%), +10pts
    - Add to optimization: expected_move_weight: 5-15

This treats FOM data as a quantitative factor in scoring, not just informational.
9. WEIGHT CONFIDENCE TRACKING:
    - Track how many trades each weight set has been used for
    - Low-confidence (<20 trades): apply with 0.9x multiplier
    - High-confidence (50+ trades): apply at full value

Function: get_weight_confidence(regime: str) -> float (0.5-1.0)
10. CLI COMMANDS:

- python dynamic_weights.py --optimize (run manual optimization)
- python dynamic_weights.py --show (display current weights + performance)
- python dynamic_weights.py --backtest (validate against historical data)

11. DATA PERSISTENCE:
Save to data/optimized_weights.json:
```json
{
  "GREEN": {
    "weights": {"regime": 18, "trend": 28, "pullback": 24, "momentum": 22, "pattern": 8, "em_alignment": 0},
    "performance": {"sharpe": 1.85, "win_rate": 0.64, "profit_factor": 2.1, "trades": 47},
    "last_updated": "2026-02-20T16:30:00",
    "confidence": 0.95
  },
  "YELLOW": {...},
  "RED": {...}
}
```

TESTING:
Write tests/test_dynamic_weights.py with synthetic trade outcome data.

DELIVERABLE:

- dynamic_weights.py (300-400 lines)
- tests/test_dynamic_weights.py
- Integration diffs for composite_scorer.py
- Migration script to initialize data/optimized_weights.json

```

***

## PROMPT 6: XGBoost Ensemble Scoring Layer

```

CREATE: ensemble_scorer.py

Build a machine learning ensemble that blends rule-based composite scoring with gradient-boosted probability predictions.

REQUIREMENTS:

1. FEATURE ENGINEERING:
Extract features from every candidate:
    - Pillar scores: regime_score, trend_score, pullback_score, momentum_score, pattern_score (5 features)
    - Sub-indicators: rsi, williams_r, adx, macd_hist, volume_ratio, atr_pct (ATR/price), price_change_5d (7 features)
    - Regime context: regime_numeric (GREEN=2, YELLOW=1, RED=0), vix, hurst_exponent, hmm_confidence (4 features)
    - Whale data: whale_premium_log (log10 of premium), dominant_sentiment_numeric (bull=1, bear=-1, neutral=0) (2 features)
    - Sector: sector_rank (1-11), sector_hot (1/0), sector_cold (1/0) (3 features)
    - Calendar: days_to_earnings, is_friday (1/0) (2 features)
    - FOM: expected_move_pct, entry_distance_pct_of_em (2 features)

Total: 25 features

Function: extract_features(candidate: dict) -> np.array
2. TARGET VARIABLE:
Binary classification: Did stock gain 2%+ within 5 trading days?
    - Load from performance_tracker.py: get_trade_outcomes()
    - Join with historical signals from memory.py
    - Label: 1 if 5-day return >= 2%, 0 otherwise

Function: build_training_dataset() -> (X, y, metadata)
3. MODEL TRAINING:
Use XGBoost with:
    - Objective: binary:logistic
    - Eval metric: AUC-ROC + log loss
    - Max depth: 6
    - Learning rate: 0.05
    - N_estimators: 200
    - Early stopping: 20 rounds on validation set (20% holdout)

Train separate models per regime (GREEN, YELLOW, RED)

Function: train_ensemble_models(X, y, regime_labels) -> dict
4. MODEL PERSISTENCE:
Save models to models/ directory:
    - models/xgb_ensemble_green.pkl
    - models/xgb_ensemble_yellow.pkl
    - models/xgb_ensemble_red.pkl
    - models/feature_scaler.pkl (StandardScaler for normalization)

Save feature importance to data/feature_importance.json for analysis
5. PREDICTION PIPELINE:
For each new candidate:
    - Extract 25 features
    - Scale using saved scaler
    - Load regime-specific model
    - Predict probability: P(gain >= 2% in 5 days)

Function: predict_ensemble_score(candidate: dict, regime: str) -> float (0-1)
6. INTEGRATION AS 6TH PILLAR:
Modify composite_scorer.py:
    - Add ml_ensemble_score pillar (max 15 points)
    - ml_score = ensemble_scorer.predict(candidate, regime) * 15
    - New total: Regime(20) + Trend(25) + Pullback(25) + Momentum(20) + Pattern(10) + ML(15) = 115 points
    - Adjust tier thresholds: SLAM: 95+, HIGH: 80+, TRADEABLE: 65+
7. FOM EXPECTED MOVES AS FEATURE:
Two FOM-derived features:
    - expected_move_pct: Daily expected move % from FOM data
    - entry_distance_pct_of_em: How far current pullback is as % of expected move
        * Example: Stock EM = 3%, current pullback = 1.8%, entry_distance = 60%

This teaches the model that entries near 50-70% of expected move have higher win rates.
8. MODEL RETRAINING SCHEDULE:
    - Retrain weekly (Saturday 2 AM) using all trades from past 90 days
    - Require minimum 100 trades per regime for training
    - Post performance to Slack: ":brain: *ML Model Retrained:* AUC: 0.76 -> 0.81 | Features: top 5 = [williams_r, rsi, volume_ratio, em_distance, sector_rank]"

Function: scheduled_retraining() -> dict
9. FEATURE IMPORTANCE ANALYSIS:
After each training:
    - Extract SHAP values for feature importance
    - Identify which features matter most per regime
    - Adjust rule-based scorer weights to align with ML insights

Function: analyze_feature_importance(model, X) -> dict
10. ENSEMBLE CONFIDENCE:

- If ML prediction is 0.45-0.55 (uncertain), reduce ml_score by 50%
- If ML prediction is >0.7 or <0.3 (confident), apply full ml_score
- Track model calibration: compare predicted probabilities to actual outcomes

Function: calculate_ensemble_confidence(prediction: float) -> float

11. CLI COMMANDS:

- python ensemble_scorer.py --train (manual training run)
- python ensemble_scorer.py --predict AAPL (single stock prediction)
- python ensemble_scorer.py --evaluate (compute test set metrics)
- python ensemble_scorer.py --shap (generate SHAP value plots)

12. DATA STRUCTURE:
Enhance ScoreBreakdown in composite_scorer.py:
```python
{
  "ticker": "AAPL",
  "regime_score": 18.0,
  "trend_score": 23.5,
  "pullback_score": 22.0,
  "momentum_score": 19.5,
  "pattern_score": 8.0,
  "ml_ensemble_score": 12.3,  # NEW
  "total": 103.3,
  "tier": "SLAM",
  "ml_prediction": 0.82,  # NEW: raw probability
  "ml_confidence": 0.95,  # NEW: model confidence
  "top_features": ["williams_r", "rsi", "volume_ratio"]  # NEW
}
```

TESTING:
Write tests/test_ensemble_scorer.py with mock training data.

DELIVERABLE:

- ensemble_scorer.py (400-500 lines)
- tests/test_ensemble_scorer.py
- Integration diffs for composite_scorer.py
- models/ directory with .pkl files
- Training notebook: notebooks/ensemble_training.ipynb

```

***

## PROMPT 7: Real-Time Execution & Risk Governor

```

CREATE: auto_executor.py and risk_governor.py

Build immediate execution system with real-time portfolio heat monitoring and correlation checks.

REQUIREMENTS FOR auto_executor.py:

1. SIGNAL QUEUE CONSUMER:
    - Listen for SIGNAL_READY events from streaming_engine.py
    - Use asyncio.Queue for event handling
    - Process signals in order of score (highest first)

Async function: consume_signals() -> None
2. EXECUTION PIPELINE:
For each signal with score >= 75:
    - Call risk_governor.check_execution_allowed(ticker, entry_price, stop_loss)
    - If approved, calculate position size via position_sizer.calculate_position()
    - Place bracket order via alpaca_client.place_bracket_order()
    - Log to performance_tracker.py
    - Post to Slack: ":rocket: EXECUTING: AAPL | 100 shares | Entry: \$182.45 | Stop: \$180.12 | Target: \$186.20"

Async function: execute_signal(signal: dict) -> dict
3. BRACKET ORDER CONSTRUCTION:
    - Entry: Limit order at calculated entry_price (from pullback_detector or smart_entry.py)
    - Stop loss: 1.5 ATR below entry (or use short_detector stop for shorts)
    - Take profit: 2x stop distance (2:1 R:R minimum)
    - Time in force: DAY (cancel at 4PM if not filled)

Function: build_bracket_order(ticker, qty, entry, stop, target) -> dict
4. EXECUTION CONFIRMATION:
    - Wait for Alpaca fill confirmation (max 10 seconds)
    - If filled, update position_manager.py with new position
    - If not filled, log as "missed_entry" in performance tracker
    - Retry with adjusted limit price if within 0.3 ATR of original entry
5. MAXIMUM DAILY TRADES:
    - Limit: 10 executions per day (configurable)
    - Counter resets at 9:30 AM ET daily
    - After limit hit, queue remaining signals as "watchlist_only"
6. FOM EXPECTED MOVES IN EXECUTION:
    - Import from fom_expected_moves import get_expected_move
    - Set take_profit target based on expected move:
        * If EM = 3%, set target = entry + (0.5 * EM) for first target
        * Partial exit 50% of position at 50% of EM
        * Let remaining 50% run to 100% of EM or trailing stop

Function: calculate_em_based_targets(entry, expected_move) -> (target1, target2)

REQUIREMENTS FOR risk_governor.py:

1. PORTFOLIO HEAT MONITORING:
    - Query all open positions from alpaca_client.get_positions()
    - Calculate total_risk = sum of (position_size * distance_to_stop) for all positions
    - Max portfolio heat: 6% of account equity
    - If adding new position would exceed 6%, REJECT execution

Function: calculate_portfolio_heat() -> float
2. CORRELATION MATRIX:
    - Fetch 30-day returns for all current holdings + new candidate
    - Calculate Pearson correlation matrix using pandas
    - If any existing position has correlation > 0.75 with candidate, REJECT
    - If sector exposure already at 30%+ of portfolio and candidate is same sector, REJECT

Function: check_correlation(ticker: str, existing_positions: List[str]) -> bool
3. POSITION LIMITS:
Enforce:
    - Max 5% of equity per position
    - Max 60% total equity deployed (up to 12 positions at 5% each)
    - Max 3 positions per sector
    - Max 2 positions with same expected move (avoids volatility clustering)

Function: check_position_limits(ticker, size, sector, expected_move) -> bool
4. REGIME-BASED EXPOSURE SCALING:
    - GREEN: allow up to 60% portfolio deployed
    - YELLOW: limit to 40% deployed
    - RED: limit to 20% deployed (only highest-conviction longs + shorts)

Function: get_regime_exposure_limit(regime: str) -> float
5. CIRCUIT BREAKER:
    - If daily P\&L drops below -3% of equity, HALT all new executions
    - Post to Slack: ":warning: CIRCUIT BREAKER TRIGGERED | Daily P\&L: -3.2% | All new trades halted"
    - Resume next day at 9:30 AM

Function: check_circuit_breaker() -> bool
6. REAL-TIME HEAT MAP:
    - Generate correlation heatmap of current positions every 15 minutes
    - Save to data/position_heatmap_{timestamp}.png
    - Post to Slack if any pair shows correlation > 0.8: ":warning: High correlation: AAPL <-> MSFT (0.87)"

Function: generate_correlation_heatmap() -> str (path to image)
7. INTEGRATION FLOW:

```
streaming_engine.py emits SIGNAL_READY
     ↓
auto_executor.py receives signal
     ↓
risk_governor.check_execution_allowed() → TRUE/FALSE
     ↓
if TRUE: place bracket order via alpaca_client
     ↓
position_manager.py tracks position lifecycle
```

8. SLACK NOTIFICATIONS:
Post to \#oc-trade-desk:
    - Execution confirmations: ":white_check_mark: FILLED: AAPL 100 @ \$182.48"
    - Risk rejections: ":octagonal_sign: REJECTED: TSLA (correlation with AAPL 0.82)"
    - Circuit breaker: ":rotating_light: TRADING HALTED"
    - Daily summary: ":chart_with_upwards_trend: EOD Summary | Executed: 7 | Rejected: 3 | Portfolio heat: 4.2%"
9. CLI COMMANDS:
    - python auto_executor.py --start (run executor daemon)
    - python risk_governor.py --check (current portfolio heat + correlations)
    - python risk_governor.py --heatmap (generate correlation heatmap)
10. DATA PERSISTENCE:
Log all execution decisions to data/execution_log_{date}.json:
```json
{
  "timestamp": "2026-02-20T12:47:33",
  "ticker": "AAPL",
  "signal_score": 82.3,
  "trigger": "pullback_entry",
  "action": "executed" | "rejected",
  "rejection_reason": "correlation_limit" | null,
  "portfolio_heat_before": 3.8,
  "portfolio_heat_after": 4.5,
  "positions_before": 8,
  "positions_after": 9
}
```

TESTING:
Write tests/test_auto_executor.py and tests/test_risk_governor.py with mock signals and positions.

DELIVERABLE:

- auto_executor.py (300-400 lines)
- risk_governor.py (300-400 lines)
- tests/test_auto_executor.py
- tests/test_risk_governor.py
- Integration with streaming_engine.py and alpaca_client.py

```

***

## PROMPT 8: Master Integration & FOM Enhancement

```

MODIFY: main.py, daily_scanner.py, fom_expected_moves.py, composite_scorer.py

Integrate all new modules into a unified real-time + daily hybrid system with full FOM expected moves utilization.

REQUIREMENTS:

1. ENHANCE fom_expected_moves.py:
Add function: get_expected_move(ticker: str) -> float
    - Query the cached FOM data from last scrape
    - Return expected_move_pct for the given ticker
    - If not found, calculate from ATR as fallback: (ATR / price) * 100
    - Cache results in Redis or JSON for 1 hour

Add to existing scraper output:

```python
EXPECTED_MOVES_CACHE = {
  "AAPL": {"em_pct": 2.8, "em_dollars": 5.10, "last_updated": "2026-02-20T09:00:00"},
  "TSLA": {"em_pct": 4.5, "em_dollars": 9.20, "last_updated": "2026-02-20T09:00:00"}
}
```

2. CREATE: main.py (NEW orchestrator)
Replace the current main.py with unified orchestrator:

```python
async def main():
    # 1. Run daily_scanner.py at 9:00 AM (pre-market)
    daily_results = await run_daily_scan()
    
    # 2. Export to data/daily_watchlist.json for streaming_engine
    export_watchlist(daily_results['watchlist'])
    
    # 3. Start streaming_engine.py (runs 9:30 AM - 4:00 PM)
    streaming_task = asyncio.create_task(streaming_engine.run())
    
    # 4. Start auto_executor.py (consumes signals from streaming)
    executor_task = asyncio.create_task(auto_executor.run())
    
    # 5. Start risk_governor.py monitoring (every 15 min)
    risk_task = asyncio.create_task(risk_governor.monitor_loop())
    
    # 6. Dynamic weight optimization (if Friday 4:30 PM)
    if is_friday_close():
        await dynamic_weights.scheduled_optimization()
    
    # 7. Ensemble model retraining (if Saturday 2:00 AM)
    if is_saturday_morning():
        await ensemble_scorer.scheduled_retraining()
    
    # 8. Wait for market close, then shutdown streaming
    await wait_until_market_close()
    streaming_task.cancel()
    executor_task.cancel()
    risk_task.cancel()
```

3. MODIFY: daily_scanner.py
Add calls to new detectors in Step 12 (after composite scoring):

```python
# Import new detectors
from pullback_detector import batch_detect_pullbacks
from rebound_detector import batch_detect_rebounds
from short_detector import batch_detect_shorts

# In run_full_scan(), after composite_scorer runs:

# Pullback detection
pullback_data = batch_detect_pullbacks(all_tickers)
for item in watchlist:
    pb = pullback_data.get(item['ticker'], {})
    if pb.get('quality_score', 0) > 70:
        item['composite_score'] += 5  # Bonus for quality pullback
    item['pullback_data'] = pb

# Rebound detection
rebound_data = batch_detect_rebounds(all_tickers)
for item in watchlist:
    rb = rebound_data.get(item['ticker'], {})
    if rb.get('trigger_active'):
        item['composite_score'] += 3  # Bonus for rebound trigger
    item['rebound_data'] = rb

# Short detection (only in RED regime)
if regime == 'RED':
    short_data = batch_detect_shorts(all_tickers)
    short_scored = bearish_scorer.score_watchlist(short_data)
    # Add to watchlist with negative tier
    for s in short_scored:
        if s.total >= 65:
            watchlist.append({
                'ticker': s.ticker,
                'tier': 'SHORT',
                'composite_score': s.total,
                'short_data': short_data.get(s.ticker, {})
            })
```

4. MODIFY: composite_scorer.py
Add FOM expected moves pillar:

```python
from fom_expected_moves import get_expected_move

# In CompositeScorer.__init__:
self.em_cache = {}

# New method:
def _score_expected_move_alignment(self, tech: Dict) -> float:
    """Score entry quality relative to expected move."""
    score = 0.0
    ticker = tech.get('ticker')
    em_data = get_expected_move(ticker)
    if not em_data:
        return 0.0
    
    em_pct = em_data.get('em_pct', 0)
    price = tech.get('price', 0)
    sma_20 = tech.get('sma_20', 0)
    
    if price and sma_20 and em_pct:
        pullback_pct = abs(price - sma_20) / sma_20 * 100
        em_ratio = pullback_pct / em_pct
        
        # Optimal: pullback is 40-70% of expected move
        if 0.4 <= em_ratio <= 0.7:
            score += 10
        elif 0.3 <= em_ratio < 0.4 or 0.7 < em_ratio <= 0.9:
            score += 5
        elif em_ratio < 0.2:  # Too shallow
            score -= 2
        elif em_ratio > 1.0:  # Too deep
            score -= 3
    
    return min(10, score)

# In score_candidate():
breakdown.em_score = self._score_expected_move_alignment(technicals)
raw = (breakdown.regime_score + breakdown.trend_score +
       breakdown.pullback_score + breakdown.momentum_score +
       breakdown.pattern_score + breakdown.em_score +  # NEW
       breakdown.bonus + breakdown.penalty)
```

5. INTEGRATION TESTING:
Create tests/test_integration.py:
    - Mock full pipeline: daily_scan → streaming → execution
    - Verify signals flow from scanner → streaming_engine → auto_executor
    - Test all detector modules get called and produce valid output
    - Verify FOM data populates composite scores correctly
6. SLACK COMMAND EXTENSIONS:
Add to app.py:
    - /oc stream status → Show streaming_engine running status + subscriptions
    - /oc risk → Show current portfolio heat, correlations, circuit breaker status
    - /oc weights → Show current optimized weights per regime
    - /oc ml → Show ML model performance metrics
    - /oc em AAPL → Show FOM expected move for ticker
7. DOCUMENTATION:
Update README.md with:
    - New real-time architecture diagram
    - Module dependency graph
    - Setup instructions for all new components
    - Configuration guide for streaming vs batch modes

Add REAL_TIME_TRADING_GUIDE.md:
    - How the streaming engine works
    - Signal trigger explanations
    - Risk governor rules and overrides
    - Monitoring and debugging guide
8. CONFIGURATION:
Add to config.py:

```python
# Real-time trading config
STREAMING_ENABLED = os.getenv('STREAMING_ENABLED', 'true').lower() == 'true'
MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '10'))
MAX_PORTFOLIO_HEAT = float(os.getenv('MAX_PORTFOLIO_HEAT', '0.06'))
CORRELATION_THRESHOLD = float(os.getenv('CORRELATION_THRESHOLD', '0.75'))
CIRCUIT_BREAKER_THRESHOLD = float(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '-0.03'))

# FOM expected moves
FOM_CACHE_HOURS = int(os.getenv('FOM_CACHE_HOURS', '6'))
FOM_FALLBACK_ATR_MULTIPLIER = float(os.getenv('FOM_FALLBACK_ATR_MULTIPLIER', '1.0'))

# ML ensemble
ML_ENSEMBLE_ENABLED = os.getenv('ML_ENSEMBLE_ENABLED', 'true').lower() == 'true'
ML_RETRAIN_SCHEDULE = os.getenv('ML_RETRAIN_SCHEDULE', 'saturday_02:00')
MIN_TRAINING_SAMPLES = int(os.getenv('MIN_TRAINING_SAMPLES', '100'))
```

9. MONITORING DASHBOARD:
Create dashboard.py (Flask web app):
    - Real-time display of:
        * Current streaming subscriptions
        * Live scores for top 10 candidates
        * Portfolio heat gauge
        * Correlation matrix heatmap
        * Recent executions table
        * ML model performance metrics
    - Accessible at http://localhost:5001
    - Auto-refresh every 30 seconds
10. DEPLOYMENT:
Update deploy.ps1 and start.sh:
```bash
# Start all components
python main.py &            # Master orchestrator
python dashboard.py &       # Monitoring dashboard
python app.py              # Slack bot (foreground)
```

11. ERROR RECOVERY:
Add health checks to main.py:

- Ping streaming_engine every 60s, restart if unresponsive
- Check Alpaca WebSocket connection, reconnect if dropped
- Verify all detector modules can import successfully
- Log all errors to logs/health_check.log

12. PERFORMANCE TRACKING:
Enhance performance_tracker.py to log:

- Detector that generated the signal (pullback/rebound/breakout/short)
- FOM expected move at entry
- ML ensemble prediction at entry
- Actual outcome vs predicted

Generate weekly report comparing:

- Rule-based signals vs ML-enhanced signals
- Pullback entries vs rebound entries vs breakout entries
- Long trades vs short trades (in RED regime)

TESTING:
Write tests/test_master_integration.py with full end-to-end scenarios.

DELIVERABLE:

- main.py (new unified orchestrator, 300-400 lines)
- dashboard.py (monitoring web app, 200-300 lines)
- Updated daily_scanner.py with detector integration
- Updated composite_scorer.py with EM alignment pillar
- Enhanced fom_expected_moves.py with get_expected_move() function
- Updated config.py with all new settings
- REAL_TIME_TRADING_GUIDE.md (comprehensive guide)
- Updated README.md
- tests/test_master_integration.py

```

***

## EXECUTION ORDER

Give these prompts to Comet in sequence:
1. Context Block (always first)
2. Prompt 1 (Streaming Engine) — establishes real-time foundation
3. Prompt 2 (Pullback Detector) — adds long entry quality
4. Prompt 3 (Rebound Detector) — adds reversal entries
5. Prompt 4 (Short Detector) — monetizes bearish setups
6. Prompt 5 (Dynamic Weights) — enables learning from outcomes
7. Prompt 6 (XGBoost Ensemble) — adds ML prediction layer
8. Prompt 7 (Auto Executor + Risk Governor) — ties execution together
9. Prompt 8 (Master Integration) — unifies everything with FOM enhancement

Each prompt is self-contained. Comet can implement them one at a time, test, commit, then move to the next. The result will be a fully real-time, AI-enhanced, multi-strategy trading system that learns and adapts from every trade.```

