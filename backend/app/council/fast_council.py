"""FastCouncil — 5-agent pre-screening tier (<200 ms) for the council pipeline.

Issue #38 — E4: Multi-Tier Council (Fast 5-agent + Deep 35-agent).

Architecture
------------
The full 35-agent council is accurate but takes ~1 second.  FastCouncil
provides a lightweight pre-screening step that runs 5 feature-only agents
concurrently and either:

  * Returns ``skip_deep=True`` when the signal is clearly a HOLD (low
    confidence), saving the expensive full-council evaluation.
  * Returns ``skip_deep=False`` when the signal is promising, allowing
    ``CouncilGate`` to escalate to the full council.

Agents used (Stage 1 + Stage 2 + Stage 5 subset — no LLM calls):
    1. market_perception  — OHLCV price action
    2. rsi                — multi-timeframe RSI
    3. ema_trend          — EMA cascade direction
    4. risk               — hard risk guardrails (VETO capable)
    5. execution          — execution readiness (VETO capable)

Decision rules
--------------
  * Any VETO  → direction="hold", confidence=0.0, skip_deep=True
  * Consensus hold (>= 3 of 5 agents say "hold") → skip_deep=True
  * direction == "hold" with confidence < CONFIDENCE_MIN → skip_deep=True
  * Otherwise → skip_deep=False (escalate to full council)

Usage::

    from app.council.fast_council import run_fast_council

    result = await run_fast_council(
        symbol="AAPL",
        features=features_dict,      # same dict as run_council()
        context=context_dict,        # optional extra context
        timeout=0.20,                # seconds (default 200 ms)
    )
    if result.skip_deep:
        # short-circuit: do not invoke the full council
        ...
    else:
        # escalate to run_council()
        ...

Integration with CouncilGate
-----------------------------
Set ``FAST_COUNCIL_ENABLED=true`` (default true) to enable pre-screening.
When disabled, ``CouncilGate`` falls back to the previous behaviour of
directly calling ``run_council()`` for every qualifying signal.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

FAST_AGENTS: List[str] = [
    "market_perception",
    "rsi",
    "ema_trend",
    "risk",
    "execution",
]

CONFIDENCE_MIN = 0.35  # Below this → skip_deep regardless of direction
HOLD_QUORUM = 3        # N-of-5 agents voting "hold" → skip_deep
DEFAULT_TIMEOUT = 0.20  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FastCouncilResult:
    """Outcome of a fast council pre-screening.

    Attributes
    ----------
    direction:
        Aggregated direction: "buy" | "sell" | "hold".
    confidence:
        Weighted average confidence (0-1).
    skip_deep:
        True  → do NOT invoke the full council (signal cleared or vetoed).
        False → escalate to the full 35-agent council.
    veto:
        True when a VETO agent fired.
    veto_reasons:
        Reasons for any veto.
    votes:
        Individual agent votes collected.
    latency_ms:
        Wall-clock time for the fast council run.
    """

    direction: str = "hold"
    confidence: float = 0.0
    skip_deep: bool = False
    veto: bool = False
    veto_reasons: List[str] = field(default_factory=list)
    votes: List[AgentVote] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": round(self.confidence, 3),
            "skip_deep": self.skip_deep,
            "veto": self.veto,
            "veto_reasons": self.veto_reasons,
            "latency_ms": round(self.latency_ms, 1),
            "votes": [
                {
                    "agent": v.agent_name,
                    "direction": v.direction,
                    "confidence": round(v.confidence, 3),
                    "veto": v.veto,
                }
                for v in self.votes
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent loader
# ─────────────────────────────────────────────────────────────────────────────

_AGENT_MODULE_MAP: Dict[str, str] = {
    "market_perception": "app.council.agents.market_perception_agent",
    "rsi":               "app.council.agents.rsi_agent",
    "ema_trend":         "app.council.agents.ema_trend_agent",
    "risk":              "app.council.agents.risk_agent",
    "execution":         "app.council.agents.execution_agent",
}


async def _run_agent_safe(
    name: str,
    symbol: str,
    timeframe: str,
    features: Dict[str, Any],
    context: Dict[str, Any],
) -> Optional[AgentVote]:
    """Import, evaluate, and return an agent vote; return None on failure."""
    import importlib
    module_path = _AGENT_MODULE_MAP.get(name)
    if not module_path:
        return None
    try:
        mod = importlib.import_module(module_path)
        vote: AgentVote = await mod.evaluate(symbol, timeframe, features, context)
        return vote
    except Exception as exc:
        logger.debug("FastCouncil: agent '%s' failed: %s", name, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core function
# ─────────────────────────────────────────────────────────────────────────────

async def run_fast_council(
    symbol: str,
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    timeframe: str = "1d",
    timeout: float = DEFAULT_TIMEOUT,
) -> FastCouncilResult:
    """Run the 5-agent fast council and return a FastCouncilResult.

    Parameters
    ----------
    symbol:
        Ticker to evaluate.
    features:
        Pre-computed feature dict (same shape as run_council).  If None,
        an empty dict is used (agents fall back to their defaults).
    context:
        Optional extra context for agents.
    timeframe:
        Bar timeframe string (default "1d").
    timeout:
        Maximum wall-clock seconds allowed for all agents (default 200 ms).
        Agents that exceed the timeout contribute no vote.

    Returns
    -------
    FastCouncilResult
    """
    t0 = time.monotonic()
    if features is None:
        features = {}
    if context is None:
        context = {}

    # Run all agents concurrently, respecting the timeout
    tasks = [
        _run_agent_safe(name, symbol, timeframe, features, context)
        for name in FAST_AGENTS
    ]
    try:
        raw_results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("FastCouncil: timed out for %s (%.0fms)", symbol, timeout * 1000)
        latency_ms = (time.monotonic() - t0) * 1000
        return FastCouncilResult(
            direction="hold",
            confidence=0.0,
            skip_deep=True,  # Timeout → conservative hold
            latency_ms=latency_ms,
        )

    latency_ms = (time.monotonic() - t0) * 1000

    # Collect valid votes
    votes: List[AgentVote] = []
    for res in raw_results:
        if isinstance(res, AgentVote):
            votes.append(res)

    if not votes:
        return FastCouncilResult(
            direction="hold",
            confidence=0.0,
            skip_deep=True,
            latency_ms=latency_ms,
        )

    # Check for any VETO
    veto_reasons: List[str] = []
    for v in votes:
        if v.veto:
            veto_reasons.append(v.veto_reason or v.agent_name)

    if veto_reasons:
        return FastCouncilResult(
            direction="hold",
            confidence=0.0,
            skip_deep=True,
            veto=True,
            veto_reasons=veto_reasons,
            votes=votes,
            latency_ms=latency_ms,
        )

    # Tally directions and aggregate confidence
    direction_counts: Dict[str, int] = {"buy": 0, "sell": 0, "hold": 0}
    confidence_sum = 0.0
    for v in votes:
        direction_counts[v.direction] = direction_counts.get(v.direction, 0) + 1
        confidence_sum += v.confidence

    avg_confidence = confidence_sum / len(votes)
    hold_count = direction_counts.get("hold", 0)

    # Majority direction
    majority_dir = max(direction_counts, key=lambda d: direction_counts[d])

    # Skip-deep rules
    skip_deep = False
    if hold_count >= HOLD_QUORUM:
        skip_deep = True
    elif majority_dir == "hold" and avg_confidence < CONFIDENCE_MIN:
        skip_deep = True
    elif avg_confidence < CONFIDENCE_MIN:
        skip_deep = True

    result = FastCouncilResult(
        direction=majority_dir,
        confidence=round(avg_confidence, 3),
        skip_deep=skip_deep,
        votes=votes,
        latency_ms=latency_ms,
    )

    logger.debug(
        "FastCouncil %s → %s (conf=%.2f, skip=%s, %.1fms)",
        symbol,
        majority_dir,
        avg_confidence,
        skip_deep,
        latency_ms,
    )
    return result
