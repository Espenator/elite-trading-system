# 🚀 ELITE TRADER: ALL 12 CLAUDE OPUS 4.5 PROMPTS

**Complete Build Guide for Oleh**  
**Date:** December 12, 2025, 4:45 PM EST  
**Repository:** https://github.com/Espenator/elite-trading-system.git  
**Status:** ✅ ALL 12 MODULES READY  
**Timeline:** 10-14 hours total  

---

## 📋 TABLE OF CONTENTS

1. MessageBus (Event Routing) - 45-60 min
2. Alpaca WebSocket (Real-Time) - 30-45 min  
3. Streaming Features (O(1) Updates) - 45-60 min
4. River ML (Online Learning) - 45-60 min
5. XGBoost Validator (Drift Detection) - 30-45 min
6. Unusual Whales (Options Flow) - 45-60 min
7. Risk Validator (6-Layer Gates) - 45-60 min
8. Position Sizer (VIX-Adjusted) - 20-30 min
9. Signal Fusion (Multi-Source) - 30-45 min
10. Alpaca Trading + Approval - 60-90 min
11. Parallel Processing (1600 Symbols) - 30-45 min
12. Monitoring/Alerts (Telegram) - 30-45 min

---

## 🎯 HOW TO USE THESE PROMPTS

1. Open Claude Opus 4.5 (or Claude Code mode)
2. Copy one prompt at a time
3. Paste into Claude
4. Save the generated code to the specified file path
5. Move to next prompt
6. Test as you go

---

## PROMPT 4: RIVER ML ONLINE LEARNING ENGINE

**Time:** 45-60 minutes  
**File:** `backend/learning/river_online_engine.py`  
**Dependencies:** river==0.21.0

```markdown
You are implementing an online machine learning engine using the River library that learns from every completed trade.

CONTEXT:
- Current system has NO learning - static rule-based signals
- Target: Continuous learning from every trade outcome (win/loss)
- River uses incremental algorithms that update with each sample
- Integration with MessageBus for position.closed events

YOUR TASK:
Build a RiverOnlineEngine that:

1. **Prediction Phase:**
   - Takes 75 features from StreamingFeatureEngine
   - Returns win probability (0.0 to 1.0) for a trade
   - Uses ensemble of online models (per-symbol + global)

2. **Learning Phase:**
   - Receives trade outcome (1=win, 0=loss) when position closes
   - Updates model incrementally in <5ms
   - Tracks accuracy metrics per symbol and globally

3. **Persistence:**
   - Auto-saves models every 100 trades
   - Loads previous models on startup
   - Stores under storage/models/river/

KEY REQUIREMENTS:

```python
from river import ensemble, metrics
from typing import Dict, Optional
import pickle
from pathlib import Path

class RiverOnlineEngine:
    def __init__(self, model_dir: str = "storage/models/river"):
        # Global model for all symbols
        self.global_model = ensemble.AdaptiveRandomForestClassifier(
            n_models=10,
            lambda_value=6,
            drift_window_threshold=300
        )
        
        # Per-symbol models (lazy initialization)
        self.symbol_models = {}
        
        # Accuracy tracking
        self.global_accuracy = metrics.Accuracy()
        self.symbol_accuracy = {}
    
    def predict_proba(self, symbol: str, features: dict) -> float:
        """Predict win probability (0-1)"""
        pass
    
    def learn_from_outcome(self, symbol: str, features: dict, outcome: int):
        """Update model with trade result (1=win, 0=loss)"""
        pass
    
    def get_symbol_stats(self, symbol: str) -> dict:
        """Return {accuracy, n_samples, drift_count}"""
        pass
```

FEATURE HANDLING:
- Clean NaN values → 0.0
- Convert numpy types to Python float
- Handle missing features gracefully

BLENDING STRATEGY:
- 70% symbol-specific model
- 30% global model
- Fallback to 0.5 if model not ready

MESSAGEBUS INTEGRATION:
```python
async def on_position_closed(data: dict):
    # data = {"symbol": "AAPL", "features": {...}, "outcome": 1}
    engine.learn_from_outcome(
        data["symbol"],
        data["features"],
        data["outcome"]
    )
    
    # Publish update event
    await message_bus.publish("model.updated", {
        "symbol": data["symbol"],
        "stats": engine.get_symbol_stats(data["symbol"])
    })
```

SUCCESS CRITERIA:
- ✅ Prediction: <2ms per call
- ✅ Learning: <5ms per call
- ✅ Handles 1000+ symbols without memory issues
- ✅ Models persist across restarts
- ✅ Accuracy improves over time (track this!)

Generate the complete production-ready code now.
```

---

## PROMPT 5: XGBOOST DRIFT VALIDATOR

**Time:** 30-45 minutes  
**File:** `backend/learning/xgboost_validator.py`  
**Dependencies:** xgboost==2.0.3, scikit-learn==1.4.0, pandas==2.2.0

