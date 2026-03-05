"""Debate Engine — structured Bull/Bear debate mechanism.

Inserts a debate stage (5.5) between risk/execution and critic where
opposing agents argue for and against the trade thesis using blackboard
evidence. An optional Claude judge summarizes contradictions and assigns
quality scores.

Research basis: TradingAgents Framework (UCLA/MIT) — agentic debate
between opposing viewpoints significantly improves decision quality.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.council.blackboard import BlackboardState

logger = logging.getLogger(__name__)


@dataclass
class DebateRound:
    """A single round of bull/bear exchange."""
    round_num: int
    bull_argument: str
    bear_argument: str
    bull_evidence: List[str] = field(default_factory=list)  # blackboard keys cited
    bear_evidence: List[str] = field(default_factory=list)
    bull_confidence: float = 0.5
    bear_confidence: float = 0.5


@dataclass
class DebateResult:
    """Result of the full debate."""
    rounds: List[DebateRound]
    quality_score: float  # 0.0-1.0
    winner: str  # "bull", "bear", or "contested"
    evidence_breadth: float  # unique keys cited / total available
    final_confidence_spread: float  # abs(bull_conf - bear_conf)
    judge_summary: str = ""
    action_modifier: str = "neutral"  # "boost", "neutral", "dampen", "veto"
    transcript: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rounds": [
                {
                    "round": r.round_num,
                    "bull": r.bull_argument,
                    "bear": r.bear_argument,
                    "bull_evidence": r.bull_evidence,
                    "bear_evidence": r.bear_evidence,
                    "bull_confidence": r.bull_confidence,
                    "bear_confidence": r.bear_confidence,
                }
                for r in self.rounds
            ],
            "quality_score": round(self.quality_score, 3),
            "winner": self.winner,
            "evidence_breadth": round(self.evidence_breadth, 3),
            "final_confidence_spread": round(self.final_confidence_spread, 3),
            "judge_summary": self.judge_summary,
            "action_modifier": self.action_modifier,
        }


class DebateEngine:
    """Runs structured Bull/Bear debate using blackboard evidence."""

    MAX_ROUNDS = 3
    EARLY_TERMINATION_SPREAD = 0.7

    def __init__(self, max_rounds: int = None):
        if max_rounds is not None:
            self.MAX_ROUNDS = max_rounds

    async def run_debate(
        self,
        blackboard: BlackboardState,
        symbol: str,
        proposed_direction: str,
        context: Dict[str, Any] = None,
    ) -> DebateResult:
        """Execute the structured debate.

        Args:
            blackboard: Current BlackboardState with all upstream data
            symbol: Ticker symbol
            proposed_direction: Council's preliminary direction ("buy"/"sell"/"hold")
            context: Additional context dict

        Returns:
            DebateResult with full transcript, scores, and action modifier
        """
        rounds: List[DebateRound] = []
        all_evidence_keys = self._get_available_evidence_keys(blackboard)

        # Build evidence summary for debaters
        evidence_package = self._build_evidence_package(blackboard)

        for round_num in range(1, self.MAX_ROUNDS + 1):
            # Run bull and bear in parallel
            bull_coro = self._run_bull(
                symbol, proposed_direction, evidence_package, rounds, round_num
            )
            bear_coro = self._run_bear(
                symbol, proposed_direction, evidence_package, rounds, round_num
            )

            bull_result, bear_result = await asyncio.gather(
                bull_coro, bear_coro, return_exceptions=True
            )

            # Handle errors gracefully
            if isinstance(bull_result, Exception):
                bull_result = {"argument": f"Bull error: {bull_result}", "evidence": [], "confidence": 0.5}
            if isinstance(bear_result, Exception):
                bear_result = {"argument": f"Bear error: {bear_result}", "evidence": [], "confidence": 0.5}

            debate_round = DebateRound(
                round_num=round_num,
                bull_argument=bull_result.get("argument", ""),
                bear_argument=bear_result.get("argument", ""),
                bull_evidence=bull_result.get("evidence", []),
                bear_evidence=bear_result.get("evidence", []),
                bull_confidence=float(bull_result.get("confidence", 0.5)),
                bear_confidence=float(bear_result.get("confidence", 0.5)),
            )
            rounds.append(debate_round)

            # Early termination if confidence spread is decisive
            spread = abs(debate_round.bull_confidence - debate_round.bear_confidence)
            if spread > self.EARLY_TERMINATION_SPREAD:
                logger.info(
                    "Debate early termination at round %d (spread=%.2f)", round_num, spread
                )
                break

        # Score the debate
        result = self._score_debate(rounds, all_evidence_keys)

        # Optional: Claude judge summarization
        try:
            judge_result = await self._run_judge(symbol, proposed_direction, rounds)
            result.judge_summary = judge_result.get("summary", "")
            result.action_modifier = judge_result.get("action_modifier", "neutral")
        except Exception as e:
            logger.debug("Judge summarization failed: %s", e)

        return result

    async def _run_bull(
        self,
        symbol: str,
        direction: str,
        evidence: Dict[str, Any],
        prior_rounds: List[DebateRound],
        round_num: int,
    ) -> Dict[str, Any]:
        """Run the bull debater agent."""
        from app.council.agents.bull_debater import evaluate_debate
        return await evaluate_debate(symbol, direction, evidence, prior_rounds, round_num)

    async def _run_bear(
        self,
        symbol: str,
        direction: str,
        evidence: Dict[str, Any],
        prior_rounds: List[DebateRound],
        round_num: int,
    ) -> Dict[str, Any]:
        """Run the bear debater agent."""
        from app.council.agents.bear_debater import evaluate_debate
        return await evaluate_debate(symbol, direction, evidence, prior_rounds, round_num)

    async def _run_judge(
        self,
        symbol: str,
        direction: str,
        rounds: List[DebateRound],
    ) -> Dict[str, Any]:
        """Optional Claude judge that summarizes and scores the debate."""
        from app.services.llm_router import Tier, get_llm_router

        transcript = "\n".join([
            f"Round {r.round_num}:\n"
            f"  BULL (conf={r.bull_confidence:.2f}): {r.bull_argument}\n"
            f"  BEAR (conf={r.bear_confidence:.2f}): {r.bear_argument}"
            for r in rounds
        ])

        prompt = (
            f"You are a debate judge for a trading council evaluating {symbol} ({direction}).\n\n"
            f"Debate transcript:\n{transcript}\n\n"
            "Analyze:\n"
            "1. Which side presented stronger evidence?\n"
            "2. Were there contradictions that reveal risk?\n"
            "3. What is your recommendation?\n\n"
            "Return JSON: {\"summary\": str, \"evidence_quality\": 0-100, "
            "\"action_modifier\": \"boost\"|\"neutral\"|\"dampen\"|\"veto\", "
            "\"key_contradiction\": str|null}"
        )

        router = get_llm_router()
        result = await router.route(
            tier=Tier.DEEP_CORTEX,
            messages=[
                {"role": "system", "content": "You are a rigorous debate judge for an algorithmic trading council. Return JSON."},
                {"role": "user", "content": prompt},
            ],
            task="debate_judge",
            temperature=0.2,
            max_tokens=1024,
        )

        if result.content:
            import re
            try:
                # Try JSON parse
                parsed = json.loads(result.content.strip())
                return parsed
            except json.JSONDecodeError:
                # Try extracting JSON from markdown
                match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result.content, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        pass
        return {"summary": result.content or "Judge unavailable", "action_modifier": "neutral"}

    def _score_debate(
        self, rounds: List[DebateRound], all_evidence_keys: List[str]
    ) -> DebateResult:
        """Score the debate using the debate_scorer formula."""
        from app.council.debate.debate_scorer import score_debate
        return score_debate(rounds, all_evidence_keys)

    def _get_available_evidence_keys(self, blackboard: BlackboardState) -> List[str]:
        """List all available evidence keys on the blackboard."""
        keys = []
        if blackboard.perceptions:
            keys.extend(list(blackboard.perceptions.keys()))
        if blackboard.hypothesis:
            keys.append("hypothesis")
        if blackboard.strategy:
            keys.append("strategy")
        if blackboard.risk_assessment:
            keys.append("risk_assessment")
        if blackboard.execution_plan:
            keys.append("execution_plan")
        # Add intelligence keys
        intel = blackboard.metadata.get("intelligence", {})
        keys.extend([k for k in intel.keys() if k not in ("symbol", "regime", "gathered_at", "tiers_queried", "errors", "total_latency_ms")])
        return keys

    def _build_evidence_package(self, blackboard: BlackboardState) -> Dict[str, Any]:
        """Build a compact evidence package for debaters."""
        return {
            "perceptions": blackboard.perceptions,
            "hypothesis": blackboard.hypothesis,
            "strategy": blackboard.strategy,
            "risk_assessment": blackboard.risk_assessment,
            "intelligence": blackboard.metadata.get("intelligence", {}),
            "regime_belief": blackboard.regime_belief,
        }
