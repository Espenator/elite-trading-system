"""Debate Scorer — scores debate quality for WeightLearner feedback.

Scoring formula:
    quality = evidence_diversity * 0.4 + confidence_convergence * 0.3 + round_utilization * 0.3

Where:
    evidence_diversity = unique blackboard keys cited / total available (capped at 1.0)
    confidence_convergence = 1.0 - abs(final_bull - final_bear) for contested debates
    round_utilization = num_rounds / MAX_ROUNDS
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def score_debate(rounds, all_evidence_keys, max_rounds: int = 3) -> "DebateResult":
    """Score a completed debate.

    Args:
        rounds: List of DebateRound objects
        all_evidence_keys: List of all available blackboard evidence keys

    Returns:
        DebateResult with computed scores
    """
    from app.council.debate.debate_engine import DebateResult

    if not rounds:
        return DebateResult(
            rounds=[], quality_score=0.0, winner="contested",
            evidence_breadth=0.0, final_confidence_spread=0.0,
        )

    # Evidence diversity: unique keys cited across all rounds
    all_cited = set()
    for r in rounds:
        all_cited.update(r.bull_evidence)
        all_cited.update(r.bear_evidence)
    total_available = max(len(all_evidence_keys), 1)
    evidence_diversity = min(1.0, len(all_cited) / total_available)

    # Confidence convergence (how close the final round is)
    final_round = rounds[-1]
    final_spread = abs(final_round.bull_confidence - final_round.bear_confidence)
    confidence_convergence = 1.0 - final_spread  # high when contested/close

    # Round utilization
    round_utilization = len(rounds) / max_rounds

    # Weighted score
    quality_score = (
        evidence_diversity * 0.4
        + confidence_convergence * 0.3
        + round_utilization * 0.3
    )

    # Determine winner
    avg_bull = sum(r.bull_confidence for r in rounds) / len(rounds)
    avg_bear = sum(r.bear_confidence for r in rounds) / len(rounds)
    if abs(avg_bull - avg_bear) < 0.15:
        winner = "contested"
    elif avg_bull > avg_bear:
        winner = "bull"
    else:
        winner = "bear"

    return DebateResult(
        rounds=rounds,
        quality_score=round(quality_score, 4),
        winner=winner,
        evidence_breadth=round(evidence_diversity, 4),
        final_confidence_spread=round(final_spread, 4),
    )
