"""Fast Council — lightweight pre-screening path for the multi-tier council.

Runs a small subset of fast, local agents (no LLM calls, no external API
calls) to decide whether a signal is worth escalating to the full deep
council.  The goal is to drop obvious holds/vetoes cheaply before the
expensive 35-agent DAG runs.

Fast-path stages
----------------
  Stage F1 (perception subset): market_perception, regime
  Stage F2 (technical subset):  rsi, ema_trend, bbv, relative_strength
  Stage F3 (risk gate):         risk

Escalation rules (applied in order)
------------------------------------
1. FAST_VETO_AGENTS veto          → fast_hold, vetoed=True,  escalate=False
2. FAST_REQUIRED_AGENTS missing   → fast_hold, vetoed=False, escalate=False
3. Weighted confidence < FAST_HOLD_THRESHOLD → fast_hold,   escalate=False
4. Weighted direction == "hold"   → fast_hold, vetoed=False, escalate=False
5. Otherwise                      → escalate=True  (invoke deep council)

Usage
-----
    from app.council.fast_council import run_fast_council

    result = await run_fast_council(symbol="AAPL", timeframe="1d")
    if result.escalate:
        decision = await run_council(symbol="AAPL", timeframe="1d")
    else:
        # signal dropped — result.reasoning explains why
        pass
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote
from app.council.task_spawner import TaskSpawner

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent sets for each fast-path stage
# ---------------------------------------------------------------------------

# Stage F1: lightweight perception — no external API, fast local inference
FAST_STAGE_F1: List[str] = ["market_perception", "regime"]

# Stage F2: pure technical indicators — deterministic, sub-millisecond
FAST_STAGE_F2: List[str] = ["rsi", "ema_trend", "bbv", "relative_strength"]

# Stage F3: basic risk gate — local portfolio-heat check only
FAST_STAGE_F3: List[str] = ["risk"]

# ---------------------------------------------------------------------------
# Arbitration constants
# ---------------------------------------------------------------------------

# Agents whose presence is required for a directional fast decision
FAST_REQUIRED_AGENTS: frozenset = frozenset({"regime", "risk"})

# Only risk can issue a hard veto in the fast path
FAST_VETO_AGENTS: frozenset = frozenset({"risk"})

# Below this weighted confidence the fast path issues a hold rather than
# escalating — avoids sending marginal signals to the expensive deep council.
# Confidence here is the *fraction* of total weight that the winning direction
# captures (e.g., 0.50 means the winning direction holds 50% of all vote
# weight).  A near three-way tie produces a winning fraction ≈ 0.33, which
# falls below the threshold and is correctly suppressed.
# Matches the full arbiter's execution_ready floor (final_confidence > 0.4).
FAST_HOLD_THRESHOLD: float = 0.40


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class FastCouncilResult:
    """Result from the fast pre-screening council.

    Attributes
    ----------
    symbol:
        Ticker that was evaluated.
    direction:
        Consensus direction from fast agents: ``"buy"`` | ``"sell"`` | ``"hold"``.
    confidence:
        Weighted-vote confidence in [0, 1].
    escalate:
        ``True`` → signal should proceed to the full deep council.
        ``False`` → signal was dropped by the fast path.
    vetoed:
        ``True`` → a fast veto agent (risk) blocked the trade.
    veto_reasons:
        Human-readable veto reasons when ``vetoed=True``.
    agent_votes:
        Individual :class:`~app.council.schemas.AgentVote` objects collected
        during the fast evaluation.
    reasoning:
        Short plain-English summary of the escalation decision.
    latency_ms:
        Wall-clock evaluation time in milliseconds.
    """

    symbol: str
    direction: str           # "buy" | "sell" | "hold"
    confidence: float        # 0.0 – 1.0
    escalate: bool           # True → invoke deep council
    vetoed: bool             # True → hard stop, do not escalate
    veto_reasons: List[str] = field(default_factory=list)
    agent_votes: List[AgentVote] = field(default_factory=list)
    reasoning: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "confidence": round(self.confidence, 4),
            "escalate": self.escalate,
            "vetoed": self.vetoed,
            "veto_reasons": self.veto_reasons,
            "agent_votes": [v.to_dict() for v in self.agent_votes],
            "reasoning": self.reasoning,
            "latency_ms": round(self.latency_ms, 1),
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_fast_council(
    symbol: str,
    timeframe: str = "1d",
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> FastCouncilResult:
    """Run the fast pre-screening council and return a :class:`FastCouncilResult`.

    This function is intentionally lightweight — no LLM calls, no external
    API calls.  The goal is to quickly discard obvious holds and vetoes before
    invoking the expensive full council.

    Args:
        symbol:    Ticker symbol to evaluate.
        timeframe: Timeframe string (default ``"1d"``).
        features:  Pre-computed feature dict.  If ``None``, auto-computed via
                   ``feature_aggregator.aggregate()``.
        context:   Additional key-value context forwarded to agents.

    Returns:
        :class:`FastCouncilResult` — check ``.escalate`` to decide whether to
        invoke the deep council.
    """
    t0 = time.monotonic() * 1000
    if context is None:
        context = {}
    context = dict(context)  # local copy — don't mutate caller's dict

    # Auto-compute features when not provided
    if features is None:
        try:
            from app.features.feature_aggregator import aggregate
            fv = await aggregate(symbol, timeframe=timeframe)
            features = fv.to_dict()
        except Exception as exc:
            logger.warning(
                "Fast council: feature aggregation failed for %s: %s", symbol, exc
            )
            features = {"features": {}, "symbol": symbol}

    # Lightweight blackboard — pre-council heavy setup is skipped intentionally
    blackboard = BlackboardState(symbol=symbol, raw_features=features)
    blackboard.council_start_ms = t0
    context["blackboard"] = blackboard

    # ── Homeostasis gate (shared with full council) ──────────────────────────
    try:
        from app.council.homeostasis import get_homeostasis
        homeostasis = get_homeostasis()
        await homeostasis.check_vitals()
        mode = homeostasis.get_mode()
        if mode == "HALTED":
            logger.warning(
                "Fast council: homeostasis HALTED for %s — skipping", symbol
            )
            return FastCouncilResult(
                symbol=symbol,
                direction="hold",
                confidence=0.0,
                escalate=False,
                vetoed=True,
                veto_reasons=["Homeostasis: system HALTED"],
                reasoning="System halted by homeostasis",
                latency_ms=time.monotonic() * 1000 - t0,
            )
        context["homeostasis_mode"] = mode
    except Exception as exc:
        logger.debug("Fast council: homeostasis check skipped: %s", exc)

    # ── Circuit breaker ──────────────────────────────────────────────────────
    try:
        from app.council.reflexes.circuit_breaker import circuit_breaker
        halt_reason = await circuit_breaker.check_all(blackboard)
        if halt_reason:
            logger.warning(
                "Fast council: circuit breaker fired for %s: %s", symbol, halt_reason
            )
            return FastCouncilResult(
                symbol=symbol,
                direction="hold",
                confidence=0.0,
                escalate=False,
                vetoed=True,
                veto_reasons=[f"Circuit breaker: {halt_reason}"],
                reasoning=f"Halted by circuit breaker: {halt_reason}",
                latency_ms=time.monotonic() * 1000 - t0,
            )
    except Exception as exc:
        logger.debug("Fast council: circuit breaker check skipped: %s", exc)

    # ── Agent execution ──────────────────────────────────────────────────────
    spawner = TaskSpawner(blackboard)
    spawner.register_all_agents()

    all_votes: List[AgentVote] = []

    # Stage F1: Perception subset (parallel)
    try:
        f1_configs = [
            {
                "agent_type": agent,
                "symbol": symbol,
                "timeframe": timeframe,
                "context": context,
            }
            for agent in FAST_STAGE_F1
        ]
        f1_votes = await spawner.spawn_parallel(f1_configs)
        all_votes.extend(f1_votes)
        for v in f1_votes:
            blackboard.perceptions[v.agent_name] = v.to_dict()
    except Exception as exc:
        logger.warning("Fast council Stage F1 failed for %s: %s", symbol, exc)

    # Stage F2: Technical subset (parallel)
    try:
        f2_configs = [
            {
                "agent_type": agent,
                "symbol": symbol,
                "timeframe": timeframe,
                "context": context,
            }
            for agent in FAST_STAGE_F2
        ]
        f2_votes = await spawner.spawn_parallel(f2_configs)
        all_votes.extend(f2_votes)
        for v in f2_votes:
            blackboard.perceptions[v.agent_name] = v.to_dict()
    except Exception as exc:
        logger.warning("Fast council Stage F2 failed for %s: %s", symbol, exc)

    # Stage F3: Risk gate (single agent)
    try:
        risk_vote = await spawner.spawn("risk", symbol, timeframe, context=context)
        if risk_vote is not None:
            all_votes.append(risk_vote)
            blackboard.risk_assessment = risk_vote.to_dict()
    except Exception as exc:
        logger.warning(
            "Fast council Stage F3 (risk) failed for %s: %s", symbol, exc
        )

    latency_ms = time.monotonic() * 1000 - t0
    result = _fast_arbitrate(symbol, all_votes, latency_ms)

    logger.info(
        "Fast council %s: %s @ %.0f%% conf — %s (%.0fms, %d agents)",
        symbol,
        result.direction.upper(),
        result.confidence * 100,
        "ESCALATE" if result.escalate else ("VETO" if result.vetoed else "HOLD"),
        result.latency_ms,
        len(all_votes),
    )
    return result


# ---------------------------------------------------------------------------
# Pure arbitration logic (testable without async)
# ---------------------------------------------------------------------------

def _fast_arbitrate(
    symbol: str,
    votes: List[AgentVote],
    latency_ms: float,
) -> FastCouncilResult:
    """Apply fast arbitration rules and return a :class:`FastCouncilResult`.

    Rules are applied in order; the first matching rule wins.

    1. ``FAST_VETO_AGENTS`` veto          → fast_hold, vetoed=True,  escalate=False
    2. ``FAST_REQUIRED_AGENTS`` missing   → fast_hold, vetoed=False, escalate=False
    3. Weighted confidence < threshold    → fast_hold, vetoed=False, escalate=False
    4. Weighted direction == ``"hold"``   → fast_hold, vetoed=False, escalate=False
    5. Otherwise                          → escalate=True

    Args:
        symbol:     Ticker symbol (for result labelling).
        votes:      Agent votes collected during the fast evaluation.
        latency_ms: Elapsed wall-clock time to include in the result.

    Returns:
        :class:`FastCouncilResult`
    """
    # ── Rule 1: Veto check ───────────────────────────────────────────────────
    veto_reasons = [
        f"{v.agent_name}: {v.veto_reason}"
        for v in votes
        if v.veto and v.agent_name in FAST_VETO_AGENTS
    ]
    if veto_reasons:
        return FastCouncilResult(
            symbol=symbol,
            direction="hold",
            confidence=0.0,
            escalate=False,
            vetoed=True,
            veto_reasons=veto_reasons,
            agent_votes=votes,
            reasoning=f"Fast veto: {'; '.join(veto_reasons)}",
            latency_ms=latency_ms,
        )

    # ── Rule 2: Required agents present ─────────────────────────────────────
    present = {v.agent_name for v in votes}
    missing = FAST_REQUIRED_AGENTS - present
    if missing:
        return FastCouncilResult(
            symbol=symbol,
            direction="hold",
            confidence=0.0,
            escalate=False,
            vetoed=False,
            agent_votes=votes,
            reasoning=f"Fast hold: required agents absent: {sorted(missing)}",
            latency_ms=latency_ms,
        )

    # ── Weighted vote aggregation (mirrors full arbiter) ─────────────────────
    buy_w = sell_w = hold_w = total_w = 0.0
    for v in votes:
        if v.veto:
            continue
        w = v.weight * v.confidence
        total_w += w
        if v.direction == "buy":
            buy_w += w
        elif v.direction == "sell":
            sell_w += w
        else:
            hold_w += w

    if total_w == 0:
        direction, confidence = "hold", 0.0
    elif buy_w == sell_w:
        # Mirrors the full arbiter's tie-breaking rule: exact buy/sell tie → hold.
        # Confidence reflects hold_w share (may be 0.0 when there are no hold votes).
        direction = "hold"
        confidence = hold_w / total_w if hold_w > 0 else 0.0
    else:
        max_w = max(buy_w, sell_w, hold_w)
        if max_w == buy_w:
            direction, confidence = "buy", buy_w / total_w
        elif max_w == sell_w:
            direction, confidence = "sell", sell_w / total_w
        else:
            direction, confidence = "hold", hold_w / total_w

    # ── Rule 3: Confidence below threshold ──────────────────────────────────
    if confidence < FAST_HOLD_THRESHOLD:
        return FastCouncilResult(
            symbol=symbol,
            direction="hold",
            confidence=round(confidence, 4),
            escalate=False,
            vetoed=False,
            agent_votes=votes,
            reasoning=(
                f"Fast hold: confidence {confidence:.0%} < "
                f"threshold {FAST_HOLD_THRESHOLD:.0%}"
            ),
            latency_ms=latency_ms,
        )

    # ── Rule 4: Majority voted hold ──────────────────────────────────────────
    if direction == "hold":
        return FastCouncilResult(
            symbol=symbol,
            direction="hold",
            confidence=round(confidence, 4),
            escalate=False,
            vetoed=False,
            agent_votes=votes,
            reasoning="Fast hold: majority voted hold",
            latency_ms=latency_ms,
        )

    # ── Rule 5: Escalate ─────────────────────────────────────────────────────
    counts: Dict[str, int] = {"buy": 0, "sell": 0, "hold": 0}
    for v in votes:
        if not v.veto:
            counts[v.direction] = counts.get(v.direction, 0) + 1

    return FastCouncilResult(
        symbol=symbol,
        direction=direction,
        confidence=round(confidence, 4),
        escalate=True,
        vetoed=False,
        agent_votes=votes,
        reasoning=(
            f"Fast council: {direction.upper()} @ {confidence:.0%} confidence "
            f"(buy={counts['buy']}, sell={counts['sell']}, hold={counts['hold']}) "
            f"— escalating to deep council"
        ),
        latency_ms=latency_ms,
    )