```markdown
You are building an offline validator that trains XGBoost on historical trades to detect River model drift.

CONTEXT:
- River learns incrementally → might drift in regime changes
- Need nightly validation against batch-trained XGBoost
- If XGBoost significantly outperforms River → drift alert

YOUR TASK:
Build XGBoostValidator that:

1. **Data Loading:**
   - Fetch last 30 days of trades from CSV/Postgres
   - Each trade has: features (75), outcome (0/1), river_pred (0-1)

2. **Training:**
   - Train XGBoost classifier on 80% of data
   - Test on remaining 20%
   - Compute AUC and accuracy

3. **Comparison:**
   - Compare XGBoost metrics to River's historical predictions
   - If XGBoost AUC > River AUC by >15% → DRIFT DETECTED

4. **Reporting:**
   - Generate DriftReport with all metrics
   - Publish to MessageBus: model.drift_detected

CODE STRUCTURE:

```python
from pydantic import BaseModel
from datetime import datetime
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score

class DriftReport(BaseModel):
    river_auc: float
    xgb_auc: float
    river_accuracy: float
    xgb_accuracy: float
    drift_detected: bool
    drift_magnitude: float
    sample_size: int
    generated_at: datetime

class TradeHistoryRepository:
    """Abstract interface - implement for CSV/Postgres"""
    def get_labeled_trades(self, days_back: int) -> List[TradeRecord]:
        pass

class XGBoostValidator:
    def __init__(self, repository, drift_threshold=0.15):
        self.repository = repository
        self.drift_threshold = drift_threshold
        self.xgb_params = {
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "objective": "binary:logistic"
        }
    
    def run_validation(self, days_back=30) -> DriftReport:
        # 1. Load trades
        # 2. Train/test split
        # 3. Train XGBoost
        # 4. Compare metrics
        # 5. Return report
        pass
```

SCHEDULING (use APScheduler):
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    run_nightly_validation,
    'cron',
    hour=2,  # 2 AM EST
    args=[validator, message_bus]
)
scheduler.start()
```

SUCCESS CRITERIA:
- ✅ Handles 50k-200k trade records
- ✅ Fails gracefully with <100 samples
- ✅ Drift detection is accurate
- ✅ Report published to MessageBus

Generate the complete production-ready code now.
```

---

## PROMPT 6: UNUSUAL WHALES OPTIONS FLOW

**Time:** 45-60 minutes  
**Files:** 
- `backend/services/unusual_whales_client.py`
- `backend/services/unusual_whales_stream.py`
- `backend/features/whales_features.py`

```markdown
You are integrating Unusual Whales API to enrich equity signals with institutional options flow data.

CONTEXT:
- Unusual Whales provides real-time options flow, sweeps, dark pool data
- REST API for historical queries
- WebSocket for real-time whale trades
- Goal: Boost signal scores when big money is aligned

YOUR TASK:
Build 3 components:

### 1. REST CLIENT (unusual_whales_client.py)

```python
import httpx
from typing import List, Optional
from pydantic import BaseModel

class FlowRecord(BaseModel):
    symbol: str
    side: str  # CALL/PUT
    sentiment: str  # BULLISH/BEARISH/NEUTRAL
    premium: float
    size: int
    timestamp: datetime

class UnusualWhalesClient:
    def __init__(self, api_key: str, base_url="https://api.unusualwhales.com/api"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def get_ticker_flow(
        self, 
        symbol: str, 
        lookback_minutes: int = 30
    ) -> List[FlowRecord]:
        """Fetch recent options flow for symbol"""
        pass
    
    async def get_darkpool(
        self, 
        symbol: str, 
        lookback_minutes: int = 30
    ) -> List[dict]:
        """Fetch recent dark pool prints"""
        pass
```

### 2. WEBSOCKET STREAM (unusual_whales_stream.py)

```python
import websockets
import json

class UnusualWhalesStream:
    def __init__(self, api_key: str, message_bus):
        self.api_key = api_key
        self.message_bus = message_bus
        self.ws_url = "wss://stream.unusualwhales.com"
    
    async def connect_and_stream(self):
        """Connect to WebSocket and stream whale trades"""
        async with websockets.connect(self.ws_url) as ws:
            # Subscribe to flow-alerts channel
            await ws.send(json.dumps({
                "action": "subscribe",
                "channel": "flow-alerts",
                "apiKey": self.api_key
            }))
            
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                # Publish to MessageBus
                await self.message_bus.publish(
                    "options_flow.whale_trade",
                    data
                )
```

### 3. FEATURE BUILDER (whales_features.py)

```python
from collections import deque
from datetime import datetime, timedelta

class WhalesFeatureBuilder:
    """Convert flow data into numeric features"""
    
    def __init__(self, window_minutes=30):
        # Store recent flow per symbol
        self.flow_history = {}  # symbol -> deque of FlowRecord
        self.window_minutes = window_minutes
    
    def update_flow(self, symbol: str, flow: FlowRecord):
        """Add new flow record"""
        if symbol not in self.flow_history:
            self.flow_history[symbol] = deque(maxlen=100)
        
        self.flow_history[symbol].append(flow)
    
    def get_features(self, symbol: str) -> dict:
        """Generate flow features for signal fusion"""
        if symbol not in self.flow_history:
            return self._empty_features()
        
        recent = self._get_recent_flow(symbol)
        
        return {
            "call_put_imbalance": self._calc_cp_imbalance(recent),
            "sweep_notional_5min": self._calc_sweep_notional(recent, 5),
            "darkpool_notional_30min": self._calc_darkpool(recent),
            "bullish_flow_pct": self._calc_bullish_pct(recent),
            "large_lot_count": self._count_large_lots(recent)
        }
    
    def _empty_features(self) -> dict:
        return {
            "call_put_imbalance": 0.0,
            "sweep_notional_5min": 0.0,
            "darkpool_notional_30min": 0.0,
            "bullish_flow_pct": 0.5,
            "large_lot_count": 0
        }
```

