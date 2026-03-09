"""Agent Timeout Reflexes — adaptive timeout management for council agents.

This module implements intelligent timeout handling with:
1. Tiered timeouts based on agent stage/type
2. Adaptive timeout adjustment based on historical performance
3. Graceful degradation when agents timeout
4. Telemetry and monitoring of timeout events

Usage:
    from app.council.reflexes.timeout_reflex import get_timeout_manager
    tm = get_timeout_manager()
    timeout = tm.get_timeout("market_perception")
    tm.record_execution("market_perception", elapsed_ms=450, timed_out=False)
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Deque
from dataclasses import dataclass, field

from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)


@dataclass
class AgentTimeoutStats:
    """Statistics for a single agent's timeout behavior."""

    agent_name: str
    total_executions: int = 0
    total_timeouts: int = 0
    total_errors: int = 0
    execution_times: Deque[float] = field(default_factory=lambda: deque(maxlen=100))  # Last 100 execution times in ms
    last_execution_ms: float = 0.0
    last_timeout: Optional[datetime] = None
    timeout_streak: int = 0  # Consecutive timeouts

    @property
    def timeout_rate(self) -> float:
        """Calculate timeout rate (0-1)."""
        if self.total_executions == 0:
            return 0.0
        return self.total_timeouts / self.total_executions

    @property
    def p50_latency(self) -> float:
        """50th percentile latency in milliseconds."""
        if not self.execution_times:
            return 0.0
        sorted_times = sorted(self.execution_times)
        idx = len(sorted_times) // 2
        return sorted_times[idx]

    @property
    def p95_latency(self) -> float:
        """95th percentile latency in milliseconds."""
        if not self.execution_times:
            return 0.0
        sorted_times = sorted(self.execution_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def avg_latency(self) -> float:
        """Average latency in milliseconds."""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times)


