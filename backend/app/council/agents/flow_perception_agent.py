"""Flow Perception Agent — options flow analysis."""
import logging
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "flow_perception"
WEIGHT = 0.8


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze options flow data if available."""
    f = features.get("features", features)

    call_vol = f.get("flow_call_volume", 0)
    put_vol = f.get("flow_put_volume", 0)
    net_premium = f.get("flow_net_premium", 0)
    pcr = f.get("flow_pcr", 0)

    # If no flow data, abstain with low confidence
    if call_vol == 0 and put_vol == 0:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No options flow data available",
            weight=WEIGHT,
            metadata={"data_available": False},
        )

    # PCR analysis
    direction = "hold"
    confidence = 0.4

    if pcr > 0 and pcr < 0.7:
        direction = "buy"
        confidence = 0.6
    elif pcr > 1.3:
        direction = "sell"
        confidence = 0.6
    elif pcr > 1.0:
        direction = "sell"
        confidence = 0.5

    # Net premium confirms
    if net_premium > 0 and direction == "buy":
        confidence = min(0.8, confidence + 0.1)
    elif net_premium < 0 and direction == "sell":
        confidence = min(0.8, confidence + 0.1)

    reasoning = (
        f"PCR={pcr:.2f}, Net premium=${net_premium:,.0f}, "
        f"Call vol={call_vol:,.0f}, Put vol={put_vol:,.0f}"
    )

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=WEIGHT,
        metadata={"data_available": True, "pcr": pcr},
    )
