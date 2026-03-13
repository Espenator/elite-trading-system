"""Flow Perception Agent — options flow analysis."""
import logging
import time
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote
from app.services.unusual_whales_service import get_unusual_whales_service

logger = logging.getLogger(__name__)

NAME = "flow_perception"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Analyze options flow data if available."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)

    call_vol = f.get("flow_call_volume", 0)
    put_vol = f.get("flow_put_volume", 0)
    net_premium = f.get("flow_net_premium", 0)
    pcr = f.get("flow_pcr", 0)
    intel_meta = {"data_available": True, "pcr": pcr}

    # Cache-warming path: use fresh UW bus cache if direct flow features are missing.
    if call_vol == 0 and put_vol == 0:
        uw_svc = get_unusual_whales_service()
        cached = getattr(uw_svc, "_last_flow_cache", []) or []
        cache_age = time.time() - float(getattr(uw_svc, "_last_flow_ts", 0) or 0)
        if cached and cache_age < 60:
            call_count = 0
            put_count = 0
            net = 0.0
            for alert in cached:
                if not isinstance(alert, dict):
                    continue
                put_call = str(alert.get("put_call", "")).lower()
                premium = float(alert.get("premium", 0) or alert.get("total_premium", 0) or 0)
                if put_call == "call":
                    call_count += 1
                    net += premium
                elif put_call == "put":
                    put_count += 1
                    net -= premium
            if call_count or put_count:
                call_vol = call_count
                put_vol = put_count
                net_premium = net
                pcr = put_vol / max(call_vol, 1)
                intel_meta.update({"cache_used": True, "cache_age_s": round(cache_age, 2), "pcr": pcr})

    # If no flow data, abstain with low confidence
    if call_vol == 0 and put_vol == 0:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No options flow data available",
            weight=cfg["weight_flow_perception"],
            metadata={"data_available": False, "cache_used": False},
        )

    # PCR analysis
    direction = "hold"
    confidence = 0.4

    if pcr > 0 and pcr < cfg["pcr_bullish_threshold"]:
        direction = "buy"
        confidence = 0.6
    elif pcr > cfg["pcr_bearish_threshold"]:
        direction = "sell"
        confidence = 0.6
    elif pcr > cfg["pcr_mild_bearish_threshold"]:
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

    # Enrich with institutional flow intelligence if available
    blackboard = context.get("blackboard")
    if blackboard:
        intel = blackboard.metadata.get("intelligence", {})
        inst_flow = intel.get("cortex_institutional", {})
        if isinstance(inst_flow, dict) and inst_flow.get("data"):
            flow_data = inst_flow["data"]
            inst_sentiment = flow_data.get("institutional_sentiment")
            if inst_sentiment == "accumulating" and direction != "sell":
                confidence = min(0.85, confidence + 0.05)
                reasoning += f" | Institutional: {inst_sentiment}"
            elif inst_sentiment == "distributing" and direction != "buy":
                confidence = min(0.85, confidence + 0.05)
                reasoning += f" | Institutional: {inst_sentiment}"
            intel_meta["institutional_sentiment"] = inst_sentiment

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg["weight_flow_perception"],
        metadata=intel_meta,
    )
