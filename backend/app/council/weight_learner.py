"""Weight Learner — Bayesian self-learning agent weight updater.

After each trade outcome, updates agent weights based on whether each
agent's vote aligned with the actual result.  Agents that consistently
vote correctly get higher weights; agents that are wrong get dampened.

This is the recursive self-learning loop that makes Embodier Trader
a profit-consciousness entity — the system learns from every decision.

Key methods: get_weights() (used by arbiter), update_from_outcome() (feedback_loop),
get_decision_by_trade_id() (postmortem context), _load_from_store()/_persist_to_store() (DuckDB).
Regime-stratified weights per (agent, regime) for regime-adaptive learning.

Algorithm:
    For each agent vote in a completed trade:
        if agent_direction aligned with outcome:
            weight *= (1 + learning_rate * confidence)
        else:
            weight *= (1 - learning_rate * confidence)
    Clamp to [min_weight, max_weight] (default 0.2–2.5). Normalize mean = 1.0.
    Persist to DuckDB for durability across restarts.

Decay/reset rules (explainable, bounded):
    - _apply_decay(): after each update, weights decay toward DEFAULT_WEIGHTS by decay_rate
      (default 0.005) to limit overfitting to recent outcomes.
    - reset(): restores all weights to DEFAULT_WEIGHTS and persists (auditable).
    - Arbiter consumes get_weights() only; behavior remains deterministic and auditable.

Input quality gates (STRICT_LEARNER_INPUTS): required attribution, confidence
threshold, invalid/censored filtered; dropped inputs are audited and metrics emitted.
"""
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum confidence (0–1) for an outcome to be used for learning when STRICT_LEARNER_INPUTS is True
# Phase C: Lowered from 0.35 to 0.20 to retain 80%+ of outcomes for learning
LEARNER_MIN_CONFIDENCE = 0.20

