"""Agent Self-Awareness System — streak detection, health monitoring; weights from WeightLearner.

Components:
1. BayesianAgentWeights: READ-ONLY delegate to WeightLearner (single source of truth).
   No longer updated from outcomes — avoids dual weight system desync (dopamine loop bug).
2. StreakDetector: Tracks win/loss streaks, PROBATION at 5, HIBERNATION at 10.
   Recovery: 5 consecutive wins after HIBERNATION -> ACTIVE.
3. AgentHealthMonitor: Tracks latency, error rate, last success

Usage:
    from app.council.self_awareness import get_self_awareness
    sa = get_self_awareness()
    weight = sa.get_effective_weight("market_perception")  # WeightLearner weight * streak mult
    status = sa.streaks.get_status("risk")
    sa.health.record_run("hypothesis", latency_ms=45.0, success=True)
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY_WEIGHTS = "bayesian_agent_weights"
CONFIG_KEY_STREAKS = "agent_streaks"


# ---------------------------------------------------------------------------
# 1. Bayesian Agent Weights (read-through to WeightLearner — single source of truth)
# ---------------------------------------------------------------------------
class BayesianAgentWeights:
    """Weights delegate to WeightLearner to avoid dual weight system desync.

    No longer stores or updates its own Beta(alpha, beta). get_weight() returns
    WeightLearner.get_weight(agent). get_distribution() returns a synthetic view
    for dashboard compatibility.
    """

    def __init__(self):
        self._weights: Dict[str, tuple] = {}  # legacy cache only; prefer weight_learner
        self._load()

    def _load(self):
        """Load legacy cache from SQLite (for backward compatibility only)."""
        data = db_service.get_config(CONFIG_KEY_WEIGHTS)
        if data:
            self._weights = {k: tuple(v) for k, v in data.items()}

    def _get_learner_weight(self, agent_name: str) -> float:
        """Single source of truth: WeightLearner."""
        try:
            from app.council.weight_learner import get_weight_learner
            return get_weight_learner().get_weight(agent_name)
        except Exception:
            return 1.0

    def get_weight(self, agent_name: str) -> float:
        """Returns WeightLearner weight for this agent (single source of truth)."""
        return self._get_learner_weight(agent_name)

    def get_all_weights(self) -> Dict[str, float]:
        """Return weights for all agents known to WeightLearner."""
        try:
            from app.council.weight_learner import get_weight_learner
            return get_weight_learner().get_weights()
        except Exception:
            return dict(self._weights) if self._weights else {}

    def get_distribution(self, agent_name: str) -> Dict[str, float]:
        """Return synthetic distribution for dashboard (mean = WeightLearner weight)."""
        mean = self.get_weight(agent_name)
        return {
            "alpha": 2.0,
            "beta": 2.0,
            "mean": mean,
            "samples": 0,
            "source": "weight_learner",
        }


# ---------------------------------------------------------------------------
# 2. Streak Detector
# ---------------------------------------------------------------------------
class StreakDetector:
    """Tracks agent win/loss streaks.

    5 consecutive losses = PROBATION (0.25x weight)
    10 consecutive losses = HIBERNATION (0x weight, agent skipped)
    """

    PROBATION_THRESHOLD = 5
    HIBERNATION_THRESHOLD = 10

    def __init__(self):
        self._streaks: Dict[str, Dict[str, Any]] = {}  # agent -> {current, type, max_loss}
        self._load()

    def _load(self):
        data = db_service.get_config(CONFIG_KEY_STREAKS)
        if data:
            self._streaks = data

    def _save(self):
        db_service.set_config(CONFIG_KEY_STREAKS, self._streaks)

    def get_status(self, agent_name: str) -> str:
        """Returns ACTIVE, PROBATION, or HIBERNATION."""
        info = self._streaks.get(agent_name, {})
        loss_streak = info.get("loss_streak", 0)
        if loss_streak >= self.HIBERNATION_THRESHOLD:
            return "HIBERNATION"
        elif loss_streak >= self.PROBATION_THRESHOLD:
            return "PROBATION"
        return "ACTIVE"

    def get_streak_info(self, agent_name: str) -> Dict[str, Any]:
        """Return full streak info for an agent."""
        info = self._streaks.get(agent_name, {"loss_streak": 0, "win_streak": 0, "max_loss_streak": 0})
        info["status"] = self.get_status(agent_name)
        return info

    # Consecutive wins required to recover: PROBATION -> ACTIVE
    PROBATION_RECOVERY_WINS = 3
    # Consecutive wins required to recover: HIBERNATION -> PROBATION (then 3 more -> ACTIVE)
    HIBERNATION_RECOVERY_WINS = 5

    def record_outcome(self, agent_name: str, profitable: bool):
        """Record a trade outcome for streak tracking.

        Auto-recovery:
        - 3 consecutive wins after PROBATION -> ACTIVE.
        - 5 consecutive wins after HIBERNATION -> PROBATION; then 3 consecutive wins -> ACTIVE.
        """
        if agent_name not in self._streaks:
            self._streaks[agent_name] = {"loss_streak": 0, "win_streak": 0, "max_loss_streak": 0}

        info = self._streaks[agent_name]
        prev_loss = info.get("loss_streak", 0)
        was_hibernated = prev_loss >= self.HIBERNATION_THRESHOLD
        was_probation = self.PROBATION_THRESHOLD <= prev_loss < self.HIBERNATION_THRESHOLD

        if profitable:
            info["win_streak"] = info.get("win_streak", 0) + 1
            win_streak = info["win_streak"]

            if was_hibernated and win_streak >= self.HIBERNATION_RECOVERY_WINS:
                info["loss_streak"] = self.PROBATION_THRESHOLD
                info["win_streak"] = 0
                logger.info(
                    "Agent %s recovered from HIBERNATION to PROBATION after %d wins",
                    agent_name, self.HIBERNATION_RECOVERY_WINS,
                )
            elif was_probation and win_streak >= self.PROBATION_RECOVERY_WINS:
                info["loss_streak"] = 0
                info["win_streak"] = 0
                logger.info(
                    "Agent %s recovered from PROBATION to ACTIVE after %d wins",
                    agent_name, self.PROBATION_RECOVERY_WINS,
                )
            elif was_hibernated or was_probation:
                pass
            else:
                info["loss_streak"] = 0
        else:
            info["loss_streak"] = prev_loss + 1
            info["win_streak"] = 0
            info["max_loss_streak"] = max(info.get("max_loss_streak", 0), info["loss_streak"])

        self._save()
        status = self.get_status(agent_name)
        if status != "ACTIVE":
            logger.warning("Agent %s status: %s (loss streak: %d)", agent_name, status, info["loss_streak"])

    def get_weight_multiplier(self, agent_name: str) -> float:
        """Return weight multiplier based on streak status."""
        status = self.get_status(agent_name)
        if status == "HIBERNATION":
            return 0.0
        elif status == "PROBATION":
            return 0.25
        return 1.0

    def reset(self, agent_name: str):
        """Reset streak for an agent (manual recovery from hibernation)."""
        self._streaks[agent_name] = {"loss_streak": 0, "win_streak": 0, "max_loss_streak": 0}
        self._save()


# ---------------------------------------------------------------------------
# 3. Agent Health Monitor
# ---------------------------------------------------------------------------
class AgentHealthMonitor:
    """Tracks latency, error rate, last_success for each agent."""

    def __init__(self):
        self._health: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_runs": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
            "last_run": 0.0,
            "last_success": 0.0,
            "last_error": "",
        })

    def record_run(self, agent_name: str, latency_ms: float, success: bool, error: str = ""):
        """Record an agent execution run."""
        h = self._health[agent_name]
        h["total_runs"] += 1
        h["total_latency_ms"] += latency_ms
        h["last_run"] = time.time()
        if success:
            h["last_success"] = time.time()
        else:
            h["errors"] += 1
            h["last_error"] = error

    def get_health(self, agent_name: str) -> Dict[str, Any]:
        """Get health metrics for an agent."""
        h = dict(self._health[agent_name])
        if h["total_runs"] > 0:
            h["avg_latency_ms"] = h["total_latency_ms"] / h["total_runs"]
            h["error_rate"] = h["errors"] / h["total_runs"]
        else:
            h["avg_latency_ms"] = 0.0
            h["error_rate"] = 0.0
        h["healthy"] = self.is_healthy(agent_name)
        return h

    def is_healthy(self, agent_name: str) -> bool:
        """Check if agent is healthy (error rate < 50%, recent success)."""
        h = self._health[agent_name]
        if h["total_runs"] == 0:
            return True  # No data = assume healthy
        error_rate = h["errors"] / h["total_runs"]
        if error_rate > 0.5:
            return False
        # Check for stale agent (no success in 1 hour)
        if h["last_success"] > 0 and (time.time() - h["last_success"]) > 3600:
            return False
        return True

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health metrics for all agents."""
        return {name: self.get_health(name) for name in self._health}


# ---------------------------------------------------------------------------
# Combined Self-Awareness System
# ---------------------------------------------------------------------------
class SelfAwareness:
    """Combined system: Bayesian weights + streak detection + health monitoring."""

    def __init__(self):
        self.weights = BayesianAgentWeights()
        self.streaks = StreakDetector()
        self.health = AgentHealthMonitor()

    def get_effective_weight(self, agent_name: str) -> float:
        """Get effective weight: WeightLearner (single source) * streak multiplier."""
        base_weight = self.weights.get_weight(agent_name)  # delegates to WeightLearner
        streak_mult = self.streaks.get_weight_multiplier(agent_name)
        return base_weight * streak_mult

    def record_trade_outcome(self, agent_name: str, profitable: bool):
        """Record a trade outcome for streak tracking only. Weights come from WeightLearner."""
        self.streaks.record_outcome(agent_name, profitable)

    def should_skip_agent(self, agent_name: str) -> bool:
        """Check if agent should be skipped (hibernated or unhealthy)."""
        status = self.streaks.get_status(agent_name)
        if status == "HIBERNATION":
            return True
        if not self.health.is_healthy(agent_name):
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Full self-awareness status for dashboard."""
        agents = set(list(self.weights._weights.keys()) + list(self.streaks._streaks.keys()))
        result = {}
        for agent in agents:
            result[agent] = {
                "bayesian_weight": self.weights.get_weight(agent),
                "distribution": self.weights.get_distribution(agent),
                "streak": self.streaks.get_streak_info(agent),
                "health": self.health.get_health(agent),
                "effective_weight": self.get_effective_weight(agent),
                "skip": self.should_skip_agent(agent),
            }
        return result


# Global singleton
_self_awareness: Optional[SelfAwareness] = None


def get_self_awareness() -> SelfAwareness:
    """Get or create the singleton SelfAwareness system."""
    global _self_awareness
    if _self_awareness is None:
        _self_awareness = SelfAwareness()
    return _self_awareness
