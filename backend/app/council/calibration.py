"""Agent Confidence Calibration — Brier score tracking per agent (Phase C, C2).

Tracks (predicted_confidence - actual_outcome)^2 over rolling 100-trade windows.
Agents with Brier > 0.35 get a 20% weight penalty in the arbiter.

Usage:
    from app.council.calibration import get_calibration_tracker
    tracker = get_calibration_tracker()
    tracker.record(agent_name="risk", predicted_confidence=0.8, actual_outcome=1.0)
    brier = tracker.get_brier_score("risk")
    penalty = tracker.get_weight_penalty("risk")
"""
import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ROLLING_WINDOW = 100
POORLY_CALIBRATED_THRESHOLD = 0.35
WEIGHT_PENALTY_FACTOR = 0.80  # 20% penalty


class CalibrationTracker:
    """Track Brier scores per agent over rolling windows."""

    def __init__(self, window_size: int = ROLLING_WINDOW):
        self.window_size = window_size
        # agent_name -> deque of (predicted_confidence, actual_outcome, timestamp)
        self._observations: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    def record(self, agent_name: str, predicted_confidence: float, actual_outcome: float) -> None:
        """Record a calibration observation.

        Parameters
        ----------
        agent_name : str
            The agent being tracked.
        predicted_confidence : float
            The agent's stated confidence (0-1).
        actual_outcome : float
            1.0 if the agent's prediction was correct, 0.0 if wrong.
        """
        self._observations[agent_name].append(
            (float(predicted_confidence), float(actual_outcome), time.time())
        )

    def get_brier_score(self, agent_name: str) -> Optional[float]:
        """Compute Brier score for an agent: mean((predicted - actual)^2).

        Returns None if no observations yet.
        Lower is better (0 = perfect calibration, 1 = worst).
        """
        obs = self._observations.get(agent_name)
        if not obs or len(obs) == 0:
            return None
        total = sum((p - a) ** 2 for p, a, _ in obs)
        return round(total / len(obs), 4)

    def get_weight_penalty(self, agent_name: str) -> float:
        """Return weight multiplier based on calibration.

        Returns 0.80 (20% penalty) if Brier > 0.35, else 1.0.
        """
        brier = self.get_brier_score(agent_name)
        if brier is not None and brier > POORLY_CALIBRATED_THRESHOLD:
            return WEIGHT_PENALTY_FACTOR
        return 1.0

    def get_all_scores(self) -> Dict[str, Dict[str, Any]]:
        """Return calibration data for all tracked agents."""
        result = {}
        for agent_name in self._observations:
            obs = self._observations[agent_name]
            brier = self.get_brier_score(agent_name)
            penalty = self.get_weight_penalty(agent_name)
            window_start = obs[0][2] if obs else None
            window_end = obs[-1][2] if obs else None
            result[agent_name] = {
                "brier_score": brier,
                "n_trades": len(obs),
                "weight_penalty": penalty,
                "poorly_calibrated": brier is not None and brier > POORLY_CALIBRATED_THRESHOLD,
                "window_start": window_start,
                "window_end": window_end,
            }
        return result

    def persist_to_duckdb(self) -> None:
        """Persist calibration scores to DuckDB agent_calibration table."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            for agent_name, data in self.get_all_scores().items():
                conn.execute("""
                    INSERT OR REPLACE INTO agent_calibration
                    (agent_name, brier_score, window_start, window_end, n_trades, weight_penalty)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    agent_name,
                    data["brier_score"] or 0.0,
                    data["window_start"] or 0.0,
                    data["window_end"] or 0.0,
                    data["n_trades"],
                    data["weight_penalty"],
                ])
        except Exception as e:
            logger.debug("Calibration persist failed: %s", e)


# Global singleton
_tracker: Optional[CalibrationTracker] = None


def get_calibration_tracker() -> CalibrationTracker:
    """Get or create the global CalibrationTracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = CalibrationTracker()
    return _tracker