ENVIRONMENT SETUP:
```bash
UNUSUAL_WHALES_API_KEY=your_key_here
```

SUCCESS CRITERIA:
- ✅ REST calls return valid data within 500ms
- ✅ WebSocket maintains 24/7 connection
- ✅ Features computed in <1ms per symbol
- ✅ Rate limits respected (429 handling)

Generate all 3 production-ready files now.
```

---

## PROMPT 7: 6-LAYER RISK VALIDATOR

**Time:** 45-60 minutes  
**File:** `backend/risk/validator.py`

```markdown
You are building the institutional-grade risk gate that blocks bad trades before execution.

CONTEXT:
- Every signal must pass 6 risk checks
- Account data from Alpaca: equity, positions, daily P&L
- Config-driven thresholds (risk_config.yml)

YOUR TASK:
Implement RiskValidator with 6 sequential gates:

### GATE 1: Trading State
- HALTED if daily loss ≥ -5%
- CAUTION if daily loss ≥ -3%
- ACTIVE otherwise
- Reject: New trades when HALTED

### GATE 2: Position Count
- Max open positions: 15 (configurable)
- Reject: If already at max

### GATE 3: Position Size
- Max per position: 20% of equity
- Reject or adjust: If exceeds limit

### GATE 4: Daily Loss Circuit Breaker
- Stop all trading at -5% daily loss
- Reduce risk by 50% at -3% loss

### GATE 5: ML Confidence
- Minimum win probability: 70% (configurable)
- Reject: If confidence < threshold

### GATE 6: Signal Freshness
- Max age: 30 minutes
- Reject: If signal too old

CODE STRUCTURE:

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

class RiskDecision(BaseModel):
    approved: bool
    reasons: List[str]
    adjusted_qty: Optional[int]
    risk_score: float  # 0-100

class RiskConfig(BaseModel):
    max_positions: int = 15
    max_position_pct: float = 0.20
    daily_loss_halt: float = -0.05
    daily_loss_caution: float = -0.03
    min_ml_confidence: float = 0.70
    max_signal_age_minutes: int = 30

class RiskValidator:
    def __init__(self, config: RiskConfig):
        self.config = config
    
    def validate(
        self, 
        signal: dict,
        account: dict,
        positions: List[dict]
    ) -> RiskDecision:
        """Run all 6 gates"""
        reasons = []
        adjusted_qty = signal["qty"]
        risk_score = 0
        
        # Gate 1: Trading State
        state = self._check_trading_state(account)
        if state == "HALTED":
            return RiskDecision(
                approved=False,
                reasons=["Trading halted due to daily loss"],
                adjusted_qty=None,
                risk_score=100
            )
        
        # Gate 2: Position Count
        if len(positions) >= self.config.max_positions:
            return RiskDecision(
                approved=False,
                reasons=[f"Max positions reached ({self.config.max_positions})"],
                adjusted_qty=None,
                risk_score=90
            )
        
        # Gate 3: Position Size
        max_notional = account["equity"] * self.config.max_position_pct
        proposed_notional = signal["qty"] * signal["entry_price"]
        
        if proposed_notional > max_notional:
            adjusted_qty = int(max_notional / signal["entry_price"])
            reasons.append(f"Position size adjusted: {signal['qty']} → {adjusted_qty}")
            risk_score += 20
        
        # Gate 4: Daily Loss
        # (handled in Gate 1)
        
        # Gate 5: ML Confidence
        if signal["ml_confidence"] < self.config.min_ml_confidence:
            return RiskDecision(
                approved=False,
                reasons=[f"ML confidence too low: {signal['ml_confidence']:.1%}"],
                adjusted_qty=None,
                risk_score=80
            )
        
        # Gate 6: Signal Freshness
        age_minutes = (datetime.now() - signal["timestamp"]).total_seconds() / 60
        if age_minutes > self.config.max_signal_age_minutes:
            return RiskDecision(
                approved=False,
                reasons=[f"Signal too old: {age_minutes:.0f} minutes"],
                adjusted_qty=None,
                risk_score=70
            )
        
        # All gates passed
        return RiskDecision(
            approved=True,
            reasons=reasons if reasons else ["All risk checks passed"],
            adjusted_qty=adjusted_qty,
            risk_score=risk_score
        )
    
    def _check_trading_state(self, account: dict) -> str:
        daily_pnl_pct = account["daily_pnl"] / account["equity"]
        
        if daily_pnl_pct <= self.config.daily_loss_halt:
            return "HALTED"
        elif daily_pnl_pct <= self.config.daily_loss_caution:
            return "CAUTION"
        else:
            return "ACTIVE"
```

CONFIG FILE (risk_config.yml):
```yaml
max_positions: 15
max_position_pct: 0.20
daily_loss_halt: -0.05
daily_loss_caution: -0.03
min_ml_confidence: 0.70
max_signal_age_minutes: 30
```

SUCCESS CRITERIA:
- ✅ Deterministic decisions
- ✅ Each gate independently testable
- ✅ Config-driven (no hard-coded values)
- ✅ Clear rejection reasons

Generate the complete production-ready code now.
```

