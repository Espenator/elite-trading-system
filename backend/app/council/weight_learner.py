"""Weight Learner — Bayesian self-learning agent weight updater.

After each trade outcome, updates agent weights based on whether each
agent's vote aligned with the actual result.  Agents that consistently
vote correctly get higher weights; agents that are wrong get dampened.

This is the recursive self-learning loop that makes Embodier Trader
a profit-consciousness entity — the system learns from every decision.

Algorithm:
    For each agent vote in a completed trade:
        if agent_direction aligned with outcome:
            weight *= (1 + learning_rate * confidence)
        else:
            weight *= (1 - learning_rate * confidence)
    Normalize weights so mean = 1.0 (preserves relative scaling).
    Persist to DuckDB for durability across restarts.
"""
import json
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default weights for all 13 agents (+ arbiter reference)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "market_perception": 1.0,
    "flow_perception": 0.8,
    "regime": 1.2,
    "intermarket": 0.9,
    "rsi": 1.0,
    "bbv": 0.9,
    "ema_trend": 1.1,
    "relative_strength": 0.9,
    "cycle_timing": 0.8,
    "hypothesis": 0.9,
    "strategy": 1.1,
    "risk": 1.3,
    "execution": 1.0,
    "critic": 0.5,
}


class WeightLearner:
    """Bayesian weight updater for council agent weights.

    Parameters
    ----------
    learning_rate : float
        How fast weights adapt (default 0.05 = 5% per outcome).
    min_weight : float
        Floor to prevent any agent from being silenced entirely.
    max_weight : float
        Ceiling to prevent any single agent from dominating.
    decay_rate : float
        Older decisions decay toward default (prevents overfitting).
    """

    def __init__(
        self,
        learning_rate: float = 0.05,
        min_weight: float = 0.2,
        max_weight: float = 2.5,
        decay_rate: float = 0.001,
    ):
        self.learning_rate = learning_rate
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.decay_rate = decay_rate

        self._weights: Dict[str, float] = dict(DEFAULT_WEIGHTS)
        self._decision_history: List[Dict[str, Any]] = []
        self.update_count: int = 0
        self.last_update: Optional[str] = None

        # Try to load persisted weights from DuckDB
        self._load_from_store()

    def get_weights(self) -> Dict[str, float]:
        """Return current agent weights."""
        return dict(self._weights)

    def get_weight(self, agent_name: str) -> float:
        """Get weight for a specific agent."""
        return self._weights.get(agent_name, 1.0)

    def reset(self) -> None:
        """Reset all weights to defaults."""
        self._weights = dict(DEFAULT_WEIGHTS)
        self.update_count = 0
        self.last_update = None
        self._persist_to_store()
        logger.info("WeightLearner: weights reset to defaults")

    def record_decision(self, decision) -> None:
        """Record a council decision for later outcome matching.

        Called by CouncilGate after each council evaluation.
        The outcome is recorded later when the trade resolves.
        """
        record = {
            "symbol": decision.symbol,
            "timestamp": decision.timestamp,
            "final_direction": decision.final_direction,
            "final_confidence": decision.final_confidence,
            "votes": [
                {
                    "agent_name": v.agent_name,
                    "direction": v.direction,
                    "confidence": v.confidence,
                    "weight": v.weight,
                }
                for v in decision.votes
            ],
        }
        self._decision_history.append(record)
        # Keep only last 500 decisions in memory
        if len(self._decision_history) > 500:
            self._decision_history = self._decision_history[-500:]

    def update_from_outcome(
        self,
        symbol: str,
        outcome_direction: str,
        pnl: float = 0.0,
        r_multiple: float = 0.0,
    ) -> Dict[str, float]:
        """Update weights based on a trade outcome.

        Finds the most recent decision for this symbol and adjusts
        each agent's weight based on whether their vote aligned with
        the actual outcome.

        Parameters
        ----------
        symbol : str
            The ticker that resolved.
        outcome_direction : str
            "win" if profitable, "loss" if not. Or "buy"/"sell" for
            the actual direction that would have been correct.
        pnl : float
            Profit/loss amount (for magnitude-weighted learning).
        r_multiple : float
            Risk-adjusted return (for quality-weighted learning).

        Returns
        -------
        Dict[str, float]
            Updated weights after this learning step.
        """
        # Find matching decision
        matched = None
        for d in reversed(self._decision_history):
            if d["symbol"].upper() == symbol.upper():
                matched = d
                break

        if not matched:
            logger.debug(
                "WeightLearner: no decision history for %s, skipping", symbol
            )
            return self._weights

        # Determine correct direction from outcome
        if outcome_direction in ("win", "profit"):
            correct_direction = matched["final_direction"]
        elif outcome_direction in ("loss", "stop_loss"):
            # The opposite of what council decided was correct
            correct_direction = (
                "sell" if matched["final_direction"] == "buy" else "buy"
            )
        else:
            correct_direction = outcome_direction

        # Magnitude factor: larger wins/losses have more learning impact
        magnitude = 1.0
        if abs(r_multiple) > 2.0:
            magnitude = 1.5
        elif abs(r_multiple) > 1.0:
            magnitude = 1.2

        # Update each agent's weight
        adjustments = {}
        for vote in matched["votes"]:
            agent = vote["agent_name"]
            if agent not in self._weights:
                continue

            aligned = vote["direction"] == correct_direction
            confidence = vote["confidence"]
            lr = self.learning_rate * magnitude

            old_weight = self._weights[agent]
            if aligned:
                # Reward: increase weight proportional to confidence
                new_weight = old_weight * (1.0 + lr * confidence)
            else:
                # Penalize: decrease weight proportional to confidence
                new_weight = old_weight * (1.0 - lr * confidence)

            # Clamp
            new_weight = max(self.min_weight, min(self.max_weight, new_weight))
            self._weights[agent] = round(new_weight, 4)
            adjustments[agent] = {
                "old": old_weight,
                "new": new_weight,
                "aligned": aligned,
                "direction": vote["direction"],
            }

        # Normalize: keep mean weight at 1.0 to preserve arbiter math
        self._normalize_weights()

        # Apply decay toward defaults (anti-overfitting)
        self._apply_decay()

        self.update_count += 1
        from datetime import datetime, timezone
        self.last_update = datetime.now(timezone.utc).isoformat()

        # Persist
        self._persist_to_store()

        logger.info(
            "WeightLearner: updated from %s %s outcome "
            "(R=%.2f, %d agents adjusted, update #%d)",
            symbol,
            outcome_direction,
            r_multiple,
            len(adjustments),
            self.update_count,
        )

        return self._weights

    def _normalize_weights(self) -> None:
        """Normalize weights so their mean is 1.0."""
        values = list(self._weights.values())
        if not values:
            return
        mean = sum(values) / len(values)
        if mean <= 0:
            return
        for agent in self._weights:
            self._weights[agent] = round(self._weights[agent] / mean, 4)

    def _apply_decay(self) -> None:
        """Decay weights toward defaults to prevent overfitting."""
        for agent, default in DEFAULT_WEIGHTS.items():
            if agent in self._weights:
                current = self._weights[agent]
                decayed = current + self.decay_rate * (default - current)
                self._weights[agent] = round(decayed, 4)

    def _load_from_store(self) -> None:
        """Load persisted weights from DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            # Create table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_weights (
                    agent_name VARCHAR PRIMARY KEY,
                    weight DOUBLE,
                    update_count INTEGER DEFAULT 0,
                    last_update TIMESTAMP
                )
            """)
            rows = conn.execute(
                "SELECT agent_name, weight FROM agent_weights"
            ).fetchall()
            if rows:
                for name, weight in rows:
                    if name in self._weights:
                        self._weights[name] = float(weight)
                logger.info(
                    "WeightLearner: loaded %d persisted weights from DuckDB",
                    len(rows),
                )
        except Exception as e:
            logger.debug("WeightLearner: using defaults (store unavailable: %s)", e)

    def _persist_to_store(self) -> None:
        """Save current weights to DuckDB."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_weights (
                    agent_name VARCHAR PRIMARY KEY,
                    weight DOUBLE,
                    update_count INTEGER DEFAULT 0,
                    last_update TIMESTAMP
                )
            """)
            for agent, weight in self._weights.items():
                conn.execute(
                    """INSERT OR REPLACE INTO agent_weights
                       (agent_name, weight, update_count, last_update)
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                    [agent, weight, self.update_count],
                )
            logger.debug("WeightLearner: persisted %d weights", len(self._weights))
        except Exception as e:
            logger.debug("WeightLearner: persist failed: %s", e)


# Module-level singleton
_learner_instance: Optional[WeightLearner] = None


def get_weight_learner() -> WeightLearner:
    """Get or create the global WeightLearner singleton."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = WeightLearner()
    return _learner_instance
