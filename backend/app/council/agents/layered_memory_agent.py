"""Layered Memory (FinMem) Agent — self-evolving memory for pattern recognition.

P3 Academic Edge Agent. Implements three-layer memory architecture for
cognitive pattern recognition across trading history.

Academic basis: FinMEM architecture with short/mid/long-term layers plus
reflection improves adaptability. Aligns with cognitive structure of
human traders — adjustable cognitive span enables pattern recognition
across months of trading history.

Memory layers:
- Short-Term: Last 20 trades for current ticker, decays after 5 trading days
- Mid-Term: Sector-level patterns over past quarter
- Long-Term: Historical regime transitions and their outcomes
- Reflection: Meta-analysis of agent's own performance

Council integration: Enhancement to hypothesis_agent via brain_service.
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "layered_memory_agent"

# Memory decay parameters
_SHORT_TERM_TRADES = 20
_SHORT_TERM_DECAY_DAYS = 5
_MID_TERM_DAYS = 90
_LONG_TERM_DAYS = 365

# In-memory storage (production would use DuckDB)
_memory_store: Dict[str, Any] = {
    "short_term": defaultdict(list),   # ticker -> [trade_records]
    "mid_term": defaultdict(dict),     # sector -> pattern_data
    "long_term": defaultdict(dict),    # regime_transition -> outcome_data
    "reflection": defaultdict(dict),   # agent_name -> performance_data
}


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Provide memory-enriched context for the hypothesis agent."""
    cfg = get_agent_thresholds()
    f = features.get("features", features)
    blackboard = context.get("blackboard")

    # Load memories from DuckDB / internal store
    short_term = await _recall_short_term(symbol)
    mid_term = await _recall_mid_term(symbol, f)
    long_term = await _recall_long_term(f)
    reflection = await _recall_reflection()

    # Compute memory-based signals
    pattern_signal = _analyze_patterns(short_term, mid_term, long_term)
    reflection_adjustment = _apply_reflection(reflection, f)

    # Write to blackboard
    if blackboard:
        blackboard.layered_memory.update({
            "short_term": short_term[:_SHORT_TERM_TRADES],
            "mid_term": mid_term,
            "long_term": long_term,
            "reflection": reflection,
            "cognitive_span_days": _MID_TERM_DAYS,
        })

    # Generate vote based on memory patterns
    direction, confidence = _memory_to_vote(
        pattern_signal, reflection_adjustment, cfg,
    )

    reasoning_parts = [
        f"Short-term: {len(short_term)} trades recalled",
    ]
    if mid_term:
        sector = f.get("sector", "unknown")
        reasoning_parts.append(f"Mid-term: sector={sector} pattern available")
    if long_term:
        reasoning_parts.append(f"Long-term: {len(long_term)} regime transitions")
    if reflection:
        win_rate = reflection.get("overall_win_rate", 0)
        reasoning_parts.append(f"Reflection: win_rate={win_rate:.0%}")
    if pattern_signal:
        reasoning_parts.append(f"Pattern signal={pattern_signal.get('direction', 'neutral')}")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(confidence, 2),
        reasoning=", ".join(reasoning_parts),
        weight=cfg.get("weight_layered_memory_agent", 0.6),
        metadata={
            "data_available": True,
            "short_term_count": len(short_term),
            "mid_term_available": bool(mid_term),
            "long_term_transitions": len(long_term) if isinstance(long_term, dict) else 0,
            "pattern_signal": pattern_signal,
            "reflection_adjustment": reflection_adjustment,
        },
    )


def _memory_to_vote(
    pattern: Optional[Dict], reflection_adj: float, cfg: Dict,
) -> Tuple[str, float]:
    """Convert memory patterns to vote."""
    if not pattern:
        return "hold", 0.3

    direction = pattern.get("direction", "hold")
    confidence = pattern.get("confidence", 0.4)

    # Apply reflection adjustment
    confidence *= (1 + reflection_adj)
    confidence = max(0.1, min(0.85, confidence))

    return direction, confidence


async def _recall_short_term(symbol: str) -> List[Dict[str, Any]]:
    """Recall last 20 trades for the current ticker (in-memory store)."""
    trades = _memory_store["short_term"].get(symbol, [])

    # Apply decay (remove trades older than 5 trading days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=_SHORT_TERM_DECAY_DAYS)
    active = []
    for t in trades:
        trade_date = t.get("timestamp")
        if trade_date:
            try:
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date.replace("Z", "+00:00"))
                if trade_date > cutoff:
                    active.append(t)
            except Exception:
                active.append(t)
        else:
            active.append(t)

    return active[-_SHORT_TERM_TRADES:]


async def _recall_mid_term(symbol: str, features: Dict) -> Dict[str, Any]:
    """Recall sector-level patterns over past quarter (in-memory store)."""
    sector = str(features.get("sector", "unknown"))
    return _memory_store["mid_term"].get(sector, {})


async def _recall_long_term(features: Dict) -> Dict[str, Any]:
    """Recall historical regime transitions and their outcomes (in-memory store)."""
    regime = str(features.get("regime", "unknown")).lower()
    return _memory_store["long_term"].get(regime, {})


async def _recall_reflection() -> Dict[str, Any]:
    """Meta-analysis of agent's own performance (in-memory store)."""
    return _memory_store["reflection"].get("overall", {})