---

## PROMPT 8: VIX-ADJUSTED POSITION SIZER

**Time:** 20-30 minutes  
**File:** `backend/risk/position_sizer.py`

```markdown
You are building dynamic position sizing based on account risk and VIX regime.

CONTEXT:
- Base risk: 2% of equity per trade
- VIX multiplier scales position up/down based on volatility
- ATR-based stops determine risk per share

FORMULA:
```
Base Risk = 2% of equity
VIX Multiplier:
  - VIX <15:  1.5x (low vol, increase size)
  - VIX 15-20: 1.0x (normal)
  - VIX 20-30: 0.5x (high vol, reduce)
  - VIX >30:  0.25x (crisis, tiny positions)

Adjusted Risk = Base Risk × VIX Multiplier
Risk Per Share = |Entry - Stop|
Max Shares = Adjusted Risk ÷ Risk Per Share

Cap at 20% of equity total
```

CODE:

```python
from pydantic import BaseModel
from typing import List

class VixBand(BaseModel):
    low: float
    high: float
    multiplier: float

class PositionSizerConfig(BaseModel):
    base_risk_fraction: float = 0.02
    max_position_fraction: float = 0.20
    vix_bands: List[VixBand] = [
        VixBand(low=0, high=15, multiplier=1.5),
        VixBand(low=15, high=20, multiplier=1.0),
        VixBand(low=20, high=30, multiplier=0.5),
        VixBand(low=30, high=100, multiplier=0.25)
    ]

class PositionSizeDecision(BaseModel):
    shares: int
    notional: float
    risk_amount: float
    effective_risk_fraction: float
    vix_multiplier: float
    notes: List[str]

class PositionSizer:
    def __init__(self, config: PositionSizerConfig):
        self.config = config
    
    def size_position(
        self,
        equity: float,
        entry: float,
        stop: float,
        vix_value: float
    ) -> PositionSizeDecision:
        notes = []
        
        # Validate inputs
        if entry == stop:
            return PositionSizeDecision(
                shares=0,
                notional=0,
                risk_amount=0,
                effective_risk_fraction=0,
                vix_multiplier=0,
                notes=["Invalid: entry == stop"]
            )
        
        if equity <= 0:
            return PositionSizeDecision(
                shares=0,
                notional=0,
                risk_amount=0,
                effective_risk_fraction=0,
                vix_multiplier=0,
                notes=["Invalid: equity <= 0"]
            )
        
        # Calculate VIX multiplier
        vix_mult = self._get_vix_multiplier(vix_value)
        notes.append(f"VIX {vix_value:.1f} → {vix_mult}x multiplier")
        
        # Calculate risk amount
        base_risk = equity * self.config.base_risk_fraction
        adjusted_risk = base_risk * vix_mult
        notes.append(f"Risk: ${base_risk:.0f} × {vix_mult} = ${adjusted_risk:.0f}")
        
        # Calculate shares
        risk_per_share = abs(entry - stop)
        shares = int(adjusted_risk / risk_per_share)
        
        # Apply max position cap
        max_notional = equity * self.config.max_position_fraction
        calculated_notional = shares * entry
        
        if calculated_notional > max_notional:
            shares = int(max_notional / entry)
            notes.append(f"Capped at {self.config.max_position_fraction:.0%} of equity")
        
        # Final values
        notional = shares * entry
        actual_risk = shares * risk_per_share
        effective_risk_pct = actual_risk / equity
        
        return PositionSizeDecision(
            shares=shares,
            notional=notional,
            risk_amount=actual_risk,
            effective_risk_fraction=effective_risk_pct,
            vix_multiplier=vix_mult,
            notes=notes
        )
    
    def _get_vix_multiplier(self, vix: float) -> float:
        for band in self.config.vix_bands:
            if band.low <= vix < band.high:
                return band.multiplier
        return 0.25  # Default to crisis mode
```

EXAMPLE:
```python
sizer = PositionSizer(PositionSizerConfig())

decision = sizer.size_position(
    equity=100000,
    entry=150.0,
    stop=145.0,  # $5 ATR stop
    vix_value=18.5
)

print(f"Shares: {decision.shares}")
print(f"Notional: ${decision.notional:,.0f}")
print(f"Risk: ${decision.risk_amount:.0f} ({decision.effective_risk_fraction:.2%})")
```

SUCCESS CRITERIA:
- ✅ Matches manual calculations
- ✅ Respects both risk and max-position limits
- ✅ Clear reasoning in notes

Generate the complete production-ready code now.
```

---

## PROMPT 9: SIGNAL FUSION ENGINE

**Time:** 30-45 minutes  
**File:** `backend/signals/signal_fusion_engine.py`

