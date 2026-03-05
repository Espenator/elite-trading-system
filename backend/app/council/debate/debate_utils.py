"""Shared utilities for debate agents — evidence summarization and JSON parsing.

Extracted from bull_debater.py and bear_debater.py to eliminate duplication.
Also provides the canonical parse_json_from_llm() used across all LLM consumers.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_json_from_llm(text: str) -> Optional[Dict]:
    """Extract JSON from an LLM response, handling markdown code blocks.

    Tries in order:
        1. Direct JSON parse of the full text
        2. Extract from ```json ... ``` code blocks
        3. Extract from ``` ... ``` code blocks
        4. Find outermost { ... } using brace depth counting

    This is the canonical implementation — use this everywhere instead
    of per-module _parse_json_safe / _parse_response copies.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed dict or None if no valid JSON found
    """
    if not text:
        return None

    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2-3. Code block extraction
    for pattern in [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
    ]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError, IndexError):
                continue

    # 4. Brace depth counting for outermost JSON object
    brace_start = text.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def summarize_evidence(evidence: Dict[str, Any]) -> str:
    """Build a concise evidence summary from the blackboard evidence package.

    Used by both bull and bear debaters, and the debate engine judge.

    Args:
        evidence: Evidence package dict with perceptions, hypothesis,
                  strategy, risk_assessment, intelligence keys

    Returns:
        Formatted multi-line string summarizing all evidence
    """
    lines: List[str] = []

    # Perceptions
    perceptions = evidence.get("perceptions", {})
    for agent, data in perceptions.items():
        if isinstance(data, dict):
            direction = data.get("direction", "?")
            confidence = data.get("confidence", 0)
            reasoning = data.get("reasoning", "")[:100]
            lines.append(f"  [{agent}] {direction} ({confidence:.0%}): {reasoning}")

    # Hypothesis
    hyp = evidence.get("hypothesis")
    if hyp and isinstance(hyp, dict):
        lines.append(
            f"  [hypothesis] {hyp.get('direction', '?')} "
            f"({hyp.get('confidence', 0):.0%}): {hyp.get('reasoning', '')[:100]}"
        )

    # Strategy
    strat = evidence.get("strategy")
    if strat and isinstance(strat, dict):
        lines.append(
            f"  [strategy] {strat.get('direction', '?')} ({strat.get('confidence', 0):.0%})"
        )

    # Risk
    risk = evidence.get("risk_assessment")
    if risk and isinstance(risk, dict):
        lines.append(f"  [risk] veto={risk.get('veto', False)}: {risk.get('reasoning', '')[:100]}")

    # Intelligence
    intel = evidence.get("intelligence", {})
    for key, val in intel.items():
        if isinstance(val, dict) and "data" in val:
            lines.append(f"  [intel:{key}] {str(val.get('data', ''))[:100]}")

    return "\n".join(lines) if lines else "No evidence available."
