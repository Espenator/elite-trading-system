"""Execution Agent — broker readiness and shadow mode check with VETO power."""
import logging
import os
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "execution"
WEIGHT = 1.3


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Check broker readiness, trading mode, and liquidity.

    Can VETO if:
    - Trading mode is shadow/paper and auto-execute disabled
    - Broker API is unreachable
    - Insufficient liquidity
    """
    reasons = []
    veto = False
    veto_reason = ""

    # Check trading mode
    auto_execute = os.getenv("AUTO_EXECUTE_TRADES", "false").lower() == "true"
    trading_mode = os.getenv("TRADING_MODE", "paper").lower()

    if not auto_execute:
        reasons.append("Shadow mode (AUTO_EXECUTE_TRADES=false)")
    else:
        reasons.append("Auto-execute ENABLED")

    if trading_mode == "paper":
        reasons.append("Paper trading mode")
    elif trading_mode == "live":
        reasons.append("LIVE trading mode")

    # Check broker connectivity
    try:
        from app.services.alpaca_service import get_alpaca_service
        svc = get_alpaca_service()
        if svc:
            reasons.append("Alpaca API reachable")
        else:
            reasons.append("Alpaca service not initialized")
    except Exception:
        reasons.append("Alpaca API not available")

    # Check volume/liquidity from features
    f = features.get("features", features)
    last_volume = f.get("last_volume", 0) or f.get("volume", 0)
    if last_volume > 0 and last_volume < 50_000:
        veto = True
        veto_reason = f"Insufficient liquidity (volume={last_volume:,.0f} < 50k)"
        reasons.append(f"LOW VOLUME: {last_volume:,.0f}")

    # Execution readiness
    execution_ready = auto_execute and not veto

    if veto:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.9,
            reasoning=f"VETO: {veto_reason}. " + "; ".join(reasons),
            veto=True,
            veto_reason=veto_reason,
            weight=WEIGHT,
            metadata={"execution_ready": False, "trading_mode": trading_mode},
        )

    return AgentVote(
        agent_name=NAME,
        direction="hold",  # Execution agent doesn't decide direction
        confidence=0.5,
        reasoning="Execution checks passed. " + "; ".join(reasons),
        weight=WEIGHT,
        metadata={"execution_ready": execution_ready, "trading_mode": trading_mode},
    )