```markdown
You are merging technical features, options flow, and regime into one unified signal score.

CONTEXT:
- Technical: 75 features from StreamingFeatureEngine
- Flow: 5 features from WhalesFeatureBuilder
- Regime: 5 features (VIX, breadth, etc.)
- ML: Win probability from RiverOnlineEngine

YOUR TASK:
Build SignalFusionEngine that:

1. Normalizes all feature groups
2. Computes weighted composite score (0-100)
3. Applies ML confidence scaling
4. Categorizes into tiers (T1/T2/T3/none)

WEIGHTING:
- Technical: 50%
- Unusual Whales: 30%
- Regime: 20%

ML CONFIDENCE SCALING:
- <0.60: 0.7x (reduce score)
- 0.60-0.70: 0.85x
- 0.70-0.80: 1.0x (neutral)
- 0.80-0.90: 1.2x (boost)
- >0.90: 1.5x (strong boost)

TIER THRESHOLDS:
- ≥75: Tier 1 (Strong)
- ≥60: Tier 2 (Medium)
- ≥45: Tier 3 (Weak)
- <45: No Signal

CODE:

```python
from pydantic import BaseModel
from typing import Optional

class FusedSignal(BaseModel):
    symbol: str
    direction: str  # LONG/SHORT
    score: float  # 0-100
    tier: str  # T1/T2/T3/NONE
    ml_confidence: float
    components: dict  # Breakdown by source

class SignalFusionEngine:
    def __init__(
        self,
        tech_weight=0.50,
        whales_weight=0.30,
        regime_weight=0.20
    ):
        self.tech_weight = tech_weight
        self.whales_weight = whales_weight
        self.regime_weight = regime_weight
    
    def fuse(
        self,
        symbol: str,
        direction: str,
        tech_features: dict,
        flow_features: dict,
        regime_features: dict,
        ml_confidence: float
    ) -> FusedSignal:
        """Fuse all inputs into unified signal"""
        
        # Score each component (0-100)
        tech_score = self._score_technical(tech_features, direction)
        flow_score = self._score_flow(flow_features, direction)
        regime_score = self._score_regime(regime_features)
        
        # Weighted composite
        raw_score = (
            tech_score * self.tech_weight +
            flow_score * self.whales_weight +
            regime_score * self.regime_weight
        )
        
        # Apply ML confidence scaling
        ml_multiplier = self._get_ml_multiplier(ml_confidence)
        final_score = raw_score * ml_multiplier
        final_score = min(max(final_score, 0), 100)  # Clamp 0-100
        
        # Determine tier
        if final_score >= 75:
            tier = "T1"
        elif final_score >= 60:
            tier = "T2"
        elif final_score >= 45:
            tier = "T3"
        else:
            tier = "NONE"
        
        return FusedSignal(
            symbol=symbol,
            direction=direction,
            score=final_score,
            tier=tier,
            ml_confidence=ml_confidence,
            components={
                "technical": tech_score,
                "flow": flow_score,
                "regime": regime_score,
                "raw_score": raw_score,
                "ml_multiplier": ml_multiplier
            }
        )
    
    def _score_technical(self, features: dict, direction: str) -> float:
        """Score technical features 0-100"""
        score = 50  # Neutral baseline
        
        # RSI
        rsi = features.get("rsi", 50)
        if direction == "LONG":
            if rsi < 30:
                score += 20  # Oversold
            elif rsi > 70:
                score -= 20  # Overbought
        
        # Trend (SMA alignment)
        if features.get("price_above_sma20", 0) == 1:
            score += 10 if direction == "LONG" else -10
        
        # Volume surge
        if features.get("volume_surge", 0) == 1:
            score += 15
        
        return min(max(score, 0), 100)
    
    def _score_flow(self, features: dict, direction: str) -> float:
        """Score options flow 0-100"""
        score = 50
        
        # Call/Put imbalance
        imbalance = features.get("call_put_imbalance", 0)
        if direction == "LONG":
            score += imbalance * 30  # Positive = more calls
        else:
            score -= imbalance * 30
        
        # Bullish flow
        bullish_pct = features.get("bullish_flow_pct", 0.5)
        if direction == "LONG":
            score += (bullish_pct - 0.5) * 40
        
        return min(max(score, 0), 100)
    
    def _score_regime(self, features: dict) -> float:
        """Score market regime 0-100"""
        score = 50
        
        # VIX (lower is better)
        vix = features.get("vix_proxy", 15)
        if vix < 15:
            score += 20
        elif vix > 25:
            score -= 20
        
        return min(max(score, 0), 100)
    
    def _get_ml_multiplier(self, confidence: float) -> float:
        """Convert ML confidence to score multiplier"""
        if confidence < 0.60:
            return 0.7
        elif confidence < 0.70:
            return 0.85
        elif confidence < 0.80:
            return 1.0
        elif confidence < 0.90:
            return 1.2
        else:
            return 1.5
```

USAGE:
```python
engine = SignalFusionEngine()

signal = engine.fuse(
    symbol="AAPL",
    direction="LONG",
    tech_features={"rsi": 32, "price_above_sma20": 1, ...},
    flow_features={"call_put_imbalance": 0.6, ...},
    regime_features={"vix_proxy": 14.2, ...},
    ml_confidence=0.78
)

print(f"Signal: {signal.tier} - Score: {signal.score:.1f}")
```

SUCCESS CRITERIA:
- ✅ Deterministic scoring
- ✅ Handles missing features (neutral defaults)
- ✅ Lightweight (<1ms per call)

Generate the complete production-ready code now.
```

---

## PROMPT 10: ALPACA TRADING + OPERATOR APPROVAL

**Time:** 60-90 minutes  
**Files:**
- `backend/execution/approval_handler.py`
- `backend/services/alpaca_trading_service.py`
- `backend/services/position_tracker.py`

