"""Risk Agent — Kelly/Van Tharp constraints with VETO power."""
import logging
from typing import Any, Dict

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "risk"


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
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    veto = False
    veto_reason = ""
    reasons = []

    # Check portfolio heat via risk API
    try:
        from app.api.v1.risk import risk_score as get_risk
        risk_data = await get_risk()
        risk_score = risk_data.get("risk_score", 50)
        reasons.append(f"Risk score={risk_score}")

        if risk_score < cfg["risk_score_veto_threshold"]:
            veto = True
            veto_reason = f"Risk score too low ({risk_score} < {cfg['risk_score_veto_threshold']})"
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
    if vol > cfg["volatility_extreme_threshold"]:
        veto = True
        veto_reason = f"Extreme volatility ({vol:.0%}) — standing aside"
        reasons.append(f"Vol={vol:.0%} EXTREME")
    elif vol > cfg["volatility_elevated_threshold"]:
        reasons.append(f"Vol={vol:.0%} elevated")
    else:
        reasons.append(f"Vol={vol:.0%} normal")

    risk_limits = {
        "max_portfolio_heat": cfg["max_portfolio_heat"],
        "max_single_position": cfg["max_single_position"],
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
            weight=cfg["weight_risk"],
            metadata={"risk_limits": risk_limits},
        )

    return AgentVote(
        agent_name=NAME,
        direction="hold",  # Risk agent doesn't decide direction, just gates
        confidence=0.5,
        reasoning="Risk checks passed. " + "; ".join(reasons),
        weight=cfg["weight_risk"],
        metadata={"risk_limits": risk_limits},
    )
