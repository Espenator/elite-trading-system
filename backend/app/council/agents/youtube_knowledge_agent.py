"""YouTube Knowledge Agent — council-spawnable intelligence from video transcripts.

Reads from the YouTube knowledge store (populated by the background YouTube Agent tick)
and extracts relevant trading ideas, concepts, and symbol mentions for the target symbol.

Unlike social_perception and news_catalyst which fetch live data, this agent reads
from the pre-populated knowledge store to avoid blocking the council pipeline.

Runs in Stage 1 parallel with the other perception agents.
"""
import logging
from typing import Any, Dict, List

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "youtube_knowledge"

# Map extracted concepts to directional bias
_BULLISH_CONCEPTS = {
    "breakout", "bull flag", "double bottom", "golden cross", "momentum",
    "accumulation", "demand zone", "support", "buy signal", "long",
    "bullish divergence", "cup and handle", "ascending triangle",
}
_BEARISH_CONCEPTS = {
    "breakdown", "bear flag", "double top", "death cross",
    "distribution", "supply zone", "resistance", "sell signal", "short",
    "bearish divergence", "head and shoulders", "descending triangle",
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Read YouTube knowledge store and vote based on relevant insights."""
    cfg = get_agent_thresholds()

    knowledge = _get_relevant_knowledge(symbol)
    if not knowledge:
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning="No YouTube knowledge available (set YOUTUBE_API_KEY or wait for agent tick)",
            weight=cfg.get("weight_youtube_knowledge", 0.4),
            metadata={"data_available": False, "entries_found": 0},
        )

    # Analyze extracted ideas and concepts for directional bias
    all_ideas = []
    all_concepts = []
    for entry in knowledge:
        all_ideas.extend(entry.get("ideas", []))
        all_concepts.extend(entry.get("concepts", []))

    bull_signals = sum(1 for c in all_concepts if c.lower() in _BULLISH_CONCEPTS)
    bear_signals = sum(1 for c in all_concepts if c.lower() in _BEARISH_CONCEPTS)

    # Also check ideas for directional keywords
    for idea in all_ideas:
        idea_lower = idea.lower()
        if any(kw in idea_lower for kw in ("bullish", "buy", "long", "breakout", "rally")):
            bull_signals += 1
        elif any(kw in idea_lower for kw in ("bearish", "sell", "short", "breakdown", "crash")):
            bear_signals += 1

    total = bull_signals + bear_signals
    if total == 0:
        direction = "hold"
        confidence = 0.2
    elif bull_signals > bear_signals:
        direction = "buy"
        confidence = min(0.7, 0.35 + bull_signals * 0.05)
    elif bear_signals > bull_signals:
        direction = "sell"
        confidence = min(0.7, 0.35 + bear_signals * 0.05)
    else:
        direction = "hold"
        confidence = 0.3

    reasoning = (
        f"YouTube knowledge: {len(knowledge)} entries, "
        f"{len(all_ideas)} ideas, {len(all_concepts)} concepts, "
        f"bull/bear signals={bull_signals}/{bear_signals}"
    )

    # Write to blackboard for downstream agents
    blackboard = context.get("blackboard")
    if blackboard:
        blackboard.metadata["youtube_knowledge"] = {
            "entries_found": len(knowledge),
            "ideas_count": len(all_ideas),
            "concepts_count": len(all_concepts),
            "bull_signals": bull_signals,
            "bear_signals": bear_signals,
            "direction": direction,
        }

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        weight=cfg.get("weight_youtube_knowledge", 0.4),
        metadata={
            "data_available": True,
            "entries_found": len(knowledge),
            "ideas_count": len(all_ideas),
            "concepts_count": len(all_concepts),
            "bull_signals": bull_signals,
            "bear_signals": bear_signals,
        },
    )


def _get_relevant_knowledge(symbol: str) -> List[Dict[str, Any]]:
    """Read YouTube knowledge store and return entries mentioning this symbol.

    B3: First tries DuckDB youtube_knowledge table, then falls back to config store.
    Only returns confidence=0.1 stub if both are empty AND no YOUTUBE_API_KEY.
    """
    import os

    # Try DuckDB youtube_knowledge table first
    try:
        from app.services.duckdb_service import get_duckdb
        db = get_duckdb()
        rows = db.execute(
            "SELECT * FROM youtube_knowledge WHERE symbol = ? ORDER BY created_at DESC LIMIT 10",
            [symbol.upper()],
        ).fetchall()
        if rows:
            columns = [d[0] for d in db.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception:
        pass  # Table may not exist yet

    # Fallback: config store
    try:
        from app.services.database import db_service
        all_knowledge = db_service.get_config("youtube_knowledge") or []
        if not isinstance(all_knowledge, list):
            all_knowledge = []

        sym = symbol.upper()
        relevant = []
        for entry in all_knowledge:
            symbols_in_entry = [s.upper() for s in (entry.get("symbols") or [])]
            if sym in symbols_in_entry:
                relevant.append(entry)

        # Also return recent entries even without symbol match (general market intel)
        if not relevant:
            relevant = all_knowledge[-3:] if all_knowledge else []

        if relevant:
            return relevant[:10]
    except Exception as e:
        logger.debug("YouTube knowledge fetch failed: %s", e)

    return []