# Default weights for all agents (core + academic edge agents)
DEFAULT_WEIGHTS: Dict[str, float] = {
    # ── Core Council Agents ──────────────────────────────────────────
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
    # Phase 2: Debate + Red Team agents
    "bull_debater": 0.7,
    "bear_debater": 0.7,
    "red_team": 0.8,
    # ── Academic Edge Agents (P2) ────────────────────────────────────
    "dark_pool_agent": 0.9,
    "congressional_agent": 0.7,
    "insider_agent": 0.8,
    "earnings_tone_agent": 0.8,
    "gex_agent": 0.85,
    "news_catalyst_agent": 0.8,
    "portfolio_optimizer_agent": 0.9,
    "institutional_flow_agent": 0.8,
    "macro_regime_agent": 0.9,
    "layered_memory_agent": 0.7,
    "market_perception_agent": 0.8,
    "finbert_sentiment_agent": 0.75,
    "alt_data_agent": 0.7,
    "social_perception_agent": 0.7,
    "supply_chain_agent": 0.7,
    "youtube_knowledge_agent": 0.6,
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

    # Minimum weight contribution to be included in learning (avoid noise from near-zero influence)
    MIN_CONTRIBUTION_WEIGHT = 0.05

    def __init__(
        self,
        learning_rate: float = 0.05,
        min_weight: float = 0.2,
        max_weight: float = 2.5,
        decay_rate: float = 0.005,  # Phase C: increased from 0.001 for faster regime adaptation
    ):
        self.learning_rate = learning_rate
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.decay_rate = decay_rate

        self._weights: Dict[str, float] = dict(DEFAULT_WEIGHTS)
        # Phase C: Regime-stratified weights — separate Beta(α,β) per regime
        # key = (agent_name, regime) -> {"alpha": float, "beta": float}
        self._regime_weights: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {"alpha": 2.0, "beta": 2.0})
        )
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
        """Record a council decision for later outcome matching and postmortem.

        Called by CouncilGate after each council evaluation.
        The outcome is recorded later when the trade resolves.
        Phase C: records trade_id and regime for proper attribution.
        Stores blackboard_snapshot when present for postmortem write on close.
        """
        # Phase C: Use council_decision_id as trade_id for unique matching (DecisionPacket has council_decision_id)
        trade_id = getattr(decision, "council_decision_id", "") or getattr(decision, "decision_id", "") or ""
        if not trade_id:
            # Fallback: generate from symbol + timestamp
            trade_id = f"{decision.symbol}:{decision.timestamp}"

        record = {
            "trade_id": trade_id,
            "symbol": decision.symbol,
            "timestamp": decision.timestamp,
            "final_direction": decision.final_direction,
            "final_confidence": decision.final_confidence,
            "regime": getattr(decision, "regime", "UNKNOWN") or "UNKNOWN",
            "votes": [
                {
                    "agent_name": v.agent_name,
                    "direction": v.direction,
                    "confidence": v.confidence,
                    "weight": v.weight,
                }
                for v in decision.votes
            ],
            "blackboard_snapshot": getattr(decision, "blackboard_snapshot", None),
        }
        self._decision_history.append(record)
        # Keep only last 500 decisions in memory
        if len(self._decision_history) > 500:
            self._decision_history = self._decision_history[-500:]

    def get_decision_by_trade_id(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent decision record matching trade_id for postmortem.

        Used by OutcomeTracker when a position resolves to build postmortem context.
        """
        if not trade_id:
            return None
        for d in reversed(self._decision_history):
            if d.get("trade_id") == trade_id:
                return d
        return None

    def _validate_learner_input(
        self,
        symbol: str,
        outcome_direction: str,
        is_censored: bool,
        confidence: float = 1.0,
        outcome_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Validate learner input when STRICT_LEARNER_INPUTS is True.

        Returns (accepted: bool, reason: str). Reason is used for audit and metrics.
        """
        try:
            from app.core.config import settings
            strict = getattr(settings, "STRICT_LEARNER_INPUTS", True)
        except Exception:
            strict = True

        if not strict:
            return True, "ok"

        if is_censored:
            return False, "censored"
        if not symbol or not symbol.strip():
            return False, "missing_symbol"
        if outcome_direction not in ("win", "loss", "profit", "stop_loss", "buy", "sell"):
            return False, "invalid_outcome_direction"
        if confidence < LEARNER_MIN_CONFIDENCE:
            return False, "low_confidence"
        return True, "ok"

    def get_regime_weight(self, agent_name: str, regime: str) -> float:
        """Get regime-stratified weight for an agent (Phase C).

        Returns the Beta distribution mean for the agent in the given regime.
        Falls back to the global weight if no regime data available.
        """
        if regime and agent_name in self._regime_weights:
            rw = self._regime_weights[agent_name].get(regime)
            if rw and (rw["alpha"] + rw["beta"]) > 4.0:  # Enough data
                return rw["alpha"] / (rw["alpha"] + rw["beta"])
        return self._weights.get(agent_name, 1.0)

    def update_from_outcome(
        self,
        symbol: str,
        outcome_direction: str,
        pnl: float = 0.0,
        r_multiple: float = 0.0,
        debate_quality_score: float = 0.0,
        red_team_score: float = 0.0,
        regime_entropy: float = 0.0,
        debate_winner: str = "",
        red_team_recommendation: str = "",
        is_censored: bool = False,
        confidence: float = 1.0,
        outcome_id: Optional[str] = None,
        trade_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """Update weights based on a trade outcome.

        Requires is_censored=False; censored outcomes must not change weights.
        When STRICT_LEARNER_INPUTS is True, validates attribution and confidence;
        dropped inputs are audited and learner_input_total{status,reason} emitted.

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
        debate_quality_score : float
            Quality score from the debate engine (0.0-1.0).
        red_team_score : float
            Fraction of scenarios survived by the trade.
        regime_entropy : float
            Shannon entropy of the regime belief distribution.
        debate_winner : str
            "bull", "bear", or "contested" from the debate.
        red_team_recommendation : str
            "PROCEED", "REDUCE_SIZE", or "REJECT".
        is_censored : bool
            If True, do not update weights (outcome not usable for learning).
        confidence : float
            Quality/confidence of the outcome (0–1). Used when STRICT_LEARNER_INPUTS.
        outcome_id : Optional[str]
            Optional outcome/trade ID for provenance.

        Returns
        -------
        Dict[str, float]
            Updated weights after this learning step.
        """
        accepted, reason = self._validate_learner_input(
            symbol, outcome_direction, is_censored, confidence, outcome_id
        )
        try:
            from app.core.metrics import counter_inc
            counter_inc("learner_input_total", {"status": "accepted" if accepted else "dropped", "reason": reason})
        except Exception:
            pass

        if not accepted:
            self._audit_dropped_input(symbol, outcome_direction, reason, outcome_id)
            logger.debug(
                "WeightLearner: input dropped symbol=%s reason=%s",
                symbol, reason,
            )
            return self._weights

        logger.info(
            "[LEARNING-TRACE] WeightLearner.update_from_outcome accepted symbol=%s outcome_id=%s",
            symbol, outcome_id,
        )
        if is_censored:
            logger.debug("WeightLearner: outcome censored, skipping weight update for %s", symbol)
            return self._weights

        # Phase C: Match by trade_id first (unique), then outcome_id, fall back to symbol match
        matched = None
        if trade_id:
            for d in reversed(self._decision_history):
                if d.get("trade_id") == trade_id:
                    matched = d
                    break
        if not matched and outcome_id:
            # Callers may pass trade_id as outcome_id — check both fields
            for d in reversed(self._decision_history):
                if d.get("trade_id") == outcome_id or d.get("outcome_id") == outcome_id:
                    matched = d
                    break
        if not matched:
            sym_upper = symbol.strip().upper()
            for d in reversed(self._decision_history):
                if d["symbol"].strip().upper() == sym_upper:
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

        # Phase C: Use regime at trade entry time (not current regime)
        entry_regime = matched.get("regime", "UNKNOWN")

        # Magnitude factor: larger wins/losses have more learning impact
        magnitude = 1.0
        if abs(r_multiple) > 2.0:
            magnitude = 1.5
        elif abs(r_multiple) > 1.0:
            magnitude = 1.2

        # Update each agent's weight (only agents with non-trivial influence)
        adjustments = {}
        for vote in matched["votes"]:
            agent = vote["agent_name"]
            if agent not in self._weights:
                continue
            weight_used = vote.get("weight", self._weights.get(agent, 1.0))
            if weight_used < self.MIN_CONTRIBUTION_WEIGHT:
                continue  # Skip agents with negligible contribution

            aligned = vote["direction"] == correct_direction
            vote_confidence = vote["confidence"]
            lr = self.learning_rate * magnitude

            old_weight = self._weights[agent]
            if aligned:
                # Reward: increase weight proportional to confidence
                new_weight = old_weight * (1.0 + lr * vote_confidence)
            else:
                # Phase C: Symmetric penalty — penalize as strongly as reward
                # (Previously biased toward positive boost)
                new_weight = old_weight * (1.0 - lr * vote_confidence)

            # Clamp
            new_weight = max(self.min_weight, min(self.max_weight, new_weight))
            self._weights[agent] = round(new_weight, 4)
            adjustments[agent] = {
                "old": old_weight,
                "new": new_weight,
                "aligned": aligned,
                "direction": vote["direction"],
            }

            # Phase C: Update regime-stratified Beta(α,β) distribution
            if entry_regime and entry_regime != "UNKNOWN":
                rw = self._regime_weights[agent][entry_regime]
                if aligned:
                    rw["alpha"] += 1.0 * magnitude
                else:
                    rw["beta"] += 1.0 * magnitude

        # ── Auxiliary learning from debate + red team ─────────────────────
        # If bear correctly predicted loss → increase bear debater weight
        if debate_winner == "bear" and outcome_direction in ("loss", "stop_loss"):
            if "bear_debater" not in self._weights:
                self._weights["bear_debater"] = 1.0
            self._weights["bear_debater"] *= (1.0 + self.learning_rate * 0.5)
            self._weights["bear_debater"] = min(self.max_weight, self._weights["bear_debater"])

        # If trade won despite strong bear case → only reduce bear weight if evidence was low
        if debate_winner == "bear" and outcome_direction in ("win", "profit"):
            if debate_quality_score < 0.5 and "bear_debater" in self._weights:
                self._weights["bear_debater"] *= (1.0 - self.learning_rate * 0.3)
                self._weights["bear_debater"] = max(self.min_weight, self._weights["bear_debater"])

        # If red team flagged fragility and trade lost → penalize strategy/risk agents
        if red_team_recommendation in ("REJECT", "REDUCE_SIZE") and outcome_direction in ("loss", "stop_loss"):
            for agent in ("strategy", "risk"):
                if agent in self._weights:
                    self._weights[agent] *= (1.0 - self.learning_rate * 0.3)
                    self._weights[agent] = max(self.min_weight, self._weights[agent])
            # Boost red team weight
            if "red_team" not in self._weights:
                self._weights["red_team"] = 1.0
            self._weights["red_team"] *= (1.0 + self.learning_rate * 0.5)
            self._weights["red_team"] = min(self.max_weight, self._weights["red_team"])

        # High regime entropy + loss → regime agent needs improvement
        if regime_entropy > 1.2 and outcome_direction in ("loss", "stop_loss"):
            if "regime" in self._weights:
                self._weights["regime"] *= (1.0 - self.learning_rate * 0.2)
                self._weights["regime"] = max(self.min_weight, self._weights["regime"])

        # Normalize: keep mean weight at 1.0 to preserve arbiter math
        self._normalize_weights()

        # Apply decay toward defaults (anti-overfitting)
        self._apply_decay()

        self.update_count += 1
        from datetime import datetime, timezone
        self.last_update = datetime.now(timezone.utc).isoformat()

        # Store attribution snapshot for this trade (agent votes, weights, decision, decisive factors)
        self._store_attribution(symbol, matched, outcome_direction, correct_direction, adjustments)

        # Persist learner provenance (outcome IDs used, version, timestamp, quality score)
        self._persist_learner_provenance(symbol, outcome_direction, matched.get("timestamp"), len(adjustments))

        # Persist
        self._persist_to_store()

        try:
            from app.core.metrics import counter_inc
            counter_inc("learner_update_total", {"status": "ok"})
        except Exception:
            pass

        logger.info(
            "WeightLearner: updated from %s %s outcome "
            "(R=%.2f, %d agents adjusted, debate=%s, red_team=%s, update #%d)",
            symbol,
            outcome_direction,
            r_multiple,
            len(adjustments),
            debate_winner or "none",
            red_team_recommendation or "none",
            self.update_count,
        )

        return self._weights

    def _audit_dropped_input(
        self,
        symbol: str,
        outcome_direction: str,
        reason: str,
        outcome_id: Optional[str] = None,
    ) -> None:
        """Audit log for dropped learner inputs (observable, diagnosable)."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learner_dropped_input_audit (
                    id INTEGER PRIMARY KEY,
                    symbol VARCHAR,
                    outcome_direction VARCHAR,
                    reason VARCHAR,
                    outcome_id VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                """INSERT INTO learner_dropped_input_audit
                   (id, symbol, outcome_direction, reason, outcome_id)
                   VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM learner_dropped_input_audit), ?, ?, ?, ?)""",
                [symbol or "", outcome_direction or "", reason or "", outcome_id or ""],
            )
        except Exception as e:
            logger.debug("Learner dropped-input audit failed: %s", e)

    def _persist_learner_provenance(
        self,
        symbol: str,
        outcome_direction: str,
        decision_ts: Any,
        agents_updated: int,
    ) -> None:
        """Persist learner update provenance: outcome IDs used, learner version, timestamp, quality score."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learner_provenance (
                    id INTEGER PRIMARY KEY,
                    symbol VARCHAR,
                    outcome_direction VARCHAR,
                    decision_ts VARCHAR,
                    agents_updated INTEGER,
                    update_count INTEGER,
                    learner_version VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                """INSERT INTO learner_provenance
                   (id, symbol, outcome_direction, decision_ts, agents_updated, update_count, learner_version)
                   VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM learner_provenance), ?, ?, ?, ?, ?, ?)""",
                [
                    symbol or "",
                    outcome_direction or "",
                    str(decision_ts) if decision_ts else "",
                    agents_updated,
                    self.update_count,
                    "1.0",
                ],
            )
        except Exception as e:
            logger.debug("Learner provenance persist failed: %s", e)

    def _store_attribution(
        self,
        symbol: str,
        decision: Dict[str, Any],
        outcome_direction: str,
        correct_direction: str,
        adjustments: Dict[str, Any],
    ) -> None:
        """Store attribution snapshot per trade in DuckDB (agent votes, weights, arbiter decision)."""
        try:
            from app.data.duckdb_storage import duckdb_store
            import json
            conn = duckdb_store.get_thread_cursor()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_attribution (
                    id INTEGER PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    final_direction VARCHAR,
                    outcome_direction VARCHAR,
                    correct_direction VARCHAR,
                    agent_votes VARCHAR,
                    weights_used VARCHAR,
                    decisive_factors VARCHAR
                )
            """)
            votes_json = json.dumps(decision.get("votes", []))
            weights_json = json.dumps({a: adj.get("new") for a, adj in adjustments.items()})
            decisive = json.dumps({
                "outcome": outcome_direction,
                "correct_direction": correct_direction,
                "agents_updated": list(adjustments.keys()),
            })
            conn.execute(
                """INSERT INTO trade_attribution
                   (id, symbol, final_direction, outcome_direction, correct_direction, agent_votes, weights_used, decisive_factors)
                   VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM trade_attribution), ?, ?, ?, ?, ?, ?, ?)""",
                [
                    symbol.upper(),
                    decision.get("final_direction", ""),
                    outcome_direction,
                    correct_direction,
                    votes_json,
                    weights_json,
                    decisive,
                ],
            )
        except Exception as e:
            logger.debug("WeightLearner: store attribution failed: %s", e)

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
            conn = duckdb_store.get_thread_cursor()
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
            conn = duckdb_store.get_thread_cursor()
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