def _compute_reflection(performance: List[Dict]) -> Dict[str, Any]:
    """Compute reflection metrics from historical performance."""
    if not performance:
        return {}

    total_trades = len(performance)
    wins = sum(1 for p in performance if float(p.get("pnl", 0)) > 0)
    losses = total_trades - wins

    # Compute win rate by regime
    regime_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "total": 0})
    for p in performance:
        regime = str(p.get("regime", "unknown")).lower()
        regime_stats[regime]["total"] += 1
        if float(p.get("pnl", 0)) > 0:
            regime_stats[regime]["wins"] += 1

    regime_win_rates = {}
    for regime, stats in regime_stats.items():
        if stats["total"] > 0:
            regime_win_rates[regime] = round(stats["wins"] / stats["total"], 3)

    # Compute win rate by direction
    direction_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "total": 0})
    for p in performance:
        direction = str(p.get("direction", "unknown"))
        direction_stats[direction]["total"] += 1
        if float(p.get("pnl", 0)) > 0:
            direction_stats[direction]["wins"] += 1

    direction_win_rates = {}
    for direction, stats in direction_stats.items():
        if stats["total"] > 0:
            direction_win_rates[direction] = round(stats["wins"] / stats["total"], 3)

    return {
        "overall_win_rate": round(wins / max(1, total_trades), 3),
        "total_trades": total_trades,
        "regime_win_rates": regime_win_rates,
        "direction_win_rates": direction_win_rates,
    }


def _analyze_patterns(
    short_term: List[Dict], mid_term: Dict, long_term: Dict,
) -> Optional[Dict[str, Any]]:
    """Analyze memory patterns for trading signals."""
    if not short_term and not mid_term:
        return None

    signal: Dict[str, Any] = {"direction": "hold", "confidence": 0.4, "sources": []}

    # Short-term pattern: recent win/loss streak
    if short_term:
        recent_wins = sum(1 for t in short_term[-5:] if float(t.get("pnl", 0)) > 0)
        recent_total = min(5, len(short_term))

        if recent_total > 0:
            recent_win_rate = recent_wins / recent_total
            # Strong recent performance increases confidence
            if recent_win_rate >= 0.8:
                signal["confidence"] = min(0.7, signal["confidence"] + 0.15)
                signal["sources"].append("strong_recent_streak")
            elif recent_win_rate <= 0.2:
                signal["confidence"] = max(0.2, signal["confidence"] - 0.15)
                signal["sources"].append("poor_recent_streak")

        # Most common recent direction
        directions = [t.get("direction", "hold") for t in short_term[-5:]]
        if directions:
            buy_count = directions.count("buy")
            sell_count = directions.count("sell")
            if buy_count > sell_count:
                signal["direction"] = "buy"
            elif sell_count > buy_count:
                signal["direction"] = "sell"

    # Mid-term pattern: sector behavior
    if mid_term:
        sector_bias = mid_term.get("bias", "neutral")
        sector_strength = float(mid_term.get("strength", 0))
        if sector_bias in ("bullish", "buy") and sector_strength > 0.5:
            signal["direction"] = "buy"
            signal["confidence"] = min(0.7, signal["confidence"] + 0.1)
            signal["sources"].append("sector_momentum")
        elif sector_bias in ("bearish", "sell") and sector_strength > 0.5:
            signal["direction"] = "sell"
            signal["confidence"] = min(0.7, signal["confidence"] + 0.1)
            signal["sources"].append("sector_weakness")

    # Long-term pattern: regime transition history
    if long_term:
        transition_outcome = long_term.get("avg_outcome", 0)
        if transition_outcome > 0.02:
            signal["confidence"] = min(0.75, signal["confidence"] + 0.05)
            signal["sources"].append("favorable_regime_history")
        elif transition_outcome < -0.02:
            signal["confidence"] = max(0.2, signal["confidence"] - 0.05)
            signal["sources"].append("unfavorable_regime_history")

    return signal


def _apply_reflection(reflection: Dict, features: Dict) -> float:
    """Apply reflection-based confidence adjustment.

    If the agent has historically performed poorly in the current regime,
    reduce confidence. If well, increase slightly.
    """
    if not reflection:
        return 0.0

    regime = str(features.get("regime", "unknown")).lower()
    regime_win_rates = reflection.get("regime_win_rates", {})

    current_regime_wr = regime_win_rates.get(regime)
    if current_regime_wr is None:
        return 0.0

    # Adjust confidence based on historical performance in this regime
    # Win rate 50% = neutral, >60% = boost, <40% = reduce
    if current_regime_wr > 0.6:
        return 0.1
    elif current_regime_wr < 0.4:
        return -0.15
    return 0.0


def store_trade_outcome(
    symbol: str, direction: str, pnl: float,
    regime: str, timestamp: Optional[datetime] = None,
):
    """Store a trade outcome in memory for future pattern recognition.

    Called by the execution pipeline after trade completion.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    trade = {
        "symbol": symbol,
        "direction": direction,
        "pnl": pnl,
        "regime": regime,
        "timestamp": timestamp.isoformat(),
    }

    # Short-term memory
    _memory_store["short_term"][symbol].append(trade)
    if len(_memory_store["short_term"][symbol]) > _SHORT_TERM_TRADES * 2:
        _memory_store["short_term"][symbol] = _memory_store["short_term"][symbol][-_SHORT_TERM_TRADES:]

    # Reflection update
    overall = _memory_store["reflection"].get("overall", {"wins": 0, "total": 0})
    overall["total"] = overall.get("total", 0) + 1
    if pnl > 0:
        overall["wins"] = overall.get("wins", 0) + 1
    overall["overall_win_rate"] = round(overall["wins"] / max(1, overall["total"]), 3)
    _memory_store["reflection"]["overall"] = overall
