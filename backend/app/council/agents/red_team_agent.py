"""Red Team Agent — stress-tests every decision against adversarial scenarios.

Part of Stage 5.5. Runs predefined stress scenarios against the proposed trade
to identify fragility. Uses GPU-accelerated computation on PC-2 for Monte Carlo
simulations when available.

Stress scenarios:
    flash_crash: market drops 5%+ in minutes
    liquidity_gap: bid-ask spread widens 10x
    correlated_drawdown: all positions move against simultaneously
    api_outage: broker goes down during open position
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "red_team"


@dataclass
class StressScenario:
    """A predefined adversarial stress scenario."""
    name: str
    description: str
    volatility_mult: float = 1.0
    liquidity_mult: float = 1.0
    correlation_spike: float = 0.0
    slippage_mult: float = 1.0
    fill_probability: float = 1.0
    drawdown_pct: float = 0.0
    can_exit: bool = True
    max_hold_hours: int = 0


@dataclass
class ScenarioResult:
    """Result of running one stress scenario."""
    scenario_name: str
    estimated_loss_pct: float  # worst-case loss as fraction
    estimated_loss_r: float  # worst-case loss in R-multiples
    survives_kelly: bool  # does the position survive Kelly sizing?
    recommendation: str  # "PROCEED", "REDUCE_SIZE", "REJECT"
    reasoning: str = ""


@dataclass
class RedTeamReport:
    """Aggregate stress test report."""
    scenario_results: List[ScenarioResult]
    worst_case_loss_pct: float
    worst_case_loss_r: float
    scenarios_survived: int
    total_scenarios: int
    overall_recommendation: str  # "PROCEED", "REDUCE_SIZE", "REJECT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios": [
                {
                    "name": r.scenario_name,
                    "estimated_loss_pct": round(r.estimated_loss_pct, 4),
                    "estimated_loss_r": round(r.estimated_loss_r, 2),
                    "survives_kelly": r.survives_kelly,
                    "recommendation": r.recommendation,
                    "reasoning": r.reasoning,
                }
                for r in self.scenario_results
            ],
            "worst_case_loss_pct": round(self.worst_case_loss_pct, 4),
            "worst_case_loss_r": round(self.worst_case_loss_r, 2),
            "scenarios_survived": self.scenarios_survived,
            "total_scenarios": self.total_scenarios,
            "overall_recommendation": self.overall_recommendation,
        }


# Predefined stress scenarios
STRESS_SCENARIOS = [
    StressScenario(
        name="flash_crash",
        description="Market drops 5%+ in minutes with extreme volatility",
        volatility_mult=3.0,
        liquidity_mult=0.2,
        correlation_spike=0.95,
        slippage_mult=5.0,
        drawdown_pct=0.05,
    ),
    StressScenario(
        name="liquidity_gap",
        description="Bid-ask spread widens 10x, severe slippage",
        volatility_mult=1.5,
        liquidity_mult=0.1,
        slippage_mult=10.0,
        fill_probability=0.3,
    ),
    StressScenario(
        name="correlated_drawdown",
        description="All positions move against simultaneously",
        volatility_mult=2.0,
        correlation_spike=0.98,
        drawdown_pct=0.15,
    ),
    StressScenario(
        name="api_outage",
        description="Broker API goes down during open position",
        can_exit=False,
        max_hold_hours=24,
        volatility_mult=1.5,
    ),
]


async def stress_test(
    blackboard: BlackboardState,
    proposed_direction: str,
    proposed_confidence: float,
    context: Dict[str, Any] = None,
) -> RedTeamReport:
    """Run all stress scenarios against the proposed trade.

    Args:
        blackboard: Current blackboard state
        proposed_direction: "buy" or "sell"
        proposed_confidence: Council's confidence level
        context: Additional context

    Returns:
        RedTeamReport with per-scenario results and overall recommendation
    """
    features = blackboard.raw_features.get("features", blackboard.raw_features)

    # Extract key parameters for stress testing
    entry_price = float(features.get("close", 100))
    atr = float(features.get("atr_14", entry_price * 0.02))
    stop_distance_pct = atr / entry_price if entry_price > 0 else 0.02
    kelly_pct = _get_kelly_pct(context)
    current_vix = float(features.get("vix_close", 20))

    results = []
    for scenario in STRESS_SCENARIOS:
        result = _evaluate_scenario(
            scenario=scenario,
            entry_price=entry_price,
            stop_distance_pct=stop_distance_pct,
            kelly_pct=kelly_pct,
            current_vix=current_vix,
            direction=proposed_direction,
        )
        results.append(result)

    # Aggregate
    worst_loss_pct = max(r.estimated_loss_pct for r in results) if results else 0
    worst_loss_r = max(r.estimated_loss_r for r in results) if results else 0
    survived = sum(1 for r in results if r.survives_kelly)

    # Overall recommendation
    if any(r.recommendation == "REJECT" for r in results):
        overall = "REJECT"
    elif sum(1 for r in results if r.recommendation == "REDUCE_SIZE") >= 2:
        overall = "REDUCE_SIZE"
    else:
        overall = "PROCEED"

    report = RedTeamReport(
        scenario_results=results,
        worst_case_loss_pct=worst_loss_pct,
        worst_case_loss_r=worst_loss_r,
        scenarios_survived=survived,
        total_scenarios=len(results),
        overall_recommendation=overall,
    )

    logger.info(
        "Red Team: %s — worst_case=%.1f%%, survived=%d/%d, recommendation=%s",
        blackboard.symbol, worst_loss_pct * 100, survived, len(results), overall,
    )

    return report


def _evaluate_scenario(
    scenario: StressScenario,
    entry_price: float,
    stop_distance_pct: float,
    kelly_pct: float,
    current_vix: float,
    direction: str,
) -> ScenarioResult:
    """Evaluate a single stress scenario."""
    # Base loss from drawdown
    base_loss = scenario.drawdown_pct if scenario.drawdown_pct else stop_distance_pct * scenario.volatility_mult

    # Slippage impact
    slippage_loss = stop_distance_pct * (scenario.slippage_mult - 1) * 0.1

    # Can't exit impact
    if not scenario.can_exit:
        # Assume VIX-proportional additional loss during outage
        outage_loss = (current_vix / 100) * (scenario.max_hold_hours / 6.5) * 0.5
        base_loss = max(base_loss, outage_loss)

    total_loss_pct = min(1.0, base_loss + slippage_loss)

    # R-multiple loss
    r_loss = total_loss_pct / stop_distance_pct if stop_distance_pct > 0 else total_loss_pct / 0.02

    # Kelly survival: does position survive with Kelly sizing?
    portfolio_loss = total_loss_pct * kelly_pct
    survives = portfolio_loss < 0.06  # MAX_PORTFOLIO_HEAT threshold

    # Recommendation
    if portfolio_loss >= 0.06 or r_loss > 5.0:
        recommendation = "REJECT"
        reasoning = f"Catastrophic: {scenario.name} → {portfolio_loss:.1%} portfolio loss ({r_loss:.1f}R)"
    elif portfolio_loss >= 0.03 or r_loss > 3.0:
        recommendation = "REDUCE_SIZE"
        reasoning = f"Dangerous: {scenario.name} → {portfolio_loss:.1%} portfolio loss ({r_loss:.1f}R). Reduce position."
    else:
        recommendation = "PROCEED"
        reasoning = f"Manageable: {scenario.name} → {portfolio_loss:.1%} portfolio loss ({r_loss:.1f}R)"

    return ScenarioResult(
        scenario_name=scenario.name,
        estimated_loss_pct=total_loss_pct,
        estimated_loss_r=r_loss,
        survives_kelly=survives,
        recommendation=recommendation,
        reasoning=reasoning,
    )


def _get_kelly_pct(context: Optional[Dict[str, Any]]) -> float:
    """Extract Kelly allocation percentage from context."""
    if context:
        return float(context.get("kelly_pct", 0.02))
    return 0.02  # default 2%


# Standard agent interface for TaskSpawner compatibility
async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Standard agent evaluate interface for the council DAG."""
    blackboard = context.get("blackboard")
    if not blackboard:
        return AgentVote(
            agent_name=NAME, direction="hold", confidence=0.0,
            reasoning="No blackboard available for stress testing",
        )

    # Get proposed direction from strategy
    proposed_direction = "hold"
    proposed_confidence = 0.5
    if blackboard.strategy and isinstance(blackboard.strategy, dict):
        proposed_direction = blackboard.strategy.get("direction", "hold")
        proposed_confidence = float(blackboard.strategy.get("confidence", 0.5))

    report = await stress_test(blackboard, proposed_direction, proposed_confidence, context)
    blackboard.red_team_report = report.to_dict()

    # Convert to AgentVote
    if report.overall_recommendation == "REJECT":
        return AgentVote(
            agent_name=NAME, direction="hold", confidence=0.9,
            reasoning=f"RED TEAM REJECT: worst_case={report.worst_case_loss_pct:.1%}, survived={report.scenarios_survived}/{report.total_scenarios}",
            veto=True, veto_reason=f"Stress test: {report.overall_recommendation}",
            metadata=report.to_dict(),
        )
    elif report.overall_recommendation == "REDUCE_SIZE":
        return AgentVote(
            agent_name=NAME, direction=proposed_direction, confidence=0.4,
            reasoning=f"RED TEAM CAUTION: reduce size. worst_case={report.worst_case_loss_pct:.1%}",
            metadata=report.to_dict(),
        )
    else:
        return AgentVote(
            agent_name=NAME, direction=proposed_direction, confidence=0.7,
            reasoning=f"RED TEAM PASS: survived={report.scenarios_survived}/{report.total_scenarios}",
            metadata=report.to_dict(),
        )