```markdown
You are implementing the complete execution stack with human-in-the-loop approval.

CONTEXT:
- NO auto-execution - operator must approve every trade
- Alpaca REST API for order submission
- Track positions internally for P&L and ML learning

YOUR TASK:
Build 3 components:

### 1. APPROVAL HANDLER

```python
from pydantic import BaseModel
from typing import Optional
import uuid

class ApprovalRequest(BaseModel):
    request_id: str
    symbol: str
    direction: str
    qty: int
    entry_price: float
    stop_price: float
    target_price: Optional[float]
    signal_score: float
    ml_confidence: float
    risk_amount: float
    created_at: datetime
    expires_at: datetime
    status: str  # PENDING/APPROVED/REJECTED/EXPIRED

class OperatorDecision(BaseModel):
    request_id: str
    action: str  # APPROVE/REJECT/MODIFY
    modified_qty: Optional[int]
    notes: str

class ApprovalHandler:
    def __init__(self, message_bus, timeout_seconds=300):
        self.message_bus = message_bus
        self.timeout_seconds = timeout_seconds
        self.pending_requests = {}  # request_id -> ApprovalRequest
    
    async def queue_approval(
        self,
        signal: FusedSignal,
        risk_decision: RiskDecision,
        size_decision: PositionSizeDecision
    ) -> ApprovalRequest:
        """Create approval request and notify operator"""
        
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            symbol=signal.symbol,
            direction=signal.direction,
            qty=size_decision.shares,
            entry_price=signal.entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            signal_score=signal.score,
            ml_confidence=signal.ml_confidence,
            risk_amount=size_decision.risk_amount,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.timeout_seconds),
            status="PENDING"
        )
        
        self.pending_requests[request.request_id] = request
        
        # Publish approval needed event
        await self.message_bus.publish("approval.needed", {
            "request": request.model_dump()
        }, priority=2)
        
        return request
    
    async def apply_operator_decision(
        self,
        decision: OperatorDecision
    ) -> dict:
        """Process operator's decision"""
        
        request = self.pending_requests.get(decision.request_id)
        if not request:
            return {"error": "Request not found"}
        
        if request.status != "PENDING":
            return {"error": f"Request already {request.status}"}
        
        # Update request
        if decision.action == "APPROVE":
            request.status = "APPROVED"
            if decision.modified_qty:
                request.qty = decision.modified_qty
            
            await self.message_bus.publish("approval.granted", {
                "request": request.model_dump(),
                "notes": decision.notes
            })
            
            return {"status": "approved", "request": request}
        
        elif decision.action == "REJECT":
            request.status = "REJECTED"
            
            await self.message_bus.publish("approval.rejected", {
                "request": request.model_dump(),
                "reason": decision.notes
            })
            
            return {"status": "rejected"}
```

### 2. ALPACA TRADING SERVICE

```python
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, BracketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

class AlpacaTradingService:
    def __init__(self, api_key: str, secret_key: str, paper=True):
        self.client = TradingClient(api_key, secret_key, paper=paper)
    
    async def submit_bracket_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        stop: float,
        target: Optional[float]
    ) -> dict:
        """Submit bracket order (entry + stop + target)"""
        
        order_side = OrderSide.BUY if side == "LONG" else OrderSide.SELL
        
        request = BracketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
            stop_loss={"stop_price": stop},
            take_profit={"limit_price": target} if target else None
        )
        
        order = self.client.submit_order(request)
        
        return {
            "order_id": order.id,
            "symbol": order.symbol,
            "qty": order.qty,
            "status": order.status
        }
    
    async def get_open_positions(self) -> List[dict]:
        """Get all open positions"""
        positions = self.client.get_all_positions()
        return [p.model_dump() for p in positions]
    
    async def get_account(self) -> dict:
        """Get account info"""
        account = self.client.get_account()
        return account.model_dump()
```

### 3. POSITION TRACKER

```python
class PositionTracker:
    def __init__(self, message_bus):
        self.message_bus = message_bus
        self.positions = {}  # symbol -> position_data
    
    async def on_order_filled(self, data: dict):
        """Handle order fill event"""
        symbol = data["symbol"]
        
        self.positions[symbol] = {
            "entry_price": data["filled_avg_price"],
            "qty": data["qty"],
            "side": data["side"],
            "entry_time": datetime.now(),
            "features": data.get("features", {})
        }
        
        await self.message_bus.publish("position.opened", {
            "symbol": symbol,
            "entry": data["filled_avg_price"]
        })
    
    async def on_position_closed(self, symbol: str, exit_price: float):
        """Calculate P&L and trigger ML learning"""
        
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        # Calculate P&L
        if pos["side"] == "BUY":
            pnl = (exit_price - pos["entry_price"]) * pos["qty"]
        else:
            pnl = (pos["entry_price"] - exit_price) * pos["qty"]
        
        outcome = 1 if pnl > 0 else 0
        
        # Publish position closed event
        await self.message_bus.publish("position.closed", {
            "symbol": symbol,
            "features": pos["features"],
            "outcome": outcome,
            "pnl": pnl,
            "hold_time": (datetime.now() - pos["entry_time"]).total_seconds()
        })
        
        del self.positions[symbol]
