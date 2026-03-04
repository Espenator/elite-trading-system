"""Regime Agent — market regime alignment check."""
import logging
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "regime"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Check market regime and align trading direction."""
    cfg = get_agent_thresholds()
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

    # Enrich with macro and fear/greed intelligence if available
    meta = {"regime": regime, "regime_confidence": regime_confidence}
    blackboard = context.get("blackboard")
    if blackboard:
        intel = blackboard.metadata.get("intelligence", {})
        fg = intel.get("cortex_fear_greed", {})
        if isinstance(fg, dict) and fg.get("data"):
            fg_data = fg["data"]
            fg_value = fg_data.get("fear_greed_value")
            vix_trend = fg_data.get("vix_trend")
            if fg_value is not None:
                reasoning += f" | F&G={fg_value}"
                meta["fear_greed"] = fg_value
                # Extreme fear/greed can shift confidence
                if fg_value < 20 and direction == "sell":
                    confidence = max(0.3, confidence - 0.05)  # Contrarian: extreme fear may bottom
                    reasoning += " (contrarian caution)"
                elif fg_value > 80 and direction == "buy":
                    confidence = max(0.3, confidence - 0.05)  # Contrarian: extreme greed may top
                    reasoning += " (contrarian caution)"
            if vix_trend:
                meta["vix_trend"] = vix_trend

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(min(0.9, confidence), 2),
        reasoning=reasoning,
        weight=cfg["weight_regime"],
        metadata=meta,
    )
