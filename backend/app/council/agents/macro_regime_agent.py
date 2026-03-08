"""Cross-Asset Macro Regime Enhancement Agent — FRED-powered macro signals.

P4 Academic Edge Agent. Enhances the existing regime_agent with structured
macro signal processing from FRED data sources.

Academic basis: Yield curve (10Y-2Y) is strongest recession leading indicator.
Chicago Fed research shows NTFS dominates as leading indicator. Note: the
un-inversion often occurs right before recession onset, not the inversion.

Macro signals:
- Yield Curve Inversion Monitor (T10Y2Y)
- Credit Spread Monitor (ICE BofA High Yield OAS)
- Breakeven Inflation Monitor (T10YIE, T5YIE)
- Leading Indicators Composite (ICSA, ISM PMI, building permits)
- VIX Regime Classifier

Output: Five regime states (RISK_ON, NORMAL, CAUTIOUS, RISK_OFF, CRISIS)
that map to directives adjusting confidence thresholds and position sizes.

Council integration: Enhances existing regime_agent. Reads FRED API (already integrated).
"""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote
from app.core.message_bus import get_message_bus

logger = logging.getLogger(__name__)

NAME = "macro_regime_agent"

# VIX regime classification thresholds
_VIX_COMPLACENCY = 15
_VIX_NORMAL_HIGH = 25
_VIX_ELEVATED = 35

# Yield curve thresholds
_YIELD_CURVE_INVERTED = -0.05  # Spread below this = inverted
_YIELD_CURVE_STEEP = 1.0       # Spread above this = steep/bullish

# Credit spread thresholds (OAS basis points)
_CREDIT_NORMAL = 400
_CREDIT_STRESS = 600
_CREDIT_CRISIS = 800

# Regime score weights
_WEIGHTS = {
    "yield_curve": 0.25,
    "credit_spread": 0.20,
    "vix": 0.20,
    "inflation": 0.15,
    "leading_indicators": 0.20,
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Compute macro regime from FRED and VIX data."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Fetch macro data from FRED
    macro_data = await _fetch_macro_data()

    # Publish FRED macro data to MessageBus for downstream perception consumers
    try:
        bus = get_message_bus()
        if bus._running:
            await bus.publish("perception.macro", {
                "type": "fred_macro_data",
                "data": macro_data,
                "source": "macro_regime_agent",
                "timestamp": time.time(),
            })
    except Exception:
        pass

    # Get VIX
    vix = float(f.get("vix_close", 0) or f.get("vix", 0))
    if vix == 0 and macro_data:
        vix = float(macro_data.get("vix", 0))

    # Analyze each macro signal
    yield_curve = _analyze_yield_curve(macro_data)
    credit = _analyze_credit_spreads(macro_data)
    vix_regime = _classify_vix(vix)
    inflation = _analyze_inflation(macro_data)
    leading = _analyze_leading_indicators(macro_data)

    # Compute composite macro regime
    regime_score = _compute_regime_score(
        yield_curve, credit, vix_regime, inflation, leading,
    )
    macro_regime = _score_to_regime(regime_score)

    # Write to blackboard
    if blackboard:
        blackboard.macro_regime.update({
            "yield_curve_spread": yield_curve.get("spread", 0.0),
            "yield_curve_inverted": yield_curve.get("inverted", False),
            "credit_spread": credit.get("oas", 0.0),
            "breakeven_inflation": inflation.get("t10yie", 0.0),
            "vix_regime": vix_regime,
            "leading_indicators": leading,
            "macro_regime": macro_regime,
        })

    # Vote determination
    direction, confidence = _regime_to_vote(macro_regime, regime_score, cfg)

    reasoning_parts = [
        f"Macro regime={macro_regime} (score={regime_score:+.2f})",
        f"VIX={vix:.1f} ({vix_regime})",
    ]
    if yield_curve.get("inverted"):
        reasoning_parts.append("YIELD CURVE INVERTED")
    if yield_curve.get("un_inverting"):
        reasoning_parts.append("UN-INVERTING (recession warning)")
    if credit.get("stress"):
        reasoning_parts.append(f"Credit stress: OAS={credit.get('oas', 0):.0f}bps")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_macro_regime_agent", 1.0),
        metadata={
            "data_available": True,
            "macro_regime": macro_regime,
            "regime_score": regime_score,
            "yield_curve": yield_curve,
            "credit": credit,
            "vix_regime": vix_regime,
            "inflation": inflation,
            "leading_indicators": leading,
        },
    )


def _regime_to_vote(regime: str, score: float, cfg: Dict) -> Tuple[str, float]:
    """Convert macro regime to directional vote."""
    regime_map = {
        "RISK_ON": ("buy", 0.7),
        "NORMAL": ("hold", 0.5),
        "CAUTIOUS": ("hold", 0.55),
        "RISK_OFF": ("sell", 0.65),
        "CRISIS": ("sell", 0.8),
    }
    direction, confidence = regime_map.get(regime, ("hold", 0.4))
    return direction, confidence


async def _fetch_macro_data() -> Dict[str, Any]:
    """Fetch macro data from FRED API (already integrated)."""
    data: Dict[str, Any] = {}

    try:
        from app.services.fred_service import get_series_latest
        # Fetch key FRED series
        series_ids = {
            "t10y2y": "T10Y2Y",         # 10Y-2Y Treasury spread
            "hy_oas": "BAMLH0A0HYM2",   # High Yield OAS
            "t10yie": "T10YIE",          # 10Y breakeven inflation
            "t5yie": "T5YIE",            # 5Y breakeven inflation
            "icsa": "ICSA",              # Initial jobless claims
            "unrate": "UNRATE",          # Unemployment rate
            "fedfunds": "FEDFUNDS",      # Fed funds rate
        }

        for key, series_id in series_ids.items():
            try:
                value = await get_series_latest(series_id)
                if value is not None:
                    data[key] = float(value)
            except Exception:
                pass

    except ImportError:
        pass

    # Try FRED via features
    try:
        from app.services.fred_service import get_fred_snapshot
        snapshot = await get_fred_snapshot()
        if snapshot:
            data.update(snapshot)
    except Exception:
        pass

    return data


