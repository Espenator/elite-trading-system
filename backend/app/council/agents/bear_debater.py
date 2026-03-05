"""Bear Debater Agent — argues AGAINST the trade thesis using blackboard evidence.

Part of Stage 5.5 (debate). Routed to Claude for reasoning depth.
Must cite specific blackboard evidence keys to support arguments.
"""
import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

NAME = "bear_debater"


async def evaluate_debate(
    symbol: str,
    proposed_direction: str,
    evidence: Dict[str, Any],
    prior_rounds: List[Any],
    round_num: int,
) -> Dict[str, Any]:
    """Argue AGAINST the proposed trade.

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
            f"\nThe bull previously argued: {last.bull_argument}\n"
            f"Bull cited evidence: {last.bull_evidence}\n"
            f"Counter their arguments with specific evidence.\n"
        )

    evidence_summary = _summarize_evidence(evidence)

    prompt = (
        f"You are the BEAR debater for {symbol}. The council proposes: {proposed_direction.upper()}.\n\n"
        f"This is round {round_num} of the debate.\n"
        f"Available evidence:\n{evidence_summary}\n"
        f"{prior_context}\n"
        f"Your task: Argue strongly AGAINST this trade. Find every risk, contradiction, and weakness. "
        f"Cite specific evidence keys.\n\n"
        f"Return JSON: {{\n"
        f'  "argument": "Your bear case in 2-3 sentences",\n'
        f'  "evidence": ["key1", "key2"],  // blackboard keys you cite\n'
        f'  "confidence": 0.0-1.0,  // how confident in the bear case\n'
        f'  "key_risk": "The single biggest risk for this trade"\n'
        f"}}"
    )

    router = get_llm_router()
    result = await router.route(
        tier=Tier.DEEP_CORTEX,
        messages=[
            {"role": "system", "content": "You are a bear case advocate and risk detective for an algorithmic trading council. Find every flaw. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        task="bear_debate",
        temperature=0.3,
        max_tokens=1024,
    )

    if result.content:
        parsed = _parse_response(result.content)
        if parsed:
            return parsed

    return {
        "argument": f"Bear case against {symbol} {proposed_direction}: risk factors present in current market conditions.",
        "evidence": [],
        "confidence": 0.5,
    }


def _summarize_evidence(evidence: Dict[str, Any]) -> str:
    """Build a concise evidence summary from the blackboard."""
    lines = []
    perceptions = evidence.get("perceptions", {})
    for agent, data in perceptions.items():
        if isinstance(data, dict):
            direction = data.get("direction", "?")
            confidence = data.get("confidence", 0)
            reasoning = data.get("reasoning", "")[:100]
            lines.append(f"  [{agent}] {direction} ({confidence:.0%}): {reasoning}")

    hyp = evidence.get("hypothesis")
    if hyp and isinstance(hyp, dict):
        lines.append(f"  [hypothesis] {hyp.get('direction', '?')} ({hyp.get('confidence', 0):.0%}): {hyp.get('reasoning', '')[:100]}")

    strat = evidence.get("strategy")
    if strat and isinstance(strat, dict):
        lines.append(f"  [strategy] {strat.get('direction', '?')} ({strat.get('confidence', 0):.0%})")

    risk = evidence.get("risk_assessment")
    if risk and isinstance(risk, dict):
        lines.append(f"  [risk] veto={risk.get('veto', False)}: {risk.get('reasoning', '')[:100]}")

    intel = evidence.get("intelligence", {})
    for key, val in intel.items():
        if isinstance(val, dict) and "data" in val:
            lines.append(f"  [intel:{key}] {str(val.get('data', ''))[:100]}")

    return "\n".join(lines) if lines else "No evidence available."


def _parse_response(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