class TimeoutManager:
    """Manages adaptive timeouts for council agents.

    Features:
    - Tiered timeouts by agent stage (perception, technical, strategy, etc.)
    - Adaptive timeout adjustment based on p95 latency
    - Tracks timeout statistics per agent
    - Provides timeout recommendations
    """

    # Default timeout tiers (in seconds)
    TIER_TIMEOUTS = {
        # Stage 1: Perception agents - fast data lookups
        "perception": 5.0,
        # Stage 2: Technical analysis - calculations
        "technical": 10.0,
        # Stage 3: Hypothesis/Memory - LLM inference
        "hypothesis": 15.0,
        # Stage 4: Strategy - complex decision logic
        "strategy": 12.0,
        # Stage 5: Risk/Execution - real-time critical decisions
        "risk_execution": 8.0,
        # Stage 6: Critic - postmortem analysis
        "critic": 12.0,
        # Default fallback
        "default": 30.0,
    }

    # Agent name -> tier mapping
    AGENT_TIERS = {
        # Stage 1: Perception
        "market_perception": "perception",
        "flow_perception": "perception",
        "regime": "perception",
        "social_perception": "perception",
        "news_catalyst": "perception",
        "youtube_knowledge": "perception",
        "intermarket": "perception",
        "gex_agent": "perception",
        "insider_agent": "perception",
        "finbert_sentiment_agent": "perception",
        "earnings_tone_agent": "perception",
        "dark_pool_agent": "perception",
        "macro_regime_agent": "perception",

        # Stage 2: Technical
        "rsi": "technical",
        "bbv": "technical",
        "ema_trend": "technical",
        "relative_strength": "technical",
        "cycle_timing": "technical",
        "supply_chain_agent": "technical",
        "institutional_flow_agent": "technical",
        "congressional_agent": "technical",

        # Stage 3: Hypothesis/Memory
        "hypothesis": "hypothesis",
        "layered_memory_agent": "hypothesis",

        # Stage 4: Strategy
        "strategy": "strategy",

        # Stage 5: Risk/Execution
        "risk": "risk_execution",
        "execution": "risk_execution",
        "portfolio_optimizer_agent": "risk_execution",

        # Stage 6: Critic
        "critic": "critic",

        # Background enrichment
        "alt_data_agent": "default",
    }

    def __init__(self):
        self._stats: Dict[str, AgentTimeoutStats] = defaultdict(
            lambda: AgentTimeoutStats(agent_name="unknown")
        )
        self._timeout_overrides: Dict[str, float] = {}  # Manual timeout overrides
        self._adaptive_enabled = True
        self._adaptive_multiplier = 1.2  # Add 20% buffer to p95 latency
        self._min_samples = 10  # Minimum executions before using adaptive timeout

    def get_timeout(self, agent_name: str, use_adaptive: bool = True) -> float:
        """Get timeout budget for an agent.

        Args:
            agent_name: Agent identifier
            use_adaptive: If True, use adaptive timeout based on historical performance

        Returns:
            Timeout in seconds
        """
        # Check manual override first
        if agent_name in self._timeout_overrides:
            return self._timeout_overrides[agent_name]

        # Get base timeout from tier
        tier = self.AGENT_TIERS.get(agent_name, "default")
        base_timeout = self.TIER_TIMEOUTS[tier]

        # Apply adaptive adjustment if enabled and we have enough data
        if use_adaptive and self._adaptive_enabled:
            stats = self._stats[agent_name]
            if len(stats.execution_times) >= self._min_samples:
                # Use p95 latency + buffer, but cap at 2x base timeout
                adaptive_timeout = (stats.p95_latency / 1000.0) * self._adaptive_multiplier
                adaptive_timeout = min(adaptive_timeout, base_timeout * 2.0)
                # Don't reduce timeout below base
                return max(adaptive_timeout, base_timeout)

        return base_timeout

    def record_execution(
        self,
        agent_name: str,
        elapsed_ms: float,
        timed_out: bool = False,
        error: bool = False
    ):
        """Record an agent execution for timeout learning.

        Args:
            agent_name: Agent identifier
            elapsed_ms: Execution time in milliseconds
            timed_out: Whether the execution timed out
            error: Whether the execution errored
        """
        stats = self._stats[agent_name]
        stats.agent_name = agent_name
        stats.total_executions += 1
        stats.last_execution_ms = elapsed_ms

        if timed_out:
            stats.total_timeouts += 1
            stats.timeout_streak += 1
            stats.last_timeout = datetime.now(timezone.utc)
            logger.warning(
                "Agent %s timed out (streak=%d, rate=%.1f%%)",
                agent_name, stats.timeout_streak, stats.timeout_rate * 100
            )
        else:
            stats.timeout_streak = 0
            # Only record successful execution times for percentile calculation
            if not error:
                stats.execution_times.append(elapsed_ms)

        if error:
            stats.total_errors += 1

        # Alert if timeout streak is high
        if stats.timeout_streak >= 3:
            logger.error(
                "Agent %s has %d consecutive timeouts! Consider increasing timeout or investigating issue.",
                agent_name, stats.timeout_streak
            )

    def set_timeout_override(self, agent_name: str, timeout_seconds: float):
        """Set a manual timeout override for an agent.

        Args:
            agent_name: Agent identifier
            timeout_seconds: Timeout in seconds
        """
        self._timeout_overrides[agent_name] = timeout_seconds
        logger.info("Timeout override set for %s: %.1fs", agent_name, timeout_seconds)

    def clear_timeout_override(self, agent_name: str):
        """Clear manual timeout override for an agent."""
        if agent_name in self._timeout_overrides:
            del self._timeout_overrides[agent_name]
            logger.info("Timeout override cleared for %s", agent_name)

    def get_stats(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get timeout statistics.

        Args:
            agent_name: If provided, return stats for specific agent.
                       If None, return aggregate stats.

        Returns:
            Dictionary of timeout statistics
        """
        if agent_name:
            stats = self._stats.get(agent_name)
            if not stats:
                return {}
            return {
                "agent_name": stats.agent_name,
                "total_executions": stats.total_executions,
                "total_timeouts": stats.total_timeouts,
                "total_errors": stats.total_errors,
                "timeout_rate": stats.timeout_rate,
                "timeout_streak": stats.timeout_streak,
                "p50_latency_ms": stats.p50_latency,
                "p95_latency_ms": stats.p95_latency,
                "avg_latency_ms": stats.avg_latency,
                "last_execution_ms": stats.last_execution_ms,
                "last_timeout": stats.last_timeout.isoformat() if stats.last_timeout else None,
                "current_timeout_s": self.get_timeout(agent_name),
            }

        # Aggregate stats
        total_executions = sum(s.total_executions for s in self._stats.values())
        total_timeouts = sum(s.total_timeouts for s in self._stats.values())
        agents_with_timeouts = sum(1 for s in self._stats.values() if s.total_timeouts > 0)

        return {
            "total_executions": total_executions,
            "total_timeouts": total_timeouts,
            "overall_timeout_rate": total_timeouts / total_executions if total_executions > 0 else 0.0,
            "agents_tracked": len(self._stats),
            "agents_with_timeouts": agents_with_timeouts,
            "agents_in_timeout_streak": sum(1 for s in self._stats.values() if s.timeout_streak > 0),
            "max_timeout_streak": max((s.timeout_streak for s in self._stats.values()), default=0),
        }

    def get_all_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tracked agents.

        Returns:
            Dictionary mapping agent_name -> stats dict
        """
        return {
            name: self.get_stats(name)
            for name in self._stats.keys()
        }

    def reset_stats(self, agent_name: Optional[str] = None):
        """Reset timeout statistics.

        Args:
            agent_name: If provided, reset stats for specific agent.
                       If None, reset all stats.
        """
        if agent_name:
            if agent_name in self._stats:
                del self._stats[agent_name]
                logger.info("Reset timeout stats for %s", agent_name)
        else:
            self._stats.clear()
            logger.info("Reset all timeout stats")

    def should_skip_agent(self, agent_name: str) -> bool:
        """Determine if an agent should be temporarily skipped due to repeated timeouts.

        An agent is skipped if it has 5+ consecutive timeouts.

        Args:
            agent_name: Agent identifier

        Returns:
            True if agent should be skipped
        """
        stats = self._stats.get(agent_name)
        if not stats:
            return False

        if stats.timeout_streak >= 5:
            logger.warning(
                "Skipping agent %s due to %d consecutive timeouts",
                agent_name, stats.timeout_streak
            )
            return True

        return False

    def create_fallback_vote(
        self,
        agent_name: str,
        reason: str,
        blackboard_ref: Optional[str] = None
    ) -> AgentVote:
        """Create a fallback vote for a timed-out or skipped agent.

        Args:
            agent_name: Agent identifier
            reason: Reason for fallback (e.g., "timeout", "skipped")
            blackboard_ref: Optional blackboard reference

        Returns:
            AgentVote with hold direction and zero confidence
        """
        stats = self._stats.get(agent_name)
        timeout_info = ""
        if stats:
            timeout_info = f" (timeout_rate={stats.timeout_rate:.1%}, p95={stats.p95_latency:.0f}ms)"

        return AgentVote(
            agent_name=agent_name,
            direction="hold",
            confidence=0.0,
            reasoning=f"{reason}{timeout_info}",
            blackboard_ref=blackboard_ref or "",
        )


# Global singleton
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager() -> TimeoutManager:
    """Get the global TimeoutManager singleton."""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager
