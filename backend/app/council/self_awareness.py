"""Agent Self-Awareness System — Bayesian weights, streak detection, health monitoring.

Components:
1. BayesianAgentWeights: Beta(alpha, beta) distribution updated from trade outcomes
2. StreakDetector: Tracks win/loss streaks, PROBATION at 5, HIBERNATION at 10
3. AgentHealthMonitor: Tracks latency, error rate, last success

Usage:
    from app.council.self_awareness import get_self_awareness
    sa = get_self_awareness()
    weight = sa.weights.get_weight("market_perception")
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
# 1. Bayesian Agent Weights
# ---------------------------------------------------------------------------
class BayesianAgentWeights:
    """Each agent has Beta(alpha, beta) distribution. Updated from trade outcomes.

    Weight = mean of Beta = alpha / (alpha + beta)
    Profitable trade: alpha += 1
    Losing trade: beta += 1
    """

    def __init__(self):
        self._weights: Dict[str, tuple] = {}  # agent -> (alpha, beta)
        self._load()

    def _load(self):
        """Load from SQLite config store."""
        data = db_service.get_config(CONFIG_KEY_WEIGHTS)
        if data:
            self._weights = {k: tuple(v) for k, v in data.items()}

    def _save(self):
        """Persist to SQLite config store."""
        db_service.set_config(CONFIG_KEY_WEIGHTS, {k: list(v) for k, v in self._weights.items()})

    def get_weight(self, agent_name: str) -> float:
        """Returns mean of Beta distribution = alpha / (alpha + beta).

        Default prior: Beta(2, 2) = 0.5 (neutral/uninformative).
        """
        alpha, beta = self._weights.get(agent_name, (2.0, 2.0))
        return alpha / (alpha + beta)

    def get_all_weights(self) -> Dict[str, float]:
        """Return all agent weights as a dict."""
        result = {}
        for agent_name in self._weights:
            result[agent_name] = self.get_weight(agent_name)
        return result

    def update(self, agent_name: str, trade_profitable: bool):
        """Bayesian update: profitable -> alpha+1, loss -> beta+1."""
        alpha, beta = self._weights.get(agent_name, (2.0, 2.0))
        if trade_profitable:
            alpha += 1.0
        else:
            beta += 1.0
        self._weights[agent_name] = (alpha, beta)
        self._save()
        logger.debug(
            "Bayesian update: %s -> Beta(%.1f, %.1f) = %.3f",
            agent_name, alpha, beta, alpha / (alpha + beta),
        )

    def get_distribution(self, agent_name: str) -> Dict[str, float]:
        """Return full distribution info for an agent."""
        alpha, beta = self._weights.get(agent_name, (2.0, 2.0))
        return {
            "alpha": alpha,
            "beta": beta,
            "mean": alpha / (alpha + beta),
            "samples": alpha + beta - 4,  # subtract prior
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

    def record_outcome(self, agent_name: str, profitable: bool):
        """Record a trade outcome for streak tracking."""
        if agent_name not in self._streaks:
            self._streaks[agent_name] = {"loss_streak": 0, "win_streak": 0, "max_loss_streak": 0}

        info = self._streaks[agent_name]
        if profitable:
            info["win_streak"] = info.get("win_streak", 0) + 1
            info["loss_streak"] = 0
        else:
            info["loss_streak"] = info.get("loss_streak", 0) + 1
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
        """Get effective weight combining Bayesian and streak multiplier."""
        bayesian = self.weights.get_weight(agent_name)
        streak_mult = self.streaks.get_weight_multiplier(agent_name)
        return bayesian * streak_mult

    def record_trade_outcome(self, agent_name: str, profitable: bool):
        """Record a trade outcome for both Bayesian and streak tracking."""
        self.weights.update(agent_name, profitable)
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