```

WORKFLOW:
```
1. Signal Generated → Risk Validated
2. Create Approval Request → Notify Operator (Telegram/Dashboard)
3. Operator Reviews → Approves/Modifies/Rejects
4. If Approved: Submit to Alpaca
5. Order Filled → Track Position
6. Position Closes → Calculate P&L → ML Learns
```

SUCCESS CRITERIA:
- ✅ No trade reaches Alpaca without approval
- ✅ Complete audit trail
- ✅ P&L tracked accurately

Generate all 3 production-ready files now.
```

---

## PROMPT 11: PARALLEL BAR PROCESSOR

**Time:** 30-45 minutes  
**File:** `backend/core/parallel_processor.py`

```markdown
You are building the orchestrator that processes 1,600 symbols in parallel within 1 second.

CONTEXT:
- Bars arrive from AlpacaStreamService (potentially batched)
- For each bar: update features → predict ML → fuse signal → risk validate → queue approval
- Use ThreadPoolExecutor for parallel execution

YOUR TASK:
Implement ParallelBarProcessor:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import logging

logger = logging.getLogger(__name__)

class ParallelBarProcessor:
    def __init__(
        self,
        feature_engine,
        ml_engine,
        fusion_engine,
        risk_validator,
        position_sizer,
        approval_handler,
        whales_features,
        max_workers=20
    ):
        self.feature_engine = feature_engine
        self.ml_engine = ml_engine
        self.fusion_engine = fusion_engine
        self.risk_validator = risk_validator
        self.position_sizer = position_sizer
        self.approval_handler = approval_handler
        self.whales_features = whales_features
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_bars(self, bars: List[dict]) -> None:
        """
        Process list of bars in parallel.
        
        Args:
            bars: List of bar dicts from AlpacaStreamService
        """
        start_time = datetime.now()
        
        # Submit all bars to thread pool
        futures = {
            self.executor.submit(self._process_single_bar, bar): bar
            for bar in bars
        }
        
        # Wait for completion
        results = []
        errors = []
        
        for future in as_completed(futures):
            bar = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error processing {bar['symbol']}: {e}")
                errors.append({"symbol": bar["symbol"], "error": str(e)})
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Processed {len(bars)} bars in {elapsed_ms:.0f}ms "
            f"({len(results)} signals, {len(errors)} errors)"
        )
    
    def _process_single_bar(self, bar: dict) -> Optional[dict]:
        """
        Process one bar through full pipeline.
        
        Returns:
            Approval request if signal generated, else None
        """
        symbol = bar["symbol"]
        
        try:
            # Step 1: Update features
            features = self.feature_engine.update_bar(symbol, bar)
            if not features:
                return None  # Insufficient data
            
            # Step 2: Get ML prediction
            ml_confidence = self.ml_engine.predict_proba(symbol, features)
            
            # Step 3: Get flow features
            flow_features = self.whales_features.get_features(symbol)
            
            # Step 4: Get regime features (simplified here)
            regime_features = {"vix_proxy": features.get("atr_pct", 15)}
            
            # Step 5: Fuse signal
            # Determine direction based on technical indicators
            direction = self._determine_direction(features)
            if not direction:
                return None
            
            signal = self.fusion_engine.fuse(
                symbol=symbol,
                direction=direction,
                tech_features=features,
                flow_features=flow_features,
                regime_features=regime_features,
                ml_confidence=ml_confidence
            )
            
            # Only proceed if strong signal
            if signal.tier == "NONE":
                return None
            
            # Step 6: Risk validation
            # (Need account and positions - get from cache/service)
            account = self._get_account_cached()
            positions = self._get_positions_cached()
            
            risk_decision = self.risk_validator.validate(
                signal.model_dump(),
                account,
                positions
            )
            
            if not risk_decision.approved:
                logger.debug(f"{symbol}: Risk rejected - {risk_decision.reasons}")
                return None
            
            # Step 7: Position sizing
            size_decision = self.position_sizer.size_position(
                equity=account["equity"],
                entry=bar["close"],
                stop=bar["close"] - features["atr"],  # ATR-based stop
                vix_value=regime_features["vix_proxy"]
            )
            
            # Step 8: Queue for approval
            # (This is async, but we're in sync context - use asyncio.run_coroutine_threadsafe)
            # For simplicity here, just return the data
            return {
                "symbol": symbol,
                "signal": signal,
                "risk_decision": risk_decision,
                "size_decision": size_decision
            }
            
        except Exception as e:
            logger.error(f"Error in pipeline for {symbol}: {e}")
            return None
    
    def _determine_direction(self, features: dict) -> Optional[str]:
        """Simple direction logic based on RSI and trend"""
        rsi = features.get("rsi", 50)
        above_sma = features.get("price_above_sma20", 0)
        
        if rsi < 35 and above_sma == 1:
            return "LONG"
        elif rsi > 65 and above_sma == 0:
            return "SHORT"
        
        return None
    
    def _get_account_cached(self) -> dict:
        """Get cached account data (implement caching)"""
        return {"equity": 100000, "daily_pnl": 500}
    
    def _get_positions_cached(self) -> List[dict]:
        """Get cached positions (implement caching)"""
        return []
    
    def shutdown(self):
        """Gracefully shutdown thread pool"""
        self.executor.shutdown(wait=True)
```

