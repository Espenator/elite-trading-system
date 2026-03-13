"""Council Feedback Loop — closes the learning cycle.

Records council decisions alongside trade outcomes, then adjusts agent
weights based on which agents were correct/incorrect over a rolling window.

Flow:
  1. record_decision() — called after every council evaluation
  2. record_outcome() — called when a trade's P&L is resolved
  3. update_agent_weights() — recomputes weights from accuracy history
  4. get_agent_performance() — returns per-agent accuracy stats

Decision store: in-memory rolling window (500) for speed; DuckDB council_decisions
is the canonical full history so outcomes can match decisions from long-lived trades.
"""
import json
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

MAX_DECISIONS = 500  # Rolling window (DuckDB has full history for fallback)


def _get_decision_from_duckdb(trade_id: Optional[str], symbol: str) -> Optional[Dict[str, Any]]:
    """Look up a council decision from DuckDB (canonical store). Used when in-memory list truncated."""
    if not trade_id and not (symbol and symbol.strip()):
        return None
    try:
        from app.data.duckdb_storage import duckdb_store
        cur = duckdb_store.get_thread_cursor()
        row = None
        if trade_id:
            cur.execute(
                "SELECT * FROM council_decisions WHERE decision_id = ? LIMIT 1",
                [trade_id],
            )
            row = cur.fetchone()
        if not row and symbol and symbol.strip():
            cur.execute(
                "SELECT * FROM council_decisions WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                [symbol.strip().upper()],
            )
            row = cur.fetchone()
        if not row or not cur.description:
            return None
        cols = [d[0] for d in cur.description]
        raw = dict(zip(cols, row))
        agent_votes_raw = raw.get("agent_votes")
        votes = []
        if agent_votes_raw:
            try:
                parsed = json.loads(agent_votes_raw) if isinstance(agent_votes_raw, str) else agent_votes_raw
                for v in parsed:
                    votes.append({
                        "agent": v.get("agent", v.get("agent_name", "")),
                        "direction": v.get("vote", v.get("direction", "hold")),
                        "confidence": v.get("confidence", 0.5),
                    })
            except (TypeError, ValueError):
                pass
        return {
            "symbol": (raw.get("symbol") or symbol or "").upper(),
            "timestamp": raw.get("timestamp"),
            "final_direction": raw.get("final_verdict", raw.get("final_direction", "hold")),
            "trade_id": raw.get("decision_id"),
            "votes": votes,
        }
    except Exception as e:
        logger.debug("Feedback loop: DuckDB decision lookup failed: %s", e)
        return None


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
    council_decision_id: Optional[str] = None,
) -> None:
    """Record a council decision for later feedback matching.

    Args:
        symbol: Ticker symbol
        final_direction: Council's final direction ("buy"/"sell"/"hold")
        votes: List of vote dicts with {agent_name, direction, confidence, weight}
        trade_id: Optional trade ID for matching to outcome
        council_decision_id: Council decision ID for LLM calibration outcome matching
    """
    store = _get_store()
    decisions = store.get("decisions", [])

    decision_record = {
        "symbol": symbol.upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_direction": final_direction,
        "trade_id": trade_id,
        "council_decision_id": council_decision_id,
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

    # Find the matching decision: in-memory first, then DuckDB (full history)
    decisions = store.get("decisions", [])
    matching = None
    for d in reversed(decisions):
        if trade_id and d.get("trade_id") == trade_id:
            matching = d
            break
    if not matching and not trade_id:
        for d in reversed(decisions):
            if d.get("symbol") == symbol.upper() and d.get("final_direction") != "hold":
                matching = d
                break
    if not matching:
        matching = _get_decision_from_duckdb(trade_id, symbol)

    if matching:
        _update_agent_stats(store, matching, outcome)
        # LLM calibration: match outcome to hypothesis prediction and update tier accuracy
        try:
            from app.services.llm_calibration import record_llm_outcome
            record_llm_outcome(
                trade_id=trade_id,
                council_decision_id=matching.get("council_decision_id"),
                symbol=symbol.upper(),
                outcome_direction=outcome,
                r_multiple=r_multiple,
            )
        except Exception as e:
            logger.debug("LLM calibration record_llm_outcome failed: %s", e)
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


def update_agent_weights(
    outcome: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Update agent weights via WeightLearner using the latest outcome.

    When an outcome dict is provided (from record_outcome), finds the
    matching council decision and calls WeightLearner.update_from_outcome()
    so Bayesian weight updates actually fire.

    Falls back to returning current weights if no outcome is provided
    or if the matching decision can't be found.

    Returns:
        Dict of {agent_name: weight}
    """
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()

        # If we have outcome data, actually fire the learning update
        if outcome:
            symbol = outcome.get("symbol", "UNKNOWN")
            trade_id = outcome.get("trade_id", "")
            r_multiple = outcome.get("r_multiple", 0.0)
            pnl = outcome.get("pnl", outcome.get("profit", 0.0))
            is_win = outcome.get("outcome", "") == "win" or pnl > 0

            outcome_direction = "win" if is_win else "loss"
            confidence = outcome.get("confidence", 1.0)

            try:
                updated = learner.update_from_outcome(
                    symbol=symbol,
                    outcome_direction=outcome_direction,
                    pnl=pnl,
                    r_multiple=r_multiple,
                    confidence=confidence,
                    trade_id=trade_id,
                    outcome_id=trade_id,
                )
                logger.info(
                    "WEIGHT UPDATE: %s %s (pnl=%.2f, R=%.2f). "
                    "Updated %d agent weights via WeightLearner.",
                    symbol, outcome_direction, pnl, r_multiple, len(updated),
                )
                return updated
            except Exception as learn_err:
                logger.warning(
                    "WeightLearner update_from_outcome failed for %s: %s",
                    symbol, learn_err,
                )

        # No outcome or learning failed — return current weights
        weights = learner.get_weights()
        logger.info(
            "Feedback loop: returning current weights (%d agents, %d updates)",
            len(weights), learner.update_count,
        )
        return weights
    except Exception as e:
        logger.warning("WeightLearner unavailable, returning empty: %s", e)
        return {}


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
