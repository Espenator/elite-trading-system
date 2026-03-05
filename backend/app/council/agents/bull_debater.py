"""Bull Debater Agent — argues FOR the trade thesis using blackboard evidence.

Part of Stage 5.5 (debate). Routed to Claude for reasoning depth.
Must cite specific blackboard evidence keys to support arguments.
"""
import logging
from typing import Any, Dict, List

from app.council.debate.debate_utils import parse_json_from_llm, summarize_evidence

logger = logging.getLogger(__name__)

NAME = "bull_debater"


async def evaluate_debate(
    symbol: str,
    proposed_direction: str,
    evidence: Dict[str, Any],
    prior_rounds: List[Any],
    round_num: int,
) -> Dict[str, Any]:
    """Argue FOR the proposed trade.

    Args:
        symbol: Ticker symbol
        proposed_direction: Proposed direction ("buy"/"sell")
        evidence: Evidence package from blackboard
        prior_rounds: Previous debate rounds for rebuttal
        round_num: Current round number

    Returns:
        Dict with argument, evidence keys cited, and confidence
    """
    from app.services.llm_router import Tier, get_llm_router

    # Build context from prior rounds for rebuttal
    prior_context = ""
    if prior_rounds:
        last = prior_rounds[-1]
        prior_context = (
            f"\nThe bear previously argued: {last.bear_argument}\n"
            f"Bear cited evidence: {last.bear_evidence}\n"
            f"Address their concerns in your rebuttal.\n"
        )

    evidence_summary = summarize_evidence(evidence)

    prompt = (
        f"You are the BULL debater for {symbol}. The council proposes: {proposed_direction.upper()}.\n\n"
        f"This is round {round_num} of the debate.\n"
        f"Available evidence:\n{evidence_summary}\n"
        f"{prior_context}\n"
        f"Your task: Argue strongly FOR this trade. Cite specific evidence keys.\n\n"
        f"Return JSON: {{\n"
        f'  "argument": "Your bull case in 2-3 sentences",\n'
        f'  "evidence": ["key1", "key2"],  // blackboard keys you cite\n'
        f'  "confidence": 0.0-1.0,  // how confident in the bull case\n'
        f'  "key_catalyst": "The single strongest reason for this trade"\n'
        f"}}"
    )

    router = get_llm_router()
    result = await router.route(
        tier=Tier.DEEP_CORTEX,
        messages=[
            {"role": "system", "content": "You are a bull case advocate for an algorithmic trading council. Always cite evidence. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        task="bull_debate",
        temperature=0.3,
        max_tokens=1024,
    )

    if result.content:
        parsed = parse_json_from_llm(result.content)
        if parsed:
            return parsed

    return {
        "argument": f"Bull case for {symbol} {proposed_direction}: supported by technical and fundamental signals.",
        "evidence": [],
        "confidence": 0.5,
    }
