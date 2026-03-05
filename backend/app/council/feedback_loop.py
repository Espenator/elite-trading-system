"""Council Feedback Loop — closes the learning cycle.

Records council decisions alongside trade outcomes, then adjusts agent
weights based on which agents were correct/incorrect over a rolling window.

Flow:
  1. record_decision() — called after every council evaluation
  2. record_outcome() — called when a trade's P&L is resolved
  3. update_agent_weights() — recomputes weights from accuracy history
  4. get_agent_performance() — returns per-agent accuracy stats

The feedback loop updates the 'council' settings category in the settings
service, so weight changes persist and take effect on the next evaluation.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY = "council_feedback"
# Shape: {
#   "decisions": [{ symbol, timestamp, final_direction, votes: [{agent, direction, confidence}], trade_id }],
#   "outcomes": [{ trade_id, symbol, outcome: "win"|"loss"|"scratch", r_multiple, resolved_at }],
#   "agent_stats": { agent_name: { correct: N, incorrect: N, total: N, accuracy: float } },
# }

MAX_DECISIONS = 500  # Rolling window


def _get_store() -> Dict[str, Any]:
    return db_service.get_config(CONFIG_KEY) or {
        "decisions": [],
        "outcomes": [],
        "agent_stats": {},
    }


def _save_store(store: Dict[str, Any]) -> None:
    db_service.set_config(CONFIG_KEY, store)


def record_decision(
    symbol: str,
    final_direction: str,
    votes: List[Dict[str, Any]],
    trade_id: Optional[str] = None,
) -> None:
    """Record a council decision for later feedback matching.

    Args:
        symbol: Ticker symbol
        final_direction: Council's final direction ("buy"/"sell"/"hold")
        votes: List of vote dicts with {agent_name, direction, confidence, weight}
        trade_id: Optional trade ID for matching to outcome
    """
    store = _get_store()
    decisions = store.get("decisions", [])

    decision_record = {
        "symbol": symbol.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_direction": final_direction,
        "trade_id": trade_id,
        "votes": [
            {
                "agent": v.get("agent_name", v.get("agent", "")),
                "direction": v.get("direction", "hold"),
                "confidence": v.get("confidence", 0),
            }
            for v in votes
        ],
    }

    decisions.append(decision_record)
    # Keep rolling window
    store["decisions"] = decisions[-MAX_DECISIONS:]
    _save_store(store)
    logger.debug("Recorded council decision for %s: %s", symbol, final_direction)


def record_outcome(
    trade_id: str,
    symbol: str,
    outcome: str,
    r_multiple: float = 0.0,
) -> Dict[str, Any]:
    """Record a trade outcome and update agent accuracy stats.

    Args:
        trade_id: Unique trade identifier
        symbol: Ticker symbol
        outcome: "win", "loss", or "scratch"
        r_multiple: Risk-adjusted return (>0 = win, <0 = loss)

    Returns:
        Updated agent performance stats
    """
    store = _get_store()
    outcomes = store.get("outcomes", [])

    outcomes.append({
        "trade_id": trade_id,
        "symbol": symbol.upper(),
        "outcome": outcome,
        "r_multiple": r_multiple,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    })
    store["outcomes"] = outcomes[-MAX_DECISIONS:]

    # Find the matching decision — prefer exact trade_id match
    decisions = store.get("decisions", [])
    matching = None
    for d in reversed(decisions):
        if trade_id and d.get("trade_id") == trade_id:
            matching = d
            break
    # Fallback: match by symbol only if no trade_id provided
    if not matching and not trade_id:
        for d in reversed(decisions):
            if d.get("symbol") == symbol.upper() and d.get("final_direction") != "hold":
                matching = d
                break

    if matching:
        _update_agent_stats(store, matching, outcome)
        logger.info(
            "Feedback loop: %s %s -> %s (R=%.2f). Agent stats updated.",
            symbol, matching["final_direction"], outcome, r_multiple,
        )
    else:
        logger.warning("Feedback loop: no matching decision for trade_id=%s", trade_id)

    _save_store(store)
    return get_agent_performance()


def _update_agent_stats(
    store: Dict[str, Any],
    decision: Dict[str, Any],
    outcome: str,
) -> None:
    """Update per-agent accuracy based on whether their vote aligned with outcome."""
    stats = store.get("agent_stats", {})
    final_direction = decision["final_direction"]

    # Determine what the "correct" direction was
    if outcome == "win":
        correct_direction = final_direction  # The council was right
    elif outcome == "loss":
        # The opposite would have been correct
        correct_direction = "sell" if final_direction == "buy" else "buy"
    else:  # scratch
        correct_direction = "hold"

    for vote in decision.get("votes", []):
        agent = vote["agent"]
        if agent not in stats:
            stats[agent] = {"correct": 0, "incorrect": 0, "total": 0, "accuracy": 0.5}

        stats[agent]["total"] += 1
        if vote["direction"] == correct_direction:
            stats[agent]["correct"] += 1
        else:
            stats[agent]["incorrect"] += 1

        total = stats[agent]["total"]
        if total > 0:
            stats[agent]["accuracy"] = round(stats[agent]["correct"] / total, 4)

    store["agent_stats"] = stats


def update_agent_weights() -> Dict[str, float]:
    """Recompute agent weights from accuracy history and persist to settings.

    Weight adjustment formula:
      new_weight = base_weight * (0.5 + accuracy)

    This means:
      - 50% accuracy (random) -> weight stays at base * 1.0
      - 70% accuracy -> weight becomes base * 1.2
      - 30% accuracy -> weight becomes base * 0.8
      - Minimum 10 decisions before adjusting

    Returns:
        Dict of {agent_name: new_weight}
    """
    store = _get_store()
    stats = store.get("agent_stats", {})

    # Need minimum sample size before adjusting
    MIN_DECISIONS = 10

    from app.council.agent_config import get_agent_thresholds, _DEFAULTS
    current_cfg = get_agent_thresholds()
    new_weights = {}

    for agent_name, agent_stats in stats.items():
        weight_key = f"weight_{agent_name}"
        base_weight = _DEFAULTS.get(weight_key, 1.0)

        if agent_stats["total"] < MIN_DECISIONS:
            new_weights[weight_key] = base_weight
            continue

        accuracy = agent_stats["accuracy"]
        # Scale: 0.5 + accuracy maps [0,1] -> [0.5, 1.5] multiplier
        multiplier = 0.5 + accuracy
        new_weight = round(base_weight * multiplier, 2)
        # Clamp to [0.1, 3.0] to prevent extreme weights
        new_weight = max(0.1, min(3.0, new_weight))
        new_weights[weight_key] = new_weight

    # Persist to settings service
    if new_weights:
        try:
            from app.services.settings_service import update_settings_by_category
            update_settings_by_category("council", new_weights)
            logger.info("Feedback loop: updated agent weights: %s", new_weights)
        except Exception as e:
            logger.warning("Feedback loop: failed to persist weights: %s", e)

    return new_weights


def get_agent_performance() -> Dict[str, Any]:
    """Return per-agent accuracy stats for the dashboard."""
    store = _get_store()
    stats = store.get("agent_stats", {})
    decisions_count = len(store.get("decisions", []))
    outcomes_count = len(store.get("outcomes", []))

    return {
        "agent_stats": stats,
        "total_decisions": decisions_count,
        "total_outcomes": outcomes_count,
        "feedback_active": outcomes_count >= 10,
    }


def reset_feedback() -> None:
    """Reset all feedback data (for testing or fresh start)."""
    _save_store({
        "decisions": [],
        "outcomes": [],
        "agent_stats": {},
    })
    logger.info("Feedback loop: reset all data")
