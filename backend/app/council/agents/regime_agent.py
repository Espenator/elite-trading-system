"""Regime Agent — market regime alignment check."""
import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "regime"
WEIGHT = 1.2  # Higher weight — regime is critical


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Check market regime and align trading direction."""
    f = features.get("features", features)

    regime = str(f.get("regime", "unknown")).lower()
    regime_confidence = float(f.get("regime_confidence", 0))

    # Try to get regime from dedicated service
    if regime == "unknown":
        try:
            from app.services.regime_service import get_current_regime
            r = get_current_regime()
            if r:
                regime = str(r.get("regime", "unknown")).lower()
                regime_confidence = float(r.get("confidence", 0))
        except Exception:
            pass

    # Regime-based direction
    direction = "hold"
    confidence = 0.3

    if regime in ("bullish", "bull", "trending_up", "risk_on"):
        direction = "buy"
        confidence = 0.5 + regime_confidence * 0.3
    elif regime in ("bearish", "bear", "trending_down", "risk_off"):
        direction = "sell"
        confidence = 0.5 + regime_confidence * 0.3
    elif regime in ("choppy", "range", "sideways", "volatile"):
        direction = "hold"
        confidence = 0.5
    elif regime == "unknown":
        direction = "hold"
        confidence = 0.2

    reasoning = f"Regime={regime} (confidence={regime_confidence:.2f})"

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.9, confidence), 2),
        reasoning=reasoning,
        weight=WEIGHT,
        metadata={"regime": regime, "regime_confidence": regime_confidence},
    )
