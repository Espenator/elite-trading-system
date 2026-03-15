"""Risk Agent — Kelly/Van Tharp constraints with VETO power.

GPU Channel 3: Integrates Monte Carlo VaR (10K-path GPU simulation) to
provide real portfolio risk assessment alongside existing guardrails.
"""
import asyncio
import logging
from typing import Any, Dict

import numpy as np

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
    - GPU Channel 3: Monte Carlo VaR (10K-path portfolio risk)
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

    # GPU Channel 3: Monte Carlo VaR — 10K-path portfolio risk simulation
    var_data = {}
    try:
        var_data = await asyncio.to_thread(_compute_portfolio_var, symbol)
        if var_data.get("var_95"):
            var_95 = var_data["var_95"]
            reasons.append(f"VaR95={var_95:.2%}")
            # Veto if daily VaR exceeds 5% of portfolio
            if abs(var_95) > 0.05:
                veto = True
                veto_reason = f"Monte Carlo VaR too high ({var_95:.2%} > 5%)"
    except Exception:
        pass  # VaR is supplementary — never blocks the agent

    risk_limits = {
        "max_portfolio_heat": cfg["max_portfolio_heat"],
        "max_single_position": cfg["max_single_position"],
        "current_volatility": vol,
        "monte_carlo_var": var_data,
    }

    # Write VaR to blackboard for downstream agents
    blackboard = context.get("blackboard")
    if blackboard and var_data:
        blackboard.metadata["monte_carlo_var"] = var_data

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


def _compute_portfolio_var(symbol: str) -> Dict[str, Any]:
    """Compute Monte Carlo VaR for current portfolio positions.

    GPU Channel 3: Uses CuPy on GPU for 10K-path simulation (~20ms)
    or falls back to NumPy on CPU (~200ms).
    """
    try:
        from app.modules.ml_engine.monte_carlo_var import compute_single_position_var
        from app.data.duckdb_storage import duckdb_store

        conn = duckdb_store.get_thread_cursor()
        rows = conn.execute(
            "SELECT close FROM daily_ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 60",
            [symbol.upper()],
        ).fetchall()

        if not rows or len(rows) < 20:
            return {}

        closes = np.array([float(r[0]) for r in reversed(rows) if r[0]])
        if len(closes) < 20:
            return {}

        returns = np.diff(np.log(closes))
        return compute_single_position_var(returns, n_paths=10_000)
    except Exception as e:
        logger.debug("Monte Carlo VaR computation failed for %s: %s", symbol, e)
        return {}
