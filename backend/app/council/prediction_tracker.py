"""Prediction Tracker — Free Energy Principle for agent weight learning.

Records council predictions and resolves them against actual outcomes.
Uses prediction error (surprise) as the learning signal:

  Free Energy = prediction_error^2
  Surprise = -log(P(outcome | prediction))

Agents that consistently produce high prediction errors get their
weights dampened by the WeightLearner. This implements the Free Energy
Principle: the system minimizes surprise by improving its predictions.

Usage:
    from app.council.prediction_tracker import get_prediction_tracker
    tracker = get_prediction_tracker()
    await tracker.record_predictions(decision)
    await tracker.resolve_predictions("AAPL", actual_direction="buy", pnl=150.0)
"""

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PredictionTracker:
    """Tracks council predictions and computes Free Energy metrics.

    Prediction error drives the self-learning loop:
    high error → WeightLearner dampens inaccurate agents → system improves.
    """

    def __init__(self):
        self._pending_predictions: Dict[str, Dict[str, Any]] = {}
        self._total_recorded: int = 0
        self._total_resolved: int = 0
        self._total_free_energy: float = 0.0

    async def record_predictions(self, decision) -> str:
        """Record a council decision's predictions for later resolution.

        Parameters
        ----------
        decision : DecisionPacket
            The council decision containing all agent votes.

        Returns
        -------
        str : The prediction_id for later resolution.
        """
        prediction_id = f"pred-{uuid.uuid4().hex[:12]}"
        symbol = decision.symbol
        timestamp = decision.timestamp

        # Extract per-agent predictions
        agent_predictions = {}
        for vote in decision.votes:
            agent_predictions[vote.agent_name] = {
                "direction": vote.direction,
                "confidence": vote.confidence,
                "weight": vote.weight,
            }

        record = {
            "prediction_id": prediction_id,
            "symbol": symbol,
            "timestamp": timestamp,
            "predicted_direction": decision.final_direction,
            "predicted_confidence": decision.final_confidence,
            "agent_predictions": agent_predictions,
        }

        # Store in memory for fast lookup
        key = symbol.upper()
        self._pending_predictions[key] = record
        self._total_recorded += 1

        # Persist to DuckDB
        try:
            import json
            from app.data.duckdb_storage import duckdb_store
            duckdb_store.query(
                """INSERT INTO prediction_history
                   (prediction_id, symbol, timestamp, predicted_direction,
                    predicted_confidence, agent_predictions_json)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT (prediction_id) DO NOTHING""",
                [
                    prediction_id, symbol, timestamp,
                    decision.final_direction, decision.final_confidence,
                    json.dumps(agent_predictions),
                ],
            )
        except Exception as e:
            logger.debug("prediction_history persist failed: %s", e)

        logger.debug(
            "Recorded prediction %s: %s %s @ %.0f%%",
            prediction_id, symbol, decision.final_direction,
            decision.final_confidence * 100,
        )
        return prediction_id

    async def resolve_predictions(
        self,
        symbol: str,
        actual_direction: str,
        pnl: float = 0.0,
        r_multiple: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Resolve pending predictions for a symbol against actual outcome.

        Computes prediction error and Free Energy for each agent,
        then triggers WeightLearner update.

        Parameters
        ----------
        symbol : str
            The resolved symbol.
        actual_direction : str
            The actual outcome direction ("buy"/"sell"/"win"/"loss").
        pnl : float
            Actual profit/loss.
        r_multiple : float
            Risk-adjusted return.

        Returns
        -------
        Dict with resolution metrics, or None if no pending prediction.
        """
        key = symbol.upper()
        record = self._pending_predictions.pop(key, None)
        if not record:
            logger.debug("No pending prediction for %s", symbol)
            return None

        predicted = record["predicted_direction"]
        confidence = record["predicted_confidence"]

        # Compute prediction error
        # Map outcome to direction for comparison
        if actual_direction in ("win", "profit"):
            effective_actual = predicted  # prediction was correct
        elif actual_direction in ("loss", "stop_loss"):
            effective_actual = "sell" if predicted == "buy" else "buy"
        else:
            effective_actual = actual_direction

        correct = predicted == effective_actual
        prediction_error = 0.0 if correct else 1.0

        # Surprise: -log(P(outcome)). Higher confidence wrong = more surprise
        if correct:
            surprise = -math.log(max(confidence, 0.01))
        else:
            surprise = -math.log(max(1.0 - confidence, 0.01))

        # Free Energy = prediction_error^2 (simplified)
        free_energy = prediction_error ** 2

        self._total_resolved += 1
        self._total_free_energy += free_energy

        resolution = {
            "prediction_id": record["prediction_id"],
            "symbol": symbol,
            "predicted_direction": predicted,
            "predicted_confidence": confidence,
            "actual_direction": actual_direction,
            "correct": correct,
            "prediction_error": prediction_error,
            "surprise": round(surprise, 4),
            "free_energy": round(free_energy, 4),
            "pnl": pnl,
            "r_multiple": r_multiple,
        }

        # Persist resolution to DuckDB
        try:
            from app.data.duckdb_storage import duckdb_store
            now = datetime.now(timezone.utc).isoformat()
            duckdb_store.query(
                """UPDATE prediction_history SET
                     actual_direction = ?,
                     actual_pnl = ?,
                     prediction_error = ?,
                     surprise = ?,
                     free_energy = ?,
                     resolved = TRUE,
                     resolved_at = ?
                   WHERE prediction_id = ?""",
                [
                    actual_direction, pnl, prediction_error,
                    surprise, free_energy, now,
                    record["prediction_id"],
                ],
            )
        except Exception as e:
            logger.debug("prediction_history resolution persist failed: %s", e)

        # Trigger WeightLearner update
        try:
            from app.council.weight_learner import get_weight_learner
            learner = get_weight_learner()
            learner.update_from_outcome(
                symbol=symbol,
                outcome_direction=actual_direction,
                pnl=pnl,
                r_multiple=r_multiple,
            )
        except Exception as e:
            logger.debug("WeightLearner update failed: %s", e)

        logger.info(
            "Prediction resolved: %s %s -> %s (correct=%s, surprise=%.2f, FE=%.2f)",
            symbol, predicted, actual_direction, correct, surprise, free_energy,
        )
        return resolution

    def get_status(self) -> Dict[str, Any]:
        """Return tracker status."""
        avg_fe = (
            self._total_free_energy / self._total_resolved
            if self._total_resolved > 0
            else 0.0
        )
        return {
            "pending_predictions": len(self._pending_predictions),
            "total_recorded": self._total_recorded,
            "total_resolved": self._total_resolved,
            "avg_free_energy": round(avg_fe, 4),
            "total_free_energy": round(self._total_free_energy, 4),
        }


# Module-level singleton
_tracker_instance: Optional[PredictionTracker] = None


def get_prediction_tracker() -> PredictionTracker:
    """Get or create the global PredictionTracker singleton."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = PredictionTracker()
    return _tracker_instance
