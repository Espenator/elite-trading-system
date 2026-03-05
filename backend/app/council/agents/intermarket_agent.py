"""Intermarket Agent -- cross-asset correlation and risk regime detection.

Inspired by smarttrading.club SPY-UVXY, SPY-IEF, SPY-IWM correlations
and sector ETF analysis. Detects risk-on/risk-off regimes via
intermarket divergences and computes beta-adjusted signals.
"""

import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "intermarket"
WEIGHT = 1.0


async def evaluate(
    symbol: str,
    timeframe: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
) -> AgentVote:
    """Evaluate intermarket correlations and risk regime."""
    f = features.get("features", features)

    # Cross-asset correlation features
    spy_uvxy_corr = float(f.get("spy_uvxy_correlation", -0.85))
    spy_ief_corr = float(f.get("spy_ief_correlation", -0.3))
    spy_iwm_corr = float(f.get("spy_iwm_correlation", 0.9))
    ticker_spy_corr = float(f.get("ticker_spy_correlation", 0.7))
    beta = float(f.get("beta", 1.0) or 1.0)

    # VIX data
    vix_level = float(f.get("vix_level", 0) or f.get("vix", 0))
    vix_change = float(f.get("vix_change_pct", 0))

    # Sector breadth
    sector_bullish_pct = float(f.get("sector_bullish_pct", 50))

    score = 0
    reasons = []

    # SPY-UVXY divergence (normally deeply negative; less negative = fear)
    if spy_uvxy_corr > -0.5:
        score -= 2
        reasons.append(f"SPY-UVXY divergence r={spy_uvxy_corr:.2f} (fear)")
    elif spy_uvxy_corr < -0.8:
        score += 1
        reasons.append(f"SPY-UVXY normal r={spy_uvxy_corr:.2f}")

    # SPY-IEF (flight to safety when strongly negative)
    if spy_ief_corr < -0.5:
        score -= 1
        reasons.append(f"Flight to safety SPY-IEF r={spy_ief_corr:.2f}")

    # SPY-IWM (breadth weakness when decorrelating)
    if spy_iwm_corr < 0.7:
        score -= 1
        reasons.append(f"Small-cap weakness SPY-IWM r={spy_iwm_corr:.2f}")
    elif spy_iwm_corr > 0.9:
        score += 1
        reasons.append(f"Broad participation SPY-IWM r={spy_iwm_corr:.2f}")

    # VIX regime
    if vix_level > 30:
        score -= 2
        reasons.append(f"VIX={vix_level:.0f} (high fear)")
    elif vix_level > 20:
        score -= 1
        reasons.append(f"VIX={vix_level:.0f} (elevated)")
    elif 0 < vix_level <= 15:
        score += 1
        reasons.append(f"VIX={vix_level:.0f} (complacent)")

    # Sector breadth
    if sector_bullish_pct > 70:
        score += 1
        reasons.append(f"Sector breadth={sector_bullish_pct:.0f}% bullish")
    elif sector_bullish_pct < 30:
        score -= 1
        reasons.append(f"Sector breadth={sector_bullish_pct:.0f}% bearish")

    # Beta adjustment: high-beta stocks amplify regime signal
    if abs(score) >= 2 and beta > 1.3:
        if score > 0:
            score += 1
        else:
            score -= 1
        reasons.append(f"High beta={beta:.1f} amplifies signal")

    # Determine risk regime
    if score >= 3:
        regime = "risk-on"
    elif score <= -3:
        regime = "risk-off"
    else:
        regime = "cautious"

    if score >= 3:
        direction = "buy"
        confidence = min(0.8, 0.4 + score * 0.07)
    elif score <= -3:
        direction = "sell"
        confidence = min(0.8, 0.4 + abs(score) * 0.07)
    elif score >= 1:
        direction = "buy"
        confidence = 0.3 + score * 0.05
    elif score <= -1:
        direction = "sell"
        confidence = 0.3 + abs(score) * 0.05
    else:
        direction = "hold"
        confidence = 0.3

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.85, confidence), 2),
        reasoning="; ".join(reasons[:5]),
        weight=WEIGHT,
        metadata={
            "regime": regime,
            "beta": round(beta, 2),
            "spy_uvxy_corr": round(spy_uvxy_corr, 3),
            "spy_ief_corr": round(spy_ief_corr, 3),
            "spy_iwm_corr": round(spy_iwm_corr, 3),
            "vix_level": round(vix_level, 1),
            "sector_bullish_pct": round(sector_bullish_pct, 1),
            "score": score,
        },
    )
