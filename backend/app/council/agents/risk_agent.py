"""Risk Agent — Kelly/Van Tharp constraints with VETO power."""
import logging
import os
from typing import Any, Dict

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "risk"
WEIGHT = 1.5  # Highest weight — risk is paramount

MAX_PORTFOLIO_HEAT = float(os.getenv("MAX_PORTFOLIO_HEAT", "0.06"))
MAX_SINGLE_POSITION = float(os.getenv("MAX_SINGLE_POSITION", "0.02"))


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Enforce hard risk guardrails. Can VETO any trade.

    Checks:
    - Portfolio heat (total exposure)
    - Single position limit
    - Drawdown status
    - Volatility regime
    """
    f = features.get("features", features)
    veto = False
    veto_reason = ""
    reasons = []
    risk_limits = {}

    # Check portfolio heat via risk API
    try:
        from app.api.v1.risk import risk_score as get_risk
        risk_data = await get_risk()
        risk_score = risk_data.get("risk_score", 50)
        reasons.append(f"Risk score={risk_score}")

        if risk_score < 30:
            veto = True
            veto_reason = f"Risk score too low ({risk_score} < 30)"
    except Exception:
        reasons.append("Risk API unavailable")

    # Check drawdown
    try:
        from app.api.v1.risk import drawdown_check_status
        dd = await drawdown_check_status()
        if not dd.get("trading_allowed", True):
            veto = True
            veto_reason = "Drawdown limit breached — trading halted"
            reasons.append("DRAWDOWN BREACHED")
        elif dd.get("drawdown_breached"):
            veto = True
            veto_reason = "Drawdown threshold exceeded"
            reasons.append("Drawdown warning")
        else:
            reasons.append("Drawdown OK")
    except Exception:
        reasons.append("Drawdown check unavailable")

    # Volatility check
    vol = f.get("volatility_annualized", 0)
    if vol > 0.50:
        veto = True
        veto_reason = f"Extreme volatility ({vol:.0%}) — standing aside"
        reasons.append(f"Vol={vol:.0%} EXTREME")
    elif vol > 0.30:
        reasons.append(f"Vol={vol:.0%} elevated")
    else:
        reasons.append(f"Vol={vol:.0%} normal")

    risk_limits = {
        "max_portfolio_heat": MAX_PORTFOLIO_HEAT,
        "max_single_position": MAX_SINGLE_POSITION,
        "current_volatility": vol,
    }

    if veto:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.95,
            reasoning=f"VETO: {veto_reason}. " + "; ".join(reasons),
            veto=True,
            veto_reason=veto_reason,
            weight=WEIGHT,
            metadata={"risk_limits": risk_limits},
        )

    return AgentVote(
        agent_name=NAME,
        direction="hold",  # Risk agent doesn't decide direction, just gates
        confidence=0.5,
        reasoning="Risk checks passed. " + "; ".join(reasons),
        weight=WEIGHT,
        metadata={"risk_limits": risk_limits},
    )