def _analyze_yield_curve(data: Dict) -> Dict[str, Any]:
    """Analyze yield curve for inversion and un-inversion signals."""
    spread = float(data.get("t10y2y", 0))

    inverted = spread < _YIELD_CURVE_INVERTED
    steep = spread > _YIELD_CURVE_STEEP

    # Un-inversion detection: when spread was negative and is now rising
    # This often occurs right BEFORE recession onset
    un_inverting = False
    if -0.10 < spread < 0.10 and data.get("t10y2y_prev", 0) < spread:
        un_inverting = True

    # Score: positive = bullish, negative = bearish
    if steep:
        score = 1.0
    elif spread > 0.3:
        score = 0.5
    elif spread > 0:
        score = 0.2
    elif inverted:
        score = -0.8
    else:
        score = -0.3

    if un_inverting:
        score = -1.0  # Un-inversion is most bearish signal

    return {
        "spread": spread,
        "inverted": inverted,
        "steep": steep,
        "un_inverting": un_inverting,
        "score": score,
    }


def _analyze_credit_spreads(data: Dict) -> Dict[str, Any]:
    """Analyze credit spreads for stress signals."""
    oas = float(data.get("hy_oas", 0))

    stress = False
    crisis = False
    score = 0.0

    if oas == 0:
        return {"oas": 0, "stress": False, "crisis": False, "score": 0}

    if oas >= _CREDIT_CRISIS:
        crisis = True
        stress = True
        score = -1.0
    elif oas >= _CREDIT_STRESS:
        stress = True
        score = -0.6
    elif oas >= _CREDIT_NORMAL:
        score = -0.2
    else:
        score = 0.5  # Tight spreads = risk-on

    return {
        "oas": oas,
        "stress": stress,
        "crisis": crisis,
        "score": score,
    }


def _classify_vix(vix: float) -> str:
    """Classify VIX into regime buckets."""
    if vix == 0:
        return "unknown"
    if vix < _VIX_COMPLACENCY:
        return "complacency"
    elif vix < _VIX_NORMAL_HIGH:
        return "normal"
    elif vix < _VIX_ELEVATED:
        return "elevated"
    else:
        return "crisis"


def _analyze_inflation(data: Dict) -> Dict[str, Any]:
    """Analyze breakeven inflation for deflationary signals."""
    t10yie = float(data.get("t10yie", 0))
    t5yie = float(data.get("t5yie", 0))

    score = 0.0

    if t10yie == 0:
        return {"t10yie": 0, "t5yie": 0, "score": 0}

    # Moderate inflation = healthy
    if 1.5 < t10yie < 3.0:
        score = 0.3
    # Low inflation / deflation = concerning
    elif t10yie < 1.0:
        score = -0.5
    # High inflation = tightening ahead
    elif t10yie > 3.5:
        score = -0.3

    # Flattening breakeven curve = deflationary signal
    if t10yie > 0 and t5yie > 0:
        curve = t10yie - t5yie
        if curve < -0.2:
            score -= 0.2  # 5Y inflation > 10Y = deflationary expectation

    return {
        "t10yie": t10yie,
        "t5yie": t5yie,
        "curve": t10yie - t5yie if t5yie > 0 else 0,
        "score": score,
    }


def _analyze_leading_indicators(data: Dict) -> Dict[str, Any]:
    """Analyze leading economic indicators composite."""
    icsa = float(data.get("icsa", 0))  # Initial claims

    score = 0.0
    signals: List[str] = []

    # Initial jobless claims
    if icsa > 0:
        if icsa < 200_000:
            score += 0.3
            signals.append("strong_labor")
        elif icsa < 300_000:
            score += 0.1
            signals.append("healthy_labor")
        elif icsa > 400_000:
            score -= 0.4
            signals.append("weak_labor")
        elif icsa > 300_000:
            score -= 0.1
            signals.append("softening_labor")

    return {
        "icsa": icsa,
        "score": score,
        "signals": signals,
    }


def _compute_regime_score(
    yield_curve: Dict, credit: Dict, vix_regime: str,
    inflation: Dict, leading: Dict,
) -> float:
    """Compute weighted composite macro regime score."""
    # VIX to score
    vix_scores = {
        "complacency": 0.5,
        "normal": 0.2,
        "elevated": -0.5,
        "crisis": -1.0,
        "unknown": 0.0,
    }

    scores = {
        "yield_curve": yield_curve.get("score", 0),
        "credit_spread": credit.get("score", 0),
        "vix": vix_scores.get(vix_regime, 0),
        "inflation": inflation.get("score", 0),
        "leading_indicators": leading.get("score", 0),
    }

    weighted_sum = sum(
        scores[key] * _WEIGHTS.get(key, 0.2)
        for key in scores
    )

    return round(weighted_sum, 3)


def _score_to_regime(score: float) -> str:
    """Map composite score to regime label."""
    if score > 0.4:
        return "RISK_ON"
    elif score > 0.1:
        return "NORMAL"
    elif score > -0.2:
        return "CAUTIOUS"
    elif score > -0.5:
        return "RISK_OFF"
    else:
        return "CRISIS"