THREAD SAFETY:
- Feature engine: Thread-safe (per-symbol state)
- ML engine: Thread-safe (River models are thread-safe)
- Others: Stateless or use locks if needed

SUCCESS CRITERIA:
- ✅ 1600 bars in <1 second
- ✅ Failures on one symbol don't block others
- ✅ Clean shutdown

Generate the complete production-ready code now.
```

---

## PROMPT 12: MONITORING & ALERTS

**Time:** 30-45 minutes  
**Files:**
- `backend/monitoring/alert_manager.py`
- `backend/monitoring/audit_logger.py`

```markdown
You are implementing system monitoring, Telegram alerts, and audit logging for compliance.

YOUR TASK:
Build 2 components:

### 1. ALERT MANAGER (Telegram)

```python
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class TelegramTransport:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_message(self, text: str):
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": text}
            )

class AlertManager:
    def __init__(self, message_bus, transport: TelegramTransport):
        self.message_bus = message_bus
        self.transport = transport
    
    async def start(self):
        """Subscribe to alert-worthy events"""
        await self.message_bus.subscribe("approval.needed", self.on_approval_needed)
        await self.message_bus.subscribe("approval.granted", self.on_approval_granted)
        await self.message_bus.subscribe("approval.rejected", self.on_approval_rejected)
        await self.message_bus.subscribe("risk.breach", self.on_risk_breach)
        await self.message_bus.subscribe("model.drift_detected", self.on_drift_detected)
        await self.message_bus.subscribe("order.filled", self.on_order_filled)
        await self.message_bus.subscribe("position.closed", self.on_position_closed)
    
    async def on_approval_needed(self, data: dict):
        request = data["request"]
        
        message = f"""
🔔 APPROVAL NEEDED

Symbol: {request['symbol']}
Direction: {request['direction']}
Qty: {request['qty']} shares
Entry: ${request['entry_price']:.2f}
Stop: ${request['stop_price']:.2f}

Signal Score: {request['signal_score']:.1f}
ML Confidence: {request['ml_confidence']:.1%}
Risk: ${request['risk_amount']:.0f}

Expires in 5 minutes
"""
        
        await self.transport.send_message(message)
    
    async def on_approval_granted(self, data: dict):
        request = data["request"]
        
        message = f"""
✅ TRADE APPROVED

{request['symbol']} {request['direction']}
{request['qty']} shares @ ${request['entry_price']:.2f}

Notes: {data.get('notes', 'None')}
"""
        
        await self.transport.send_message(message)
    
    async def on_risk_breach(self, data: dict):
        message = f"""
⚠️ RISK BREACH

{data['description']}
Action: {data['action']}
"""
        
        await self.transport.send_message(message)
    
    async def on_drift_detected(self, data: dict):
        report = data["report"]
        
        message = f"""
🚨 MODEL DRIFT DETECTED

River AUC: {report['river_auc']:.3f}
XGBoost AUC: {report['xgb_auc']:.3f}
Drift: {report['drift_magnitude']:.1%}

Review model immediately!
"""
        
        await self.transport.send_message(message)
```

### 2. AUDIT LOGGER

```python
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

class AuditLogger:
    def __init__(self, message_bus, log_dir="logs/audit"):
        self.message_bus = message_bus
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_file = None
        self.correlation_ids = {}  # Track request flow
    
    async def start(self):
        """Subscribe to all critical events"""
        events = [
            "signal.generated",
            "signal.validated",
            "signal.rejected",
            "approval.needed",
            "approval.granted",
            "approval.rejected",
            "order.submitted",
            "order.filled",
            "order.rejected",
            "position.opened",
            "position.closed",
            "model.updated",
            "risk.breach"
        ]
        
        for event in events:
            await self.message_bus.subscribe(event, self.log_event)
    
    async def log_event(self, data: dict):
        """Write event to audit log"""
        
        # Generate correlation ID for request tracking
        correlation_id = data.get("correlation_id") or str(uuid.uuid4())
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": data.get("event_type", "unknown"),
            "correlation_id": correlation_id,
            "payload": data
        }
        
        # Write to JSONL file (one JSON object per line)
        log_file = self._get_log_file()
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    
    def _get_log_file(self) -> Path:
        """Get current log file (rotate daily)"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{today}.jsonl"
```

ENVIRONMENT:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

SUCCESS CRITERIA:
- ✅ No critical event missed
- ✅ Alerts delivered within 1 second
- ✅ Audit logs are append-only and machine-readable

Generate both production-ready files now.
```

---

## ✅ COMPLETION CHECKLIST

After generating all 12 modules:

- [ ] All files created and saved
- [ ] Dependencies added to requirements.txt
- [ ] Environment variables configured in .env
- [ ] Each module tested independently
- [ ] Integration test: bar → features → ML → signal → risk → approval
- [ ] MessageBus connecting all components
- [ ] Telegram alerts working
- [ ] Audit logs capturing all events

---

## 🚀 DEPLOYMENT STEPS

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Start system:**
```bash
python main.py
```

4. **Monitor Telegram for alerts**

5. **Paper trade for 1 week before live**

---

**Total Build Time:** 10-14 hours  
**Result:** Production-ready ML trading system with full operator control  
**Transform:** 35% → 100% complete 🎯
